# -*- coding: utf-8 -*-
"""
futbol/ia.py — El asistente de IA de ProFoot (pestañas "IA Coach" e "IA").

Reusa EXACTAMENTE el patrón que la plataforma ya tiene probado en
landing_page.py › predict_somatotype_gemini: la misma GEMINI_API_KEY, la misma
cadena de modelos de respaldo, thinkingBudget=0 (los tokens de "pensamiento"
también se cobran) y reintento ante 429.

Solo se usa el nivel GRATUITO. Si no hay clave o la API falla, se responde con
un análisis calculado de los datos del propio usuario: la pantalla siempre
devuelve algo útil, nunca un error.
"""
import logging
import os
import re

import requests

from . import db

logger = logging.getLogger(__name__)

MODELOS = ('gemini-flash-latest', 'gemini-2.5-flash', 'gemini-2.0-flash')

# Segundos como máximo para TODA la conversación con Gemini (los 3 modelos y sus
# reintentos). Debe quedar holgadamente por debajo del límite de la plataforma:
# 60 s en Vercel, 75 s en gunicorn.
PRESUPUESTO_S = int(os.getenv('IA_PRESUPUESTO_S', '30'))


def _contexto_jugador(user):
    """Datos reales del jugador para que la respuesta no sea genérica.

    Lleva también sus evaluaciones: son sus marcas y su nivel medido, justo lo
    que pregunta («¿cómo voy en velocidad?») y lo que antes no se le pasaba.
    """
    from . import evaluaciones as ev  # aquí dentro para no cruzar importaciones

    uid = user.id
    attrs = db.atributos(uid)
    perfil = db.perfil_jugador(uid)
    entrenos = db.rows('fut_trainings', 'ia entrenos', player_id=uid,
                       _order='fecha', _desc=True, _limit=8)
    metas = [m for m in db.rows('fut_goals', 'ia metas', player_id=uid)
             if m.get('estado') != 'completada']
    habitos = db.habitos(uid)

    partes = [
        f"Nombre: {getattr(user, 'name', '') or 'jugador'}",
        f"Posición: {perfil.get('posicion') or 'sin definir'}",
        f"Atributos (0-100): técnica {attrs['tecnica']}, físico {attrs['fisico']}, "
        f"táctico {attrs['tactico']}, mental {attrs['mental']}",
        f"Racha de hábitos: {db.racha_actual(uid)} días",
        f"Hábitos activos: {len(habitos)}",
        f"Entrenamientos registrados en los últimos días: {len(entrenos)}",
    ]
    if getattr(user, 'last_weight', None):
        partes.append(f"Peso: {user.last_weight} kg")
    if getattr(user, 'last_height', None):
        partes.append(f"Estatura: {user.last_height} cm")
    if metas:
        partes.append("Metas abiertas: " + "; ".join(
            f"{m.get('titulo')} ({m.get('progreso', 0)}%)" for m in metas[:5]))
    if entrenos:
        partes.append("Últimos entrenos: " + "; ".join(
            f"{e.get('fecha')} {e.get('tipo')} {e.get('duracion_min')}min" for e in entrenos[:5]))

    # ─── Sus evaluaciones ───────────────────────────────────────────────────
    try:
        mias = ev.enriquecer(ev.resultados_de(uid, 40),
                             db.entrenador_del_jugador(uid))
    except Exception as e:
        logger.warning('IA: no pude leer las evaluaciones del jugador: %s', e)
        mias = []

    if mias:
        partes.append(f"Evaluaciones que le han tomado: {len(mias)}")
        lineas = []
        for r in mias[:10]:
            fecha = r['_fecha'].strftime('%d/%m/%Y') if r.get('_fecha') else 'sin fecha'
            valor = r.get('_valor')
            marca = f"{valor:g}" if isinstance(valor, (int, float)) else (valor or '?')
            nivel_r = (r.get('_nivel_meta') or {}).get('etiqueta')
            lineas.append(
                f"{fecha}, {r.get('test_nombre') or r.get('test_clave')}: "
                f"{marca} {r.get('_unidad') or ''}".rstrip()
                + (f" ({nivel_r})" if nivel_r else '')
                + (f", puntaje {r['puntaje']}" if r.get('puntaje') is not None else ''))
        partes += _lista('Sus marcas:', lineas, 10)
    else:
        partes.append('Evaluaciones que le han tomado: 0')

    # ─── Lo que tiene por delante ───────────────────────────────────────────
    eventos = db.eventos_para_jugador(uid, desde=db.hoy_iso()) or []
    partes += _lista(f'Proximos eventos ({len(eventos)}):', [
        f"{e.get('fecha')}, {e.get('tipo') or 'evento'}: {e.get('titulo') or 'sin titulo'}"
        for e in eventos], 6)

    return "\n".join(partes)


