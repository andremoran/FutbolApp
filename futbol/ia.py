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


def _seccion_mis_partidos(uid, coach):
    """Lo que ha hecho este jugador en partido.

    Su IA veia sus evaluaciones y sus lesiones, pero de los partidos no sabia
    nada: ni si juega, ni cuanto, ni si marca. Es lo primero que pregunta un
    chaval —«¿por que no estoy jugando?»— y no habia con que responderle.

    Sale de db.totales_de_partidos, el mismo sitio que su pantalla y que la
    ficha del entrenador, para que los tres digan lo mismo.
    """
    if not coach:
        return ['Partidos: todavia no esta en ningun equipo.']

    partidos = db.rows('fut_matches', 'ia mis partidos', coach_id=coach['id'],
                       _order='fecha', _desc=True) or []
    if not partidos:
        return ['Partidos: su equipo no tiene ninguno apuntado todavia.']

    t = db.totales_de_partidos(coach['id'], ids={uid}, partidos=partidos).get(uid)
    if not t or not t['partidos']:
        return ['Partidos del equipo: %d, pero el todavia no ha jugado ni un '
                'minuto en ninguno.' % len(partidos)]

    trozos = ['Ha jugado %d de los %d partidos del equipo'
              % (t['partidos'], len(partidos))]
    if t['titularidades']:
        trozos.append('%d de titular' % t['titularidades'])
    #  Solo si hay minutos: el entrenador apunta los goles en caliente y a
    #  veces no escribe los minutos, y «0 minutos en total» se lee como que no
    #  jugo cuando en realidad marco.
    if t['minutos']:
        trozos.append('%d minutos en total (%d por partido)'
                      % (t['minutos'], round(t['minutos'] / t['partidos'])))
    for n, uno, varios in ((t['goles'], 'gol', 'goles'),
                           (t['asistencias'], 'asistencia', 'asistencias'),
                           (t['jugadas_clave'], 'jugada clave', 'jugadas clave')):
        if n:
            trozos.append('%d %s' % (n, uno if n == 1 else varios))
    if t['tarjetas_a'] or t['tarjetas_r']:
        trozos.append('%d amarilla(s) y %d roja(s)'
                      % (t['tarjetas_a'], t['tarjetas_r']))
    return ['En partido: ' + ', '.join(trozos) + '.']


def _seccion_mi_asistencia(uid):
    """Si viene a entrenar, y si llega a su hora.

    Va aparte de los partidos porque responde a otra pregunta, y porque suele
    ser la explicacion de la primera: al que falta tres semanas seguidas no le
    hace falta que la IA le adivine por que no juega.
    """
    marcas = db.q(
        lambda: db.sb().table('fut_attendance').select('estado')
        .eq('player_id', uid).execute().data or [], [], 'mi asistencia')
    if not marcas:
        return []

    from collections import Counter
    c = Counter((m.get('estado') or 'sin marcar') for m in marcas)
    total = len(marcas)
    vino = c.get('presente', 0) + c.get('tarde', 0)
    partes = ['Asistencia a entrenamientos: vino a %d de %d sesiones (%d%%)'
              % (vino, total, round(100 * vino / total))]
    detalle = []
    for clave, uno, varios in (('tarde', 'vez llego tarde', 'veces llego tarde'),
                               ('ausente', 'falta sin justificar', 'faltas sin justificar'),
                               ('justificado', 'falta justificada', 'faltas justificadas')):
        n = c.get(clave)
        if n:
            detalle.append('%d %s' % (n, uno if n == 1 else varios))
    if detalle:
        partes[0] += ': ' + ', '.join(detalle)
    partes[0] += '.'
    return partes


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

    #  Su ficha completa y su parte medico. Sin esto la IA le contestaba con
    #  los cuatro atributos de siempre y sin saber su edad ni si esta lesionado
    #  — y «¿puedo entrenar hoy?» es de lo que mas se pregunta.
    ficha = db.ficha_atributos(player_id=uid) or {}
    medica = db.ficha_medica(player_id=uid) or {}
    yo = db.one('usuarios', 'ia yo', id=uid) or {}
    edad = db.edad_de(yo.get('fecha_nacimiento'), yo.get('anio_nacimiento'))

    partes = [
        f"Nombre: {getattr(user, 'name', '') or 'jugador'}",
        f"Posición: {perfil.get('posicion') or 'sin definir'}",
    ]
    if edad is not None:
        partes.append(f"Edad: {edad} años")
    if ficha.get('_tiene_perfil'):
        partes.append(
            f"Perfil dinamico: overall {ficha['overall']}, potencial {ficha['potencial']} "
            f"(tecnica {ficha['media_tecnica']}, fisico {ficha['media_fisica']}, "
            f"mental {ficha['media_mental']})")
        flojo = min(db.ATRIBUTOS_18, key=lambda k: ficha.get(k) if ficha.get(k) is not None else 999)
        fuerte = max(db.ATRIBUTOS_18, key=lambda k: ficha.get(k) if ficha.get(k) is not None else -1)
        partes.append(f"Su mejor atributo es {fuerte} ({ficha.get(fuerte)}) y el mas flojo "
                      f"{flojo} ({ficha.get(flojo)})")
    else:
        partes.append('Perfil dinamico: todavia sin evaluar')

    #  Los cuatro atributos SOLO si esta evaluado. `db.atributos()` devuelve 50
    #  en todo cuando no hay nada, como punto de partida neutro, y pasarselos a
    #  la IA justo debajo de «todavia sin evaluar» es contradecirse: la IA se
    #  cree los cincuenta y le habla al chaval de un nivel que nadie ha medido.
    #  Es el mismo 50 inventado que se quito de la cabecera de su perfil.
    if db.fila_atributos(player_id=uid):
        partes.append(
            f"Atributos (0-100): técnica {attrs['tecnica']}, físico {attrs['fisico']}, "
            f"táctico {attrs['tactico']}, mental {attrs['mental']}")
    else:
        partes.append('Todavia no tiene ninguna nota puesta: no le hables de su '
                      'nivel como si estuviera medido.')

    fatiga = db.nivel_de_fatiga(ficha.get('fatiga'))
    if fatiga:
        partes.append(f"Fatiga declarada: {fatiga}")
    if (ficha.get('riesgo_sobrecarga') or 'bajo') != 'bajo':
        partes.append(f"Riesgo de sobrecarga: {ficha['riesgo_sobrecarga']}")

    partes += [
        f"Racha de hábitos: {db.racha_actual(uid)} días",
        f"Hábitos activos: {len(habitos)}",
        f"Entrenamientos registrados en los últimos días: {len(entrenos)}",
    ]

    # ─── Su parte médico ────────────────────────────────────────────────────
    lesiones = [x for x in (db.rows('fut_injuries', 'ia mis lesiones', player_id=uid) or [])
                if (x.get('estado') or '') not in ('alta', 'recuperado')]
    partes += _lista('Lesiones abiertas:', [
        ', '.join(t for t in (x.get('zona'), x.get('tipo'), x.get('gravedad'),
                              ('desde %s' % x['fecha']) if x.get('fecha') else None) if t)
        for x in lesiones], 5)
    ojo = [t for t in ((medica.get('alergias') or '').strip(),
                       (medica.get('condiciones') or '').strip(),
                       (medica.get('medicacion') or '').strip())
           if t and t.lower() not in ('ninguna', 'ninguno', 'no', '-')]
    if ojo:
        partes.append('Ficha medica: ' + '; '.join(ojo))
    if medica.get('apto_competir') is False:
        partes.append('ATENCION: figura como NO apto para competir.')
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

    # ─── Competicion y compromiso ───────────────────────────────────────────
    #  Lo mismo que ve su entrenador sobre el, para que las dos IA no le
    #  cuenten historias distintas al chaval y al coach.
    partes += _seccion_mis_partidos(uid, db.entrenador_del_jugador(uid))
    partes += _seccion_mi_asistencia(uid)

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


