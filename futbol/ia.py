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


def _contexto_jugador(user):
    """Datos reales del jugador para que la respuesta no sea genérica."""
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
    return "\n".join(partes)


def _contexto_entrenador(user):
    uid = user.id
    jugadores = db.jugadores_del_entrenador(uid)
    equipo = db.equipo_del_entrenador(uid)
    eventos = db.eventos_equipo(uid, desde=db.hoy_iso())

    partes = [
        f"Entrenador: {getattr(user, 'name', '') or 'entrenador'}",
        f"Equipo: {equipo.get('nombre') or 'sin nombre'}",
        f"Jugadores en plantilla: {len(jugadores)}",
        f"Eventos próximos agendados: {len(eventos)}",
    ]
    if jugadores:
        ids = [j['id'] for j in jugadores]
        attrs = db.q(
            lambda: db.sb().table('fut_attributes').select('*').in_('player_id', ids).execute().data or [],
            [], 'ia attrs')
        if attrs:
            for k in db.ATRIBUTOS:
                vals = [a[k] for a in attrs if a.get(k) is not None]
                if vals:
                    partes.append(f"Media del equipo en {k}: {round(sum(vals)/len(vals))}")
        nombres = ", ".join(
            f"{j.get('name')} ({(j.get('fut') or {}).get('posicion') or 'sin posición'})"
            for j in jugadores[:12])
        partes.append(f"Plantilla: {nombres}")
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

    import time
    for modelo in MODELOS:
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}'
        try:
            r = requests.post(url, json=payload, timeout=40)
            if r.status_code == 429:
                time.sleep(3)
                r = requests.post(url, json=payload, timeout=40)
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
        jugadores = db.jugadores_del_entrenador(user.id)
        eventos = db.eventos_equipo(user.id, desde=db.hoy_iso())
        lineas = [f"{nombre}, esto es lo que veo hoy en tu equipo:", ""]
        lineas.append(f"· Plantilla: {len(jugadores)} jugador"
                      f"{'es' if len(jugadores) != 1 else ''} registrado"
                      f"{'s' if len(jugadores) != 1 else ''}.")
        lineas.append(f"· Agenda: {len(eventos)} evento"
                      f"{'s' if len(eventos) != 1 else ''} por delante.")
        if not jugadores:
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