def _lista(titulo, filas, tope):
    """Una sección del contexto, o nada si no hay datos que contar."""
    if not filas:
        return []
    salida = [titulo]
    salida += ['  - ' + f for f in filas[:tope]]
    if len(filas) > tope:
        salida.append(f'  ... y {len(filas) - tope} más')
    return salida


def _contexto_entrenador(user):
    """Todo lo que el entrenador tiene cargado, para que la IA no responda a ciegas.

    Antes esto eran cuatro líneas —nombre del equipo, cuántos jugadores con
    cuenta y cuántos eventos futuros— y la IA contestaba «no tienes jugadores» a
    quien tenía diecinueve: los apuntados a mano no entraban, y las evaluaciones
    y los planes de entrenamiento no se miraban siquiera.

    Se pide por `equipo_id` y no por `user.id`: un asistente técnico trabaja
    sobre el equipo del principal, y preguntando por el suyo no salía nada.
    """
    from . import evaluaciones as ev  # aquí dentro para no cruzar importaciones

    uid = db.equipo_id(user.id)
    equipo = db.equipo_del_entrenador(uid) or {}
    jugadores = db.jugadores_del_entrenador(uid)
    manuales = db.rows('fut_manual_players', 'ia manuales', coach_id=uid, activo=True) or []

    edad = equipo.get('categoria_edad') or 'general'
    nivel = equipo.get('nivel') or 'general'
    partes = [
        f"Entrenador: {getattr(user, 'name', '') or 'entrenador'}"
        + (' (asistente tecnico del equipo)' if uid != user.id else ''),
        f"Equipo: {equipo.get('nombre') or 'sin nombre'}",
        f"Categoria de referencia: {edad.replace('_', '-')}, nivel {nivel}",
        f"Plantilla: {len(jugadores) + len(manuales)} jugadores "
        f"({len(jugadores)} con cuenta, {len(manuales)} apuntados a mano)",
    ]

    # ─── Quiénes son ────────────────────────────────────────────────────────
    fichas = []
    for j in jugadores:
        f = j.get('fut') or {}
        fichas.append(f"{j.get('name')}: {f.get('posicion') or 'sin posicion'}"
                      + (f", dorsal {f['dorsal']}" if f.get('dorsal') else ''))
    for m in manuales:
        fichas.append(f"{m.get('nombre')}: {m.get('posicion') or 'sin posicion'}"
                      + (f", dorsal {m['dorsal']}" if m.get('dorsal') else '')
                      + ' (sin cuenta)')
    partes += _lista('Jugadores:', fichas, 30)

    # ─── Cómo están ─────────────────────────────────────────────────────────
    ids = [j['id'] for j in jugadores]
    if ids:
        attrs = db.q(
            lambda: db.sb().table('fut_attributes').select('*').in_('player_id', ids).execute().data or [],
            [], 'ia attrs')
        medias = []
        for k in db.ATRIBUTOS:
            vals = [a[k] for a in attrs if a.get(k) is not None]
            if vals:
                medias.append(f"{k} {round(sum(vals) / len(vals))}")
        if medias:
            partes.append('Medias del equipo (0-100): ' + ', '.join(medias))

    # ─── Evaluaciones ───────────────────────────────────────────────────────
    #  Es lo que más se le pregunta y lo que antes no se le pasaba en absoluto.
    try:
        resultados = ev.enriquecer(ev.resultados_equipo(uid, 120), uid)
    except Exception as e:
        logger.warning('IA: no pude leer las evaluaciones: %s', e)
        resultados = []

    if resultados:
        partes.append(f"Evaluaciones registradas: {len(resultados)}")
        medias = ev.medias_por_categoria(resultados) or {}
        sueltas = [f"{k} {v}" for k, v in medias.items() if v is not None]
        if sueltas:
            partes.append('Puntaje medio por familia: ' + ', '.join(sueltas))
        lineas = []
        for r in resultados[:14]:
            fecha = r['_fecha'].strftime('%d/%m/%Y') if r.get('_fecha') else 'sin fecha'
            valor = r.get('_valor')
            marca = f"{valor:g}" if isinstance(valor, (int, float)) else (valor or '?')
            nivel_r = (r.get('_nivel_meta') or {}).get('etiqueta')
            lineas.append(
                f"{fecha}, {r.get('jugador_nombre') or 'jugador'}, "
                f"{r.get('test_nombre') or r.get('test_clave')}: {marca} {r.get('_unidad') or ''}".rstrip()
                + (f" ({nivel_r})" if nivel_r else '')
                + (f", puntaje {r['puntaje']}" if r.get('puntaje') is not None else ''))
        partes += _lista('Ultimas evaluaciones:', lineas, 14)
    else:
        partes.append('Evaluaciones registradas: 0 (todavia no ha tomado ninguna prueba)')

    # ─── Entrenamientos ─────────────────────────────────────────────────────
    planes = db.rows('fut_training_plans', 'ia planes', coach_id=uid,
                     _order='creado', _desc=True, _limit=12) or []
    partes.append(f"Planes de entrenamiento creados: {len(planes)}")
    partes += _lista('Planes:', [
        f"{p.get('nombre')}: {p.get('tipo') or 'sin tipo'}"
        + (f"/{p['subtipo']}" if p.get('subtipo') else '')
        + (f", {p['duracion_min']} min" if p.get('duracion_min') else '')
        + (f", intensidad {p['intensidad']}" if p.get('intensidad') else '')
        for p in planes], 8)

    # ─── Agenda ─────────────────────────────────────────────────────────────
    #  Los eventos pasados importan tanto como los próximos: «cuántos entrenos
    #  llevamos este mes» es justo lo que se pregunta, y antes solo veía el
    #  futuro, así que un equipo con historial parecía recién creado.
    hoy = db.hoy_iso()
    todos = db.eventos_equipo(uid) or []
    proximos = [e for e in todos if (e.get('fecha') or '') >= hoy]
    pasados = sorted([e for e in todos if (e.get('fecha') or '') < hoy],
                     key=lambda x: x.get('fecha') or '', reverse=True)
    partes.append(f"Agenda: {len(proximos)} eventos por delante, {len(pasados)} ya celebrados")
    partes += _lista('Proximos eventos:', [
        f"{e.get('fecha')} {e.get('hora') or ''}, {e.get('tipo') or 'evento'}: "
        f"{e.get('titulo') or 'sin titulo'}".replace('  ', ' ')
        for e in proximos], 8)
    partes += _lista('Ultimos eventos celebrados:', [
        f"{e.get('fecha')}, {e.get('tipo') or 'evento'}: {e.get('titulo') or 'sin titulo'}"
        for e in pasados], 6)

    # ─── Parte médico ───────────────────────────────────────────────────────
    lesiones = [x for x in (db.rows('fut_injuries', 'ia lesiones', coach_id=uid) or [])
                if (x.get('estado') or '') not in ('alta', 'recuperado')]
    partes += _lista(f'Partes medicos abiertos ({len(lesiones)}):', [
        f"{x.get('zona') or 'zona sin indicar'}, {x.get('tipo') or 'lesion'}"
        f", {x.get('gravedad') or 'gravedad sin indicar'}"
        + (f", desde {x['fecha']}" if x.get('fecha') else '')
        for x in lesiones], 8)

    return "\n".join(partes)