def _fichas_de_jugadores(uid, jugadores, manuales):
    """La ficha de cada jugador: edad, perfil dinámico, estado y parte médico.

    Antes el contexto solo llevaba nombre, posición y dorsal, y las medias de
    atributos solo miraban a los jugadores CON CUENTA — así que en un equipo de
    formación, donde casi nadie la tiene, la IA no veía ni un número. Preguntar
    «¿cómo va Martín?» o «¿quién está lesionado?» no tenía respuesta posible.

    Todo se pide EN BLOQUE, no jugador a jugador: son cuatro consultas en total
    en vez de dos por cabeza. La pantalla de la IA tiene presupuesto de
    segundos, y cuarenta consultas se lo comen.
    """
    ids_reg = [j['id'] for j in jugadores]
    ids_man = [m['id'] for m in manuales]

    def _bloque(tabla, columna, ids):
        if not ids:
            return {}
        filas = db.q(
            lambda: db.sb().table(tabla).select('*').in_(columna, ids).execute().data or [],
            [], 'ia %s' % tabla)
        return {f[columna]: f for f in filas if f.get(columna)}

    attrs = dict(_bloque('fut_attributes', 'player_id', ids_reg))
    attrs.update(_bloque('fut_attributes', 'manual_player_id', ids_man))
    medico = dict(_bloque('fut_medical', 'player_id', ids_reg))
    medico.update(_bloque('fut_medical', 'manual_player_id', ids_man))

    fichas = []
    for j in jugadores:
        f = j.get('fut') or {}
        fichas.append({
            'id': j['id'], 'nombre': j.get('name'),
            'posicion': f.get('posicion'), 'dorsal': f.get('dorsal'),
            'edad': db.edad_de(j.get('fecha_nacimiento'), j.get('anio_nacimiento')),
            'sin_cuenta': False,
        })
    for m in manuales:
        fichas.append({
            'id': m['id'], 'nombre': m.get('nombre'),
            'posicion': m.get('posicion'), 'dorsal': m.get('dorsal'),
            'edad': db.edad_de(m.get('fecha_nacimiento'), m.get('anio_nacimiento')),
            'sin_cuenta': True,
        })

    for x in fichas:
        a = attrs.get(x['id']) or {}
        x['overall'] = a.get('overall')
        x['potencial'] = a.get('potencial')
        x['tecnica'], x['fisico'], x['mental'] = a.get('tecnica'), a.get('fisico'), a.get('mental')
        x['fatiga'] = db.nivel_de_fatiga(a.get('fatiga'))
        x['riesgo'] = a.get('riesgo_sobrecarga')
        x['fuerte'] = (a.get('fortalezas') or '').strip()
        x['flojo'] = (a.get('debilidades') or '').strip()
        x['medico'] = medico.get(x['id']) or {}
    return fichas


def _seccion_jugadores(fichas):
    """Una línea por jugador con lo que de verdad se le pregunta a la IA."""
    lineas = []
    for x in fichas:
        partes = [x['nombre'] or 'sin nombre']
        partes.append(x['posicion'] or 'sin posicion')
        if x['dorsal']:
            partes.append('dorsal %s' % x['dorsal'])
        if x['edad'] is not None:
            partes.append('%s años' % x['edad'])
        if x['overall'] is not None:
            partes.append('overall %s' % x['overall']
                          + ('/%s de potencial' % x['potencial'] if x['potencial'] else ''))
            medias = [('tec', x['tecnica']), ('fis', x['fisico']), ('men', x['mental'])]
            sueltas = ['%s %s' % (k, v) for k, v in medias if v is not None]
            if sueltas:
                partes.append(' '.join(sueltas))
        else:
            partes.append('sin evaluar')
        if x['fatiga'] and x['fatiga'] != 'bajo':
            partes.append('fatiga %s' % x['fatiga'])
        if x['riesgo'] and x['riesgo'] != 'bajo':
            partes.append('riesgo de sobrecarga %s' % x['riesgo'])
        lineas.append(', '.join(partes))
    return lineas


def _seccion_medica(fichas, lesiones):
    """Quién está lesionado, quién no puede competir y qué hay que tener en cuenta.

    Las lesiones se cruzan con el jugador POR SU ID: antes se listaban sueltas
    —«Isquiotibiales, moderada»— sin decir de quién, que es justo lo que se
    pregunta.
    """
    por_id = {x['id']: x for x in fichas}
    salida = []

    lineas = []
    for l in lesiones:
        duenyo = por_id.get(l.get('player_id') or l.get('manual_player_id'))
        nombre = duenyo['nombre'] if duenyo else 'jugador no identificado'
        detalle = ', '.join(p for p in (
            l.get('zona'), l.get('tipo'), l.get('gravedad'),
            ('desde %s' % l['fecha']) if l.get('fecha') else None,
            ('alta prevista %s' % l['alta_prevista']) if l.get('alta_prevista') else None,
        ) if p)
        lineas.append('%s: %s' % (nombre, detalle))
    salida += _lista('Lesionados ahora mismo (%d):' % len(lineas), lineas, 10)

    no_aptos, avisos, medidas = [], [], []
    for x in fichas:
        m = x['medico'] or {}
        apto = m.get('apto_competir')
        if apto is False or (m.get('apto') or '') in ('no_apto', 'no apto'):
            no_aptos.append(x['nombre'])
        ojo = [t for t in ((m.get('alergias') or '').strip(),
                           (m.get('condiciones') or '').strip(),
                           (m.get('medicacion') or '').strip())
               if t and t.lower() not in ('ninguna', 'ninguno', 'no', '-')]
        if ojo:
            avisos.append('%s: %s' % (x['nombre'], '; '.join(ojo)))
        if m.get('estatura_cm') or m.get('peso_kg'):
            medidas.append('%s: %s%s' % (
                x['nombre'],
                ('%s cm' % m['estatura_cm']) if m.get('estatura_cm') else '',
                (' %s kg' % m['peso_kg']) if m.get('peso_kg') else ''))

    if no_aptos:
        salida.append('NO aptos para competir: ' + ', '.join(no_aptos))
    salida += _lista('Alergias, condiciones o medicación a tener en cuenta:', avisos, 10)
    salida += _lista('Talla y peso:', medidas, 12)
    return salida


def _asistencia(uid, eventos):
    """La asistencia con sus CUATRO estados, por sesión y por jugador.

    Antes se contaban juntos «presente» y «tarde» en un solo número, que es
    justo la distinción que le importa al entrenador: quien llega tarde cinco
    veces no es lo mismo que quien no falta nunca, y con un contador único los
    dos salían igual. Se guardan por separado, con el motivo que se anotó.

    Devuelve (por_evento, por_jugador). Todo de una consulta.
    """
    ids = [e['id'] for e in eventos if e.get('id')]
    filas = db.asistencia_de(ids) if ids else []

    por_evento, por_jugador = {}, {}
    for a in filas:
        estado = a.get('estado') or 'sin marcar'
        por_evento.setdefault(a['event_id'], {}).setdefault(estado, 0)
        por_evento[a['event_id']][estado] += 1

        clave = a.get('player_id') or a.get('manual_player_id')
        if not clave:
            continue
        j = por_jugador.setdefault(clave, {
            'nombre': a.get('jugador_nombre') or '', 'total': 0,
            'presente': 0, 'tarde': 0, 'justificado': 0, 'ausente': 0,
            'motivos': []})
        j['total'] += 1
        if estado in j:
            j[estado] += 1
        if a.get('motivo'):
            j['motivos'].append('%s (%s)' % (a['motivo'], estado))
    return por_evento, por_jugador


def _resumen_asistencia(conteo):
    """«presentes 14, tarde 2, ausentes 3» — solo lo que no es cero."""
    if not conteo:
        return None
    orden = (('presente', 'presentes'), ('tarde', 'tarde'),
             ('justificado', 'justificados'), ('ausente', 'ausentes'))
    trozos = ['%d %s' % (conteo[c], et) for c, et in orden if conteo.get(c)]
    otros = sum(v for k, v in conteo.items()
                if k not in dict(orden) and v)
    if otros:
        trozos.append('%d sin marcar' % otros)
    return ', '.join(trozos) if trozos else None