def _prompt(user, pregunta):
    es_coach = getattr(user, 'role', '') == 'especialista'
    if es_coach:
        rol = ("Eres el asistente técnico de un ENTRENADOR de fútbol. Aconsejas sobre "
               "planificación de entrenamientos, gestión de plantilla, táctica y lectura "
               "del rendimiento del equipo.")
        contexto = _contexto_entrenador(user)
    else:
        rol = ("Eres el asistente personal de un JUGADOR de fútbol. Aconsejas sobre "
               "entrenamiento, técnica, hábitos, descanso, alimentación y mentalidad.")
        contexto = _contexto_jugador(user)

    return (
        f"{rol}\n\n"
        "Reglas de tu respuesta:\n"
        "- Responde SIEMPRE en español, tuteando, con tono cercano y directo.\n"
        "- Máximo 180 palabras. Ve al grano.\n"
        "- Apóyate en los datos reales que te doy; cita cifras concretas cuando ayuden.\n"
        "- Da consejos accionables, no generalidades.\n"
        "- No inventes datos que no estén en el contexto.\n"
        "- Si te preguntan por dolor, lesión o síntomas médicos, recomienda consultar "
        "al médico o fisioterapeuta del club; no diagnostiques.\n"
        "- Nada de markdown ni asteriscos: texto corrido con saltos de línea.\n\n"
        f"DATOS REALES:\n{contexto}\n\n"
        f"PREGUNTA:\n{pregunta}"
    )