def _seccion_asistencia(por_jugador, fichas):
    """Quién cumple y quién no, con nombres.

    Se ordena por los que peor van —faltas primero y despues retrasos— porque
    es lo que el entrenador busca cuando pregunta. Los que no faltan nunca se
    resumen en una linea: nombrarlos uno a uno no aporta.
    """
    if not por_jugador:
        return ['Asistencia: todavia no se ha pasado lista en ninguna sesion, '
                'asi que no hay datos de quien viene y quien no.']

    nombres = {x['id']: x['nombre'] for x in fichas}
    filas = []
    for clave, j in por_jugador.items():
        nombre = j['nombre'] or nombres.get(clave) or 'jugador'
        faltas = j['ausente'] + j['justificado']
        #  Llegar tarde es HABER VENIDO. Contando solo «presente» salia que
        #  quien llego tarde no fue al entrenamiento, que es lo contrario de lo
        #  que paso. Se separan dos cosas: si vino, y si vino puntual.
        asistio = j['presente'] + j['tarde']
        filas.append({
            'nombre': nombre, 'total': j['total'], 'tarde': j['tarde'],
            'ausente': j['ausente'], 'justificado': j['justificado'],
            'presente': j['presente'], 'asistio': asistio, 'faltas': faltas,
            'motivos': j['motivos'],
            'pct': round(100 * asistio / j['total']) if j['total'] else 0,
        })
    filas.sort(key=lambda f: (-(f['ausente'] * 2 + f['tarde']), f['nombre']))

    salida = []
    total_sesiones = max((f['total'] for f in filas), default=0)
    salida.append('Asistencia: se ha pasado lista en %d sesion(es), sobre %d jugadores.'
                  % (total_sesiones, len(filas)))

    problematicos = [f for f in filas if f['ausente'] or f['tarde'] or f['justificado']]
    perfectos = [f for f in filas if not (f['ausente'] or f['tarde'] or f['justificado'])]

    lineas = []
    for f in problematicos:
        t = ['%s: vino a %d de %d sesiones (%d%%)'
             % (f['nombre'], f['asistio'], f['total'], f['pct'])]
        if f['tarde']:
            t.append('pero %d de esas veces llego TARDE' % f['tarde'])
        if f['ausente']:
            t.append('%d falta(s) sin justificar' % f['ausente'])
        if f['justificado']:
            t.append('%d justificada(s)' % f['justificado'])
        if f['motivos']:
            t.append('motivos: ' + '; '.join(f['motivos'][:3]))
        lineas.append(', '.join(t))
    salida += _lista('Los que fallan o llegan tarde (peor primero):', lineas, 15)

    if perfectos:
        salida.append('Sin una sola falta ni retraso (%d): %s'
                      % (len(perfectos),
                         ', '.join(f['nombre'] for f in perfectos[:20])))
    return salida


def _seccion_entrenamientos(uid, n_plantilla, fichas, eventos=None):
    """Los entrenamientos con TODO lo que los describe, y la semana evaluada.

    Antes esto eran tres líneas —cuántos planes, cuántos eventos por delante y
    los títulos— así que la IA no podía responder a lo que de verdad se le
    pregunta: si la semana está bien cargada, si el reparto entre físico y
    táctico tiene sentido, o si conviene bajar el ritmo antes del partido.

    La evaluación de la semana NO se calcula aquí: se pide a
    `calendario.analisis_semana()`, que es la misma que ve el entrenador en su
    pantalla. Si se recalculara aparte, la IA y la app acabarían diciendo cosas
    distintas sobre la misma semana.
    """
    from . import calendario as cal  # aquí dentro para no cruzar importaciones

    partes = []
    hoy = db.hoy_iso()
    #  Los trae quien llama para no pedirlos otra vez: la pantalla de la IA
    #  tiene presupuesto de segundos y esta consulta la usan dos secciones.
    eventos = db.eventos_equipo(uid) or [] if eventos is None else eventos
    for e in eventos:
        e['_fecha'] = db.parse_fecha(e.get('fecha'))

    #  Quién vino a cada sesión, con los cuatro estados. En bloque.
    por_evento, por_jugador = _asistencia(uid, eventos)

    def describir(e, con_asistencia=True):
        """Una sesión con sus características, no solo su título."""
        trozos = ['%s%s' % (e.get('fecha'), ' ' + e['hora'] if e.get('hora') else '')]
        tipo = e.get('tipo') or 'evento'
        if tipo == 'entreno':
            meta = cal.ENTRENO_META.get(e.get('tipo_entreno') or 'mixto', {})
            trozos.append('entreno %s' % (meta.get('etiqueta') or 'mixto').lower())
        elif tipo == 'partido':
            trozos.append('partido' + (' vs %s' % e['rival'] if e.get('rival') else '')
                          + (' (local)' if e.get('local') else ' (visitante)'))
        else:
            trozos.append(tipo)
        trozos.append('"%s"' % (e.get('titulo') or 'sin titulo'))
        if e.get('duracion_min'):
            trozos.append('%s min' % e['duracion_min'])
        if e.get('intensidad'):
            etq = dict((c, n) for c, n, _ in cal.INTENSIDADES).get(e['intensidad'], e['intensidad'])
            trozos.append('intensidad %s' % etq.lower())
        if tipo == 'entreno':
            trozos.append('carga %s' % cal.carga_de(e))
        if e.get('lugar'):
            trozos.append('en %s' % e['lugar'])
        if e.get('estado') and e['estado'] != 'programado':
            trozos.append(e['estado'])
        if con_asistencia:
            resumen = _resumen_asistencia(por_evento.get(e['id']))
            if resumen:
                trozos.append('asistencia: %s (de %d)' % (resumen, n_plantilla))
            elif (e.get('fecha') or '') < hoy and tipo == 'entreno':
                trozos.append('sin pasar lista')
        return ', '.join(trozos)

    # ─── La semana, evaluada ────────────────────────────────────────────────
    a = cal.analisis_semana(eventos)
    partes.append('SEMANA EN CURSO (%s a %s): %d entrenamientos y %d partidos, '
                  '%d minutos, carga %d sobre un tope orientativo de 700.'
                  % (a['lunes'], a['domingo'], a['n_entrenos'], a['n_partidos'],
                     a['minutos'], a['carga']))
    if a['reparto']:
        partes.append('Reparto de la semana por tipo: ' + ', '.join(
            '%s %d min (%d%%)' % (r['etiqueta'], r['minutos'], r['pct'])
            for r in a['reparto']))
    else:
        partes.append('Reparto por tipo: las sesiones de esta semana no tienen '
                      'tipo marcado, asi que no se puede repartir.')
    if a['racha']:
        partes.append('Racha: %d dias seguidos entrenando.' % a['racha'])
    if a['proximo_partido'] is not None and a['dias_partido'] is not None:
        p = a['proximo_partido']
        partes.append('Proximo partido: %s (%s), dentro de %d dias.'
                      % (p.get('titulo') or 'partido', p.get('fecha'), a['dias_partido']))
    partes += _lista('Avisos que ya le da la app sobre esta semana:',
                     [x['texto'] for x in a['alertas']], 5)

    semana = [e for e in eventos
              if e.get('_fecha') and a['lunes'] <= e['_fecha'] <= a['domingo']]
    partes += _lista('Sesiones de esta semana, una por una:',
                     [describir(e) for e in sorted(semana, key=lambda x: x['_fecha'])], 12)

    # ─── Lo que viene y lo que ya pasó ──────────────────────────────────────
    proximos = sorted([e for e in eventos if (e.get('fecha') or '') >= hoy],
                      key=lambda x: x.get('fecha') or '')
    pasados = sorted([e for e in eventos if (e.get('fecha') or '') < hoy],
                     key=lambda x: x.get('fecha') or '', reverse=True)
    partes.append('Agenda: %d eventos por delante, %d ya celebrados.'
                  % (len(proximos), len(pasados)))
    partes += _lista('Proximos:', [describir(e, con_asistencia=False) for e in proximos], 8)
    partes += _lista('Ultimos celebrados:', [describir(e) for e in pasados], 8)

    # ─── Los planes de sesión ───────────────────────────────────────────────
    planes = db.rows('fut_training_plans', 'ia planes', coach_id=uid,
                     _order='creado', _desc=True, _limit=12) or []
    partes.append('Planes de sesion guardados: %d' % len(planes))
    lineas = []
    for p in planes:
        t = [p.get('nombre') or 'sin nombre']
        if p.get('tipo'):
            t.append(p['tipo'] + ('/' + p['subtipo'] if p.get('subtipo') else ''))
        if p.get('duracion_min'):
            t.append('%s min' % p['duracion_min'])
        if p.get('intensidad'):
            t.append('intensidad %s' % p['intensidad'])
        if p.get('carga_fisica') is not None:
            t.append('carga fisica %s/100' % p['carga_fisica'])
        if p.get('objetivo'):
            t.append('objetivo: %s' % str(p['objetivo'])[:120])
        if p.get('veces_usado'):
            t.append('usado %s veces' % p['veces_usado'])
        lineas.append(', '.join(t))
    partes += _lista('Planes:', lineas, 8)

    # ─── Quién cumple y quién no ────────────────────────────────────────────
    partes += _seccion_asistencia(por_jugador, fichas)
    return partes


def _seccion_observaciones(uid, eventos):
    """Lo que el entrenador anoto o dicto despues de cada sesion.

    Es la unica parte del contexto escrita por el propio entrenador con sus
    palabras, y hasta ahora no llegaba a la IA: se guardaba en la ficha y ahi
    se quedaba. Sin esto la IA solo veia numeros —minutos, carga, asistencia—
    y no sabia que el rondo no funciono ni que a Carlos se le vio cansado, que
    es justo lo que decide la sesion siguiente.

    Se ata cada observacion a su entreno cuando lo tiene, para que la IA pueda
    decir «el dia que hiciste fuerza pasó esto» y no leerlo todo suelto.
    """
    obs = db.rows('fut_observaciones', 'ia observaciones', coach_id=uid,
                  _order='fecha', _desc=True, _limit=12) or []
    if not obs:
        return ['Observaciones del entrenador: todavia no ha anotado ninguna '
                'sesion, asi que de lo que pasa en el campo no hay nada escrito.']

    por_id = {e['id']: e for e in eventos if e.get('id')}
    lineas = []
    for o in obs:
        ev = por_id.get(o.get('event_id'))
        cabeza = o.get('fecha') or 'sin fecha'
        if ev:
            cabeza += ' (%s)' % (ev.get('titulo') or 'entreno')
        trozos = ['%s: %s' % (cabeza, (o.get('titulo') or 'sesion'))]
        if o.get('texto'):
            trozos.append('nota del entrenador: %s' % str(o['texto'])[:600])
        #  El analisis de la IA sobre lo dictado va marcado como tal: no es lo
        #  mismo que lo dijera el entrenador a que lo dedujera una maquina.
        if o.get('analisis_ia'):
            trozos.append('lectura previa de la IA sobre esa sesion: %s'
                          % str(o['analisis_ia'])[:400])
        lineas.append(' | '.join(trozos))

    dictadas = len([o for o in obs if o.get('transcripcion')])
    cabecera = 'Observaciones del entrenador (%d, de la mas reciente a la mas antigua%s):' % (
        len(obs), ', %d dictadas por voz' % dictadas if dictadas else '')
    return _lista(cabecera, lineas, 12)