def _gemini(prompt):
    """Llama a Gemini en su nivel gratuito. Devuelve None si no hay clave o falla."""
    api_key = (os.environ.get('GEMINI_API_KEY') or '').strip()
    if not api_key:
        return None

    payload = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {
            'temperature': 0.7,
            'maxOutputTokens': 700,
            # Los modelos 2.5 "piensan" y esos tokens cuentan → apagado.
            'thinkingConfig': {'thinkingBudget': 0},
        },
    }

    # Presupuesto TOTAL de la llamada. Sin él, encadenar 3 modelos con reintento
    # podía tardar minutos y morir contra el límite de la función (Vercel) o del
    # worker (gunicorn). Antes de agotarlo se corta y responde el respaldo.
    import time
    limite = time.monotonic() + PRESUPUESTO_S

    for modelo in MODELOS:
        restante = limite - time.monotonic()
        if restante < 4:
            logger.info('IA: sin tiempo para más modelos, uso el respaldo')
            break

        url = f'https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}'
        try:
            r = requests.post(url, json=payload, timeout=min(20, restante))
            if r.status_code == 429 and (limite - time.monotonic()) > 8:
                time.sleep(2)
                r = requests.post(url, json=payload,
                                  timeout=min(20, max(4, limite - time.monotonic())))
            if r.status_code == 429:
                logger.info('IA: cuota por minuto en %s, pruebo el siguiente', modelo)
                continue
            r.raise_for_status()
            texto = r.json()['candidates'][0]['content']['parts'][0]['text']
            texto = re.sub(r'[*_`#]+', '', texto or '').strip()
            if texto:
                return texto
        except Exception as e:
            logger.warning('IA %s falló: %s', modelo, e)
            continue
    return None


def _respaldo(user, pregunta):
    """Análisis calculado con los datos del usuario, sin llamar a ninguna API.

    Se usa cuando no hay clave de Gemini o la API no responde. No es un mensaje
    de error: es una respuesta corta pero real y basada en sus propios números.
    """
    es_coach = getattr(user, 'role', '') == 'especialista'
    nombre = (getattr(user, 'name', '') or '').split(' ')[0] or 'crack'

    if es_coach:
        #  Por equipo_id y contando a los apuntados a mano: por user.id un
        #  asistente veia un equipo vacio, y sin los manuales el respaldo decia
        #  «no tienes jugadores» a quien tiene la plantilla llena de ellos.
        uid = db.equipo_id(user.id)
        jugadores = db.jugadores_del_entrenador(uid)
        manuales = db.rows('fut_manual_players', 'respaldo manuales',
                           coach_id=uid, activo=True) or []
        total = len(jugadores) + len(manuales)
        eventos = db.eventos_equipo(uid, desde=db.hoy_iso())
        lineas = [f"{nombre}, esto es lo que veo hoy en tu equipo:", ""]
        lineas.append(f"· Plantilla: {total} jugador{'es' if total != 1 else ''}"
                      + (f" ({len(manuales)} sin cuenta)" if manuales else ''))
        lineas.append(f"· Agenda: {len(eventos)} evento"
                      f"{'s' if len(eventos) != 1 else ''} por delante.")
        if not total:
            lineas += ["", "El primer paso es sumar jugadores: comparte tu código de equipo "
                           "desde la pantalla de Inicio y que se registren con él."]
        elif not eventos:
            lineas += ["", "Tienes plantilla pero la agenda está vacía. Agenda el próximo "
                           "entrenamiento para poder pasar lista y medir asistencia."]
        else:
            lineas += ["", "Con la plantilla y la agenda en marcha, el siguiente salto es "
                           "evaluar a tus jugadores: así el perfil de cada uno empieza a "
                           "moverse con datos reales."]
        return "\n".join(lineas)

    attrs = db.atributos(user.id)
    flojo = min(attrs, key=attrs.get)
    fuerte = max(attrs, key=attrs.get)
    racha = db.racha_actual(user.id)
    nombres = {'tecnica': 'técnica', 'fisico': 'físico',
               'tactico': 'táctico', 'mental': 'mental'}

    lineas = [f"{nombre}, esto es lo que dicen tus números:", ""]
    lineas.append(f"· Tu punto fuerte es lo {nombres[fuerte]} ({attrs[fuerte]}/100).")
    lineas.append(f"· Donde más margen tienes es en lo {nombres[flojo]} ({attrs[flojo]}/100).")
    if racha:
        lineas.append(f"· Llevas {racha} día{'s' if racha != 1 else ''} seguidos cumpliendo hábitos. "
                      "Esa constancia es la que termina marcando la diferencia.")
    else:
        lineas.append("· Todavía no tienes racha de hábitos. Empieza por uno solo, "
                      "el más fácil de cumplir, y encadena días.")
    lineas += ["", f"Mi consejo: dedica esta semana un bloque corto a lo {nombres[flojo]}, "
                   "aunque sean 15 minutos al final de cada entreno. Lo pequeño y sostenido "
                   "gana a lo grande y esporádico."]
    return "\n".join(lineas)


def responder_ia(user, pregunta):
    """Punto de entrada único. Nunca lanza excepción: siempre devuelve texto."""
    try:
        texto = _gemini(_prompt(user, pregunta))
        if texto:
            return texto
    except Exception as e:
        logger.warning('IA error general: %s', e)
    return _respaldo(user, pregunta)