def _seccion_partidos(uid, fichas):
    """Los partidos: resultados y lo que hizo cada jugador en ellos.

    La IA veia los partidos solo como huecos en la agenda —«partido vs Emelec,
    90 min»— y nada de lo que pasaba dentro. No podia decir quien esta
    marcando, quien no esta jugando ni como va el equipo de resultados, que es
    la mitad de lo que se le pregunta a un asistente de entrenador.

    Se apoya en `db.totales_de_partidos`, el mismo sitio del que salen las
    cifras de la ficha del jugador, para que las dos cuenten lo mismo.
    """
    partidos = db.rows('fut_matches', 'ia partidos', coach_id=uid,
                       _order='fecha', _desc=True) or []
    if not partidos:
        return ['Partidos: todavia no hay ninguno con estadisticas apuntadas, '
                'asi que de lo que pasa en competicion no hay datos.']

    partes = []

    # ─── El balance ─────────────────────────────────────────────────────────
    g = e = p = gf = gc = 0
    for m in partidos:
        f, c = int(m.get('goles_favor') or 0), int(m.get('goles_contra') or 0)
        gf += f
        gc += c
        if f > c:
            g += 1
        elif f == c:
            e += 1
        else:
            p += 1
    partes.append('Partidos jugados: %d — %d ganados, %d empatados, %d perdidos. '
                  'Goles %d a favor y %d en contra.' % (len(partidos), g, e, p, gf, gc))

    # ─── Uno a uno, del mas reciente ────────────────────────────────────────
    lineas = []
    for m in partidos[:10]:
        f, c = int(m.get('goles_favor') or 0), int(m.get('goles_contra') or 0)
        signo = 'victoria' if f > c else ('empate' if f == c else 'derrota')
        t = ['%s, %s %s' % (m.get('fecha') or 'sin fecha',
                            'vs' if m.get('local') else 'en casa de',
                            m.get('rival') or 'rival')]
        t.append('%d-%d (%s)' % (f, c, signo))
        if m.get('competicion'):
            t.append(m['competicion'])
        lineas.append(', '.join(t))
    partes += _lista('Ultimos partidos:', lineas, 10)

    # ─── Lo que hizo cada uno ───────────────────────────────────────────────
    tot = db.totales_de_partidos(uid, partidos=partidos)
    if not tot:
        partes.append('De esos partidos no hay ninguna estadistica individual '
                      'apuntada: no se sabe quien jugo ni quien marco.')
        return partes

    nombres = {x['id']: x['nombre'] for x in fichas}
    filas = []
    for clave, t in tot.items():
        filas.append({
            'nombre': nombres.get(clave) or 'jugador',
            'pj': t['partidos'], 'xi': t['titularidades'], 'min': t['minutos'],
            'g': t['goles'], 'a': t['asistencias'], 'clave': t['jugadas_clave'],
            'ta': t['tarjetas_a'], 'tr': t['tarjetas_r'],
        })
    filas.sort(key=lambda f: (-f['g'], -f['a'], -f['min']))

    lineas = []
    for f in filas:
        t = ['%s: %d partido(s)' % (f['nombre'], f['pj'])]
        if f['xi']:
            t.append('%d de titular' % f['xi'])
        if f['min']:
            t.append('%d min' % f['min'])
            if f['pj']:
                t.append('%d min por partido' % round(f['min'] / f['pj']))
        #  Singular y plural escritos a mano: pegarle una «s» al final daba
        #  «2 gols» y «3 jugada claves». Lo lee una IA, pero tambien acaba
        #  saliendo en lo que ella responde.
        for n, uno, varios in ((f['g'], 'gol', 'goles'),
                               (f['a'], 'asistencia', 'asistencias'),
                               (f['clave'], 'jugada clave', 'jugadas clave')):
            if n:
                t.append('%d %s' % (n, uno if n == 1 else varios))
        if f['ta'] or f['tr']:
            t.append('%d amarilla(s), %d roja(s)' % (f['ta'], f['tr']))
        lineas.append(', '.join(t))
    partes += _lista('En partido, jugador por jugador (los mas decisivos primero):',
                     lineas, 20)

    #  Quien no esta jugando. Es de lo primero que mira un entrenador y de lo
    #  que peor se ve en una lista ordenada por goles.
    sin_jugar = [x['nombre'] for x in fichas
                 if x['id'] not in tot or not tot[x['id']]['minutos']]
    if sin_jugar:
        partes.append('Sin un solo minuto en partido (%d): %s'
                      % (len(sin_jugar), ', '.join(sin_jugar[:20])))
    return partes


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

    # ─── Quiénes son y cómo están ───────────────────────────────────────────
    fichas = _fichas_de_jugadores(uid, jugadores, manuales)
    partes.append('Jugadores (nombre, posicion, dorsal, edad, overall/potencial, '
                  'medias por familia y estado):')
    partes += _lista('', _seccion_jugadores(fichas), 30)[1:]

    # ─── La media del equipo ────────────────────────────────────────────────
    #  Sobre TODOS los jugadores, no solo los que tienen cuenta: antes se
    #  miraban solo esos y en un equipo de formacion la media salia vacia.
    overalls = [x['overall'] for x in fichas if x['overall'] is not None]
    if overalls:
        partes.append('Overall medio del equipo: %d (sobre %d jugadores evaluados de %d)'
                      % (round(sum(overalls) / len(overalls)), len(overalls), len(fichas)))
        mejor = max(fichas, key=lambda x: x['overall'] if x['overall'] is not None else -1)
        peor = min((x for x in fichas if x['overall'] is not None),
                   key=lambda x: x['overall'])
        partes.append('El mas alto es %s (%s) y el mas bajo %s (%s)'
                      % (mejor['nombre'], mejor['overall'], peor['nombre'], peor['overall']))
    sin_evaluar = [x['nombre'] for x in fichas if x['overall'] is None]
    partes += _lista('Todavia sin evaluar:', sin_evaluar, 10)

    # ─── Evaluaciones ───────────────────────────────────────────────────────
    #  Es lo que más se le pregunta y lo que antes no se le pasaba en absoluto.
    try:
        resultados = ev.enriquecer(ev.resultados_equipo(uid, 120), uid)
    except Exception as e:
        logger.warning('IA: no pude leer las evaluaciones: %s', e)
        resultados = []

    if resultados:
        partes.append(f"Evaluaciones registradas: {len(resultados)}")
        #  Devuelve una LISTA de dicts, no un diccionario. Tratarla como
        #  diccionario reventaba con AttributeError, y como responder_ia() se
        #  traga la excepcion y contesta con el respaldo local, el entrenador
        #  no veia ningun error: simplemente la IA dejaba de usar Gemini y de
        #  ver sus evaluaciones en cuanto guardaba la primera marca. Sin
        #  resultados no pasaba por aqui, asi que el fallo estuvo escondido
        #  hasta que hubo datos.
        medias = ev.medias_por_categoria(resultados) or []
        sueltas = ['%s %s/100' % (m.get('etiqueta') or m.get('clave'), m['puntaje'])
                   for m in medias if m.get('puntaje') is not None]
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

    # ─── Entrenamientos y la semana ─────────────────────────────────────────
    eventos = db.eventos_equipo(uid) or []
    partes += _seccion_entrenamientos(uid, len(jugadores) + len(manuales), fichas,
                                      eventos)
    partes += _seccion_observaciones(uid, eventos)
    partes += _seccion_partidos(uid, fichas)

    # ─── Parte médico ───────────────────────────────────────────────────────
    lesiones = [x for x in (db.rows('fut_injuries', 'ia lesiones', coach_id=uid) or [])
                if (x.get('estado') or '') not in ('alta', 'recuperado')]
    partes += _seccion_medica(fichas, lesiones)

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
    return _gemini_partes([{'text': prompt}])


def _gemini_partes(partes, max_tokens=700, temperatura=0.7, limpiar=True,
                   presupuesto=None, timeout_req=20):
    """El mismo cliente, pero admitiendo audio ademas de texto.

    Gemini acepta el audio dentro de la propia peticion (`inline_data`), asi
    que las notas de voz del entrenador se transcriben y se analizan de una
    sola vez, con la misma clave y el mismo presupuesto. No hace falta montar
    un servicio de transcripcion aparte.

    `limpiar` quita asteriscos y demas marcas de markdown: vale para lo que se
    le ensena al usuario, pero no cuando la respuesta lleva separadores que hay
    que reconocer despues.
    """
    api_key = (os.environ.get('GEMINI_API_KEY') or '').strip()
    if not api_key:
        return None

    payload = {
        'contents': [{'parts': partes}],
        'generationConfig': {
            'temperature': temperatura,
            'maxOutputTokens': max_tokens,
            # Los modelos 2.5 "piensan" y esos tokens cuentan → apagado.
            'thinkingConfig': {'thinkingBudget': 0},
        },
    }

    # Presupuesto TOTAL de la llamada. Sin él, encadenar 3 modelos con reintento
    # podía tardar minutos y morir contra el límite de la función (Vercel) o del
    # worker (gunicorn). Antes de agotarlo se corta y responde el respaldo.
    import time
    limite = time.monotonic() + (presupuesto or PRESUPUESTO_S)

    for modelo in MODELOS:
        restante = limite - time.monotonic()
        if restante < 4:
            logger.info('IA: sin tiempo para más modelos, uso el respaldo')
            break

        url = f'https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}'
        try:
            r = requests.post(url, json=payload,
                              timeout=min(timeout_req, restante))
            if r.status_code == 429 and (limite - time.monotonic()) > 8:
                time.sleep(2)
                r = requests.post(
                    url, json=payload,
                    timeout=min(timeout_req, max(4, limite - time.monotonic())))
            if r.status_code == 429:
                logger.info('IA: cuota por minuto en %s, pruebo el siguiente', modelo)
                continue
            r.raise_for_status()
            texto = r.json()['candidates'][0]['content']['parts'][0]['text']
            if limpiar:
                texto = re.sub(r'[*_`#]+', '', texto or '')
            texto = (texto or '').strip()
            if texto:
                return texto
        except Exception as e:
            logger.warning('IA %s falló: %s', modelo, e)
            continue
    return None


# ═══════════════════════════════════════════════════════════════════════════
#  NOTAS DE VOZ DEL ENTRENAMIENTO
# ═══════════════════════════════════════════════════════════════════════════
#  A pie de campo no se escribe. El entrenador dicta lo que ve y de ahi sale
#  la observacion de la sesion. Gemini hace las dos cosas en una sola llamada:
#  pasa el audio a texto y despues lo lee como entrenador. Se le piden
#  separadas con marcas para guardar cada cosa en su sitio: lo dictado tal
#  cual, y la lectura aparte.

MARCA_T = 'TRANSCRIPCION:'
MARCA_A = 'ANALISIS:'

#  Tope por peticion. Gemini admite bastante mas, pero una nota a pie de campo
#  son segundos: sin tope, un audio largo se come el presupuesto de la
#  pantalla entera y agota la cuota gratuita en dos usos.
MAX_AUDIO_MB = 8

#  Segundos para transcribir y analizar. Es una accion con su propia espera en
#  pantalla, no el chat, asi que puede permitirse mas que los 30 de aquel.
PRESUPUESTO_VOZ_S = int(os.getenv('IA_VOZ_PRESUPUESTO_S', '55'))
FORMATOS_AUDIO = ('audio/webm', 'audio/ogg', 'audio/mp4', 'audio/mpeg',
                  'audio/wav', 'audio/aac', 'audio/flac', 'audio/x-m4a')

INSTRUCCION_VOZ = """Eres el segundo entrenador. Lo que te llega son notas de voz que el entrenador principal ha dictado durante o justo despues del entrenamiento, sobre la marcha y sin pensar en la redaccion.

Haz DOS cosas, en este orden y con estas marcas exactas:

TRANSCRIPCION:
Lo que dice, transcrito en espanol. Fiel: no resumas, no le corrijas la forma
de hablar y no te inventes lo que no se entienda (pon [no se entiende]). Si
hay varias notas, separalas con un salto de linea.

ANALISIS:
Tu lectura como entrenador, de 4 a 8 lineas, sin markdown ni asteriscos:
- Que ha funcionado y que no en la sesion.
- Jugadores nombrados y que se dice de cada uno.
- Senales de carga, fatiga o molestias, si las menciona.
- Que conviene corregir o repetir en la proxima sesion.

Habla SOLO de lo que esta en el audio. Si algo no se menciona, no lo rellenes:
vale mas una lectura corta que una inventada. Si te habla de dolor o de una
lesion, recomienda pasar por el fisio y no diagnostiques."""


def analizar_notas_de_voz(audios, contexto=''):
    """Transcribe las notas dictadas y saca de ellas la lectura de la sesion.

    `audios` es una lista de (mime, datos_en_base64). Van todas en la misma
    peticion a proposito: el entrenador suele dictar a trozos —uno por
    ejercicio, otro por un jugador— y leerlos juntos permite relacionarlos,
    que es justo lo que se pierde analizandolos por separado.

    Devuelve (transcripcion, analisis). Si no hay clave o Gemini no contesta,
    devuelve (None, None) y quien llama decide: lo que el entrenador escribio
    a mano se guarda igual, que es lo que no se puede perder.
    """
    if not audios:
        return None, None

    instruccion = INSTRUCCION_VOZ
    if contexto:
        instruccion += chr(10) + chr(10) + 'DE QUE SESION SE TRATA:' + chr(10) + contexto

    partes = [{'text': instruccion}]
    for mime, datos in audios:
        partes.append({'inline_data': {'mime_type': mime, 'data': datos}})

    #  Sin limpiar: las marcas hay que poder reconocerlas despues.
    #  Margen propio: subir el audio y transcribirlo tarda mucho mas que
    #  contestar a una pregunta escrita. Con los 20 s del chat, el primer
    #  modelo se pasaba de tiempo siempre y se perdia el intento.
    salida = _gemini_partes(partes, max_tokens=1400, temperatura=0.4,
                            limpiar=False, presupuesto=PRESUPUESTO_VOZ_S,
                            timeout_req=PRESUPUESTO_VOZ_S)
    if not salida:
        return None, None
    return _partir_respuesta(salida)


def _partir_respuesta(salida):
    """Separa la transcripcion del analisis por las marcas que se pidieron.

    Si el modelo se salta el formato —pasa— se devuelve todo como analisis en
    vez de tirarlo: es mas util una respuesta mal repartida que ninguna.
    """
    limpio = re.sub(r'[*_`#]+', '', salida or '')
    arriba = limpio.upper()
    it, ia = arriba.find(MARCA_T), arriba.find(MARCA_A)

    if it == -1 and ia == -1:
        return None, limpio.strip()
    if ia == -1:
        return limpio[it + len(MARCA_T):].strip(), None
    if it == -1 or it > ia:
        return None, limpio[ia + len(MARCA_A):].strip()

    return (limpio[it + len(MARCA_T):ia].strip(),
            limpio[ia + len(MARCA_A):].strip())


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
