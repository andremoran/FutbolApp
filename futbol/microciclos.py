# -*- coding: utf-8 -*-
"""
futbol/microciclos.py — Planificación semanal del equipo.

Un microciclo es la semana que va de partido a partido. Es la planilla que el
cuerpo técnico imprime y cuelga: los días en columnas, las capacidades en
filas. La forma sale de una planilla real de club (Cantera Orense, «MICRO 7»).

Encima de la planilla va una capa de periodización: cada día sabe qué lugar
ocupa respecto al partido (MD-4, MD-2, MD+1…) y qué carga lleva. De ahí salen
la gráfica de carga de la semana y los avisos de la guía.

La guía resume «Los 11 principios informados por evidencia e inferidos de la
periodización de microciclos en el fútbol de élite» (Buchheit, Douchet,
Settembre, McHugh, Hader y Verheijen — Sport Performance & Science Reports,
2024, #218). El artículo se publica bajo licencia Creative Commons BY 4.0.
Aquí no se copia su texto: se destila en reglas accionables y se cita la
fuente en pantalla, que es lo que le sirve al entrenador a pie de campo.
"""
from datetime import date, datetime, timedelta, timezone

from flask import abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

import roles

from . import bp, db


def _ahora():
    return datetime.now(timezone.utc).isoformat()


def _coach_o_fuera():
    """Estas pantallas son del cuerpo técnico. Un jugador va a lo suyo."""
    if getattr(current_user, 'role', '') != 'especialista':
        return redirect(url_for('futbol.p_inicio'))
    return None


# ═══════════════════════════════════════════════════════════════════════════
#  VOCABULARIO DE LA PLANILLA
# ═══════════════════════════════════════════════════════════════════════════
#  Las cinco filas de la parte principal. Son las de la planilla del club, y
#  coinciden con cómo se piensa una sesión: qué mueve el cuerpo, qué toca el
#  balón, qué ordena al equipo, qué se ensaya y qué se le pide a la cabeza.
BLOQUES_PRINCIPALES = (
    ('fisico',      'Físico',      'activity', '#3b82f6'),
    ('tecnico',     'Técnico',     'target',   '#10b981'),
    ('tactico',     'Táctico',     'command',  '#f59e0b'),
    ('estrategico', 'Estratégico', 'flag',     '#8b5cf6'),
    ('psicologico', 'Psicológico', 'heart',    '#ec4899'),
)

#  Todo lo que se escribe de un día. El orden es el de la planilla impresa:
#  se abre, se hace el grueso repartido en las cinco filas de arriba, y se cierra.
CAMPOS_TEXTO = (
    ('inicial',     'Parte inicial'),
    ('fisico',      'Físico'),
    ('tecnico',     'Técnico'),
    ('tactico',     'Táctico'),
    ('estrategico', 'Estratégico'),
    ('psicologico', 'Psicológico'),
    ('final',       'Parte final'),
)

#  La capacidad física que manda en el día. Las cinco primeras son las de la
#  planilla del club; las otras cubren los días que esa semana no tenía.
CAPACIDADES = (
    'REGENERATIVO / PREVENTIVO',
    'FUERZA',
    'RESISTENCIA',
    'VELOCIDAD',
    'VELOCIDAD DE REACCIÓN',
    'POTENCIA',
    'AGILIDAD',
    'RECUPERACIÓN',
    'DESCANSO',
    'PARTIDO',
)

#  Nivel de carga del día. El `alto` es lo que mide la barra de la gráfica:
#  no es un dato del entrenador, es la forma de la semana de un vistazo.
CARGAS = (
    ('partido',  'Partido',   '#047857', 100),
    ('alta',     'Alta',      '#10b981',  82),
    ('media',    'Media',     '#f59e0b',  55),
    ('baja',     'Baja',      '#93c5fd',  30),
    ('descanso', 'Descanso',  '#e2e8f0',  10),
)
CARGA_META = {c: {'etiqueta': e, 'color': col, 'alto': h} for c, e, col, h in CARGAS}


# ═══════════════════════════════════════════════════════════════════════════
#  PERIODIZACIÓN: QUÉ SUGIERE LA EVIDENCIA PARA CADA DÍA
# ═══════════════════════════════════════════════════════════════════════════
#  Cada día del microciclo se nombra por su distancia al partido: MD es el
#  partido, MD+1 el día siguiente, MD-1 la víspera. Es la notación del artículo
#  y la que usa todo el mundo en el vestuario.
#
#  Para cada posición: carga sugerida, capacidad, el foco del día en una línea
#  y el principio que lo respalda (para poder enseñar el porqué, no solo el qué).
DIAS_MD = {
    'MD+1': {
        'carga': 'baja', 'capacidad': 'RECUPERACIÓN', 'fase': 'recuperacion',
        'foco': 'Recuperación, compensación de suplentes y trabajo excéntrico',
        'detalle': ('Titulares: movilidad, aeróbico suave y gimnasio de tren superior. '
                    'Aquí va también el trabajo excéntrico: hecho el día después del '
                    'partido amortigua la subida de creatina quinasa, y dejado para el '
                    'tercer día deja agujetas hasta el cuarto y el quinto. '
                    'Suplentes: la carga que no hicieron en el partido — carrera a alta '
                    'velocidad, sprints y trabajo mecánico.'),
        'principios': (3, 7),
    },
    'MD+2': {
        'carga': 'descanso', 'capacidad': 'DESCANSO', 'fase': 'recuperacion',
        'foco': 'Día libre — es el sitio con menos lesiones',
        'detalle': ('El descanso en MD+2 se asocia a 2-3 veces menos lesiones sin '
                    'contacto que ponerlo en otro día. Conviene no encadenar más de '
                    '5-6 días seguidos de entrenamiento.'),
        'principios': (2,),
    },
    'MD-5': {
        'carga': 'media', 'capacidad': 'FUERZA', 'fase': 'adquisicion',
        'foco': 'Entrada en carga — fuerza en gimnasio y aceleración',
        'detalle': ('Primer día de adquisición de las semanas largas. Ojo con el '
                    'excéntrico: contando desde el partido anterior este día es MD+3, '
                    'y ahí el excéntrico deja agujetas hasta el cuarto y quinto día. '
                    'Ese trabajo ya se hizo en MD+1.'),
        'principios': (1, 7),
    },
    'MD-4': {
        'carga': 'alta', 'capacidad': 'FUERZA', 'fase': 'adquisicion',
        'foco': 'Día duro — fuerza, aceleración y agilidad',
        'detalle': ('Primero de los dos días de adquisición. Fuerza en gimnasio y en '
                    'campo, aceleraciones y agilidad, más el grueso del volumen aeróbico. '
                    'En una semana de siete días este día es MD+3: el excéntrico no toca '
                    'aquí, se hizo en MD+1.'),
        'principios': (1, 5, 7),
    },
    'MD-3': {
        'carga': 'alta', 'capacidad': 'RESISTENCIA', 'fase': 'adquisicion',
        'foco': 'Día duro — carrera a alta velocidad y potencia aeróbica',
        'detalle': ('Aquí se acumula el grueso de la carrera a alta velocidad de la '
                    'semana. Intercalar una sesión suave entre los dos días duros '
                    'permite correr más rápido en el segundo sin llegar peor al partido.'),
        'principios': (1, 4, 5),
    },
    'MD-2': {
        'carga': 'media', 'capacidad': 'VELOCIDAD', 'fase': 'afinamiento',
        'foco': 'Velocidad máxima — el día que protege los isquiotibiales',
        'detalle': ('Correr por encima del 95% de la velocidad máxima en MD-2 se asocia '
                    'a menos lesiones de isquiotibiales en el partido. Como referencia, el '
                    'artículo propone para UN LATERAL 6-8 carreras sobre el 80%, 3 sobre el '
                    '85% y 1-2 sobre el 90-95%. Un central o un delantero no corren lo '
                    'mismo: ajusta el número a lo que ese jugador hace en partido.'),
        'principios': (6,),
    },
    'MD-1': {
        'carga': 'baja', 'capacidad': 'VELOCIDAD DE REACCIÓN', 'fase': 'afinamiento',
        'foco': 'Afinamiento — sesión corta, el jugador tiene que llegar fresco',
        'detalle': ('45 minutos rinden más que 60 o 75: la sesión larga de víspera baja '
                    'el salto y el sprint del día del partido. Nunca dos días seguidos '
                    'de carga moderada antes de jugar.'),
        'principios': (8,),
    },
    'MD': {
        'carga': 'partido', 'capacidad': 'PARTIDO', 'fase': 'partido',
        'foco': 'Partido — con activación por la mañana',
        'detalle': ('15-20 minutos por la mañana (movilidad, core, tren inferior y '
                    'agilidad reactiva) aumentan la distancia a intensidad media y alta '
                    'y los duelos, sin coste técnico.'),
        'principios': (9,),
    },
}

#  Qué días tiene cada rotación, del día siguiente al partido hasta el
#  siguiente partido. Al acortarse la semana lo primero que cae es una de las
#  sesiones duras de mitad de ciclo; con cuatro días o menos ya no cabe ninguna.
ROTACIONES = {
    8: ('MD+1', 'MD+2', 'MD-5', 'MD-4', 'MD-3', 'MD-2', 'MD-1', 'MD'),
    7: ('MD+1', 'MD+2', 'MD-4', 'MD-3', 'MD-2', 'MD-1', 'MD'),
    6: ('MD+1', 'MD+2', 'MD-3', 'MD-2', 'MD-1', 'MD'),
    5: ('MD+1', 'MD-3', 'MD-2', 'MD-1', 'MD'),
    4: ('MD+1', 'MD-2', 'MD-1', 'MD'),
    3: ('MD+1', 'MD-1', 'MD'),
}

#  Aviso propio de las semanas cortas. No es un adorno: es la diferencia entre
#  planificar una semana de siete días y una de cuatro.
AVISO_ROTACION = {
    8: 'Semana larga: cabe un día extra de adquisición (MD-5) antes de los dos duros.',
    7: 'Semana completa: las tres fases caben enteras — recuperación, adquisición y afinamiento.',
    6: 'Se pierde un día de adquisición. Concentra la carrera a alta velocidad en MD-3.',
    5: 'Ya no cabe el descanso de MD+2. Si lo necesitas, quita una sesión, no el descanso.',
    4: 'No hay hueco para una sesión de alta intensidad. Prioriza recuperar y llegar fresco.',
    3: 'Solo recuperación y activación. Aquí el descanso en MD+1 vale más que cualquier sesión.',
}

FASES = (
    ('recuperacion', 'Recuperación', '#93c5fd'),
    ('adquisicion',  'Adquisición',  '#10b981'),
    ('afinamiento',  'Afinamiento',  '#f59e0b'),
    ('partido',      'Partido',      '#047857'),
)
FASE_META = {c: {'etiqueta': e, 'color': col} for c, e, col in FASES}


# ═══════════════════════════════════════════════════════════════════════════
#  LOS 11 PRINCIPIOS
# ═══════════════════════════════════════════════════════════════════════════
#  Resumen propio y accionable de cada principio del artículo, con el dato que
#  lo sostiene. Los nueve primeros salen de estudios; los dos últimos los
#  infieren los autores desde la lógica del juego.
PRINCIPIOS = (
    {'n': 1, 'tipo': 'evidencia', 'icono': 'bar-chart-2', 'color': '#047857',
     'titulo': 'Dinámica de carga y contenido',
     'resumen': 'La semana tiene tres fases: recuperación, adquisición y afinamiento.',
     'clave': 'Tres fases',
     'detalle': ('Los primeros días tras el partido son de recuperación. Después vienen '
                 'dos días de carga fuerte (adquisición). Los dos últimos bajan volumen e '
                 'intensidad para llegar fresco. Cuando la semana se acorta, lo primero '
                 'que se quita es una de las sesiones duras de mitad de ciclo.'),
     'aplica': 'La gráfica de carga de tu microciclo debería dibujar esa forma.'},

    {'n': 2, 'tipo': 'evidencia', 'icono': 'coffee', 'color': '#0ea5e9',
     'titulo': 'Dónde va el día libre',
     'resumen': 'El descanso en MD+2 se asocia a 2-3 veces menos lesiones sin contacto.',
     'clave': 'MD+2',
     'detalle': ('Analizando 56 temporadas de 18 equipos de élite, el día libre colocado '
                 'en MD+2 (segundo día tras el partido) mostró tasas de lesión sin '
                 'contacto muy por debajo de las de cualquier otra ubicación, sobre todo '
                 'en semanas de 3 y de 7 días. Además, encadenar más de 5-6 días seguidos '
                 'de entrenamiento eleva el riesgo.'),
     'aplica': 'Marca MD+2 como descanso salvo que la semana sea de 5 días o menos.'},

    {'n': 3, 'tipo': 'evidencia', 'icono': 'users', 'color': '#8b5cf6',
     'titulo': 'Recuperación y compensación',
     'resumen': 'Titulares y suplentes no pueden entrenar lo mismo tras el partido.',
     'clave': 'Dos grupos',
     'detalle': ('Los titulares recuperan: movilidad, aeróbico suave, gimnasio de tren '
                 'superior — que es compatible con la recuperación aunque no la acelere. '
                 'Los suplentes necesitan compensar lo que no corrieron: quien juega menos '
                 'de 45 minutos y acumula poca carrera a alta velocidad en dos partidos '
                 'seguidos se lesiona más de isquiotibiales. Lo más eficaz es repartir esa '
                 'carga entre el mismo día del partido y el siguiente.'),
     'aplica': 'Escribe en MD+1 dos contenidos distintos: uno para titulares, otro para suplentes.'},

    {'n': 4, 'tipo': 'evidencia', 'icono': 'trending-up', 'color': '#f59e0b',
     'titulo': 'Carrera a alta velocidad de la semana',
     'resumen': 'Entrenar entre el 60% y el 90% de lo que se corre en partido.',
     'clave': '60-90%',
     'detalle': ('Con modelos de aprendizaje automático sobre 12 equipos y 44.000 '
                 'exposiciones, la distancia acumulada a alta velocidad en entrenamiento '
                 'entre 0,6 y 0,9 veces la del partido se asoció a menos riesgo de lesión; '
                 'en sprint, entre 0,6 y 1,1. Ni pasarse ni quedarse corto.'),
     'aplica': 'En formación y desarrollo el objetivo puede ser otro: ahí se entrena para crecer.'},

    {'n': 5, 'tipo': 'evidencia', 'icono': 'shuffle', 'color': '#10b981',
     'titulo': 'El orden de las sesiones importa',
     'resumen': 'Una sesión suave entre las dos duras deja correr más, sin coste el día del partido.',
     'clave': 'Intercalar',
     'detalle': ('Separar las dos sesiones más exigentes con una de carga baja hizo que los '
                 'jugadores recorrieran más distancia a alta velocidad en la segunda, sin '
                 'empeorar salto, sprint ni bienestar el día del partido. Colocar la sesión '
                 'de velocidad antes que la aeróbica funciona igual de bien.'),
     'aplica': 'Prueba a intercambiar MD-3 y MD-2 si tus dos días duros van pegados.'},

    {'n': 6, 'tipo': 'evidencia', 'icono': 'zap', 'color': '#ef4444',
     'titulo': 'Exposición a velocidad máxima',
     'resumen': 'Correr sobre el 95% de la velocidad máxima en MD-2 protege los isquiotibiales.',
     'clave': '>95% en MD-2',
     'detalle': ('Sobre 627 jugadores y 6.698 sesiones, las carreras por encima del 95% de '
                 'la velocidad máxima —y no las de intensidad menor— en sesiones cercanas al '
                 'partido se asociaron a menos lesiones de isquiotibiales. La referencia que '
                 'da el artículo —6-8 carreras sobre el 80%, 3 sobre el 85% y 1-2 sobre el '
                 '90-95%— está calculada para UN LATERAL: es un ejemplo, no un número para '
                 'toda la plantilla.'),
     'aplica': ('Si la semana se acorta, esta exposición es lo primero que desaparece. '
                'Vigílala, y saca el número de cada jugador de lo que corre en partido.')},

    {'n': 7, 'tipo': 'evidencia', 'icono': 'anchor', 'color': '#6366f1',
     'titulo': 'Fuerza: pronto, poco y progresivo',
     'resumen': 'El trabajo excéntrico va en MD+1, y con poco volumen basta.',
     'clave': 'MD+1',
     'detalle': ('Hacer los ejercicios excéntricos el día después del partido amortigua la '
                 'subida de creatina quinasa; hacerlos en MD+3 deja agujetas hasta el cuarto '
                 'y quinto día. Y una serie de 10 repeticiones mejoró la fuerza y la longitud '
                 'del fascículo igual que cuatro series de 40. Con bandas elásticas se puede '
                 'bajar la intensidad del nórdico entre un 15% y un 40% para introducirlo.'),
     'aplica': 'Poco volumen y temprano: cunde igual y no te hipoteca la semana.'},

    {'n': 8, 'tipo': 'evidencia', 'icono': 'trending-down', 'color': '#14b8a6',
     'titulo': 'Afinamiento antes del partido',
     'resumen': 'Nunca dos días seguidos de carga moderada. Y la víspera, 45 minutos.',
     'clave': '45 min',
     'detalle': ('Los profesionales alternan moderado y suave en los dos días previos, casi '
                 'nunca dos moderados seguidos. Una sesión de 45 minutos en MD-1 dejó mejor '
                 'salto y mejor sprint el día del partido que una de 60 o de 75. Recuperar '
                 'poco o cargar de más en esos dos días se asocia a más lesiones.'),
     'aplica': 'Si MD-2 fue moderado, MD-1 tiene que ser suave. Sin excepciones.'},

    {'n': 9, 'tipo': 'evidencia', 'icono': 'sunrise', 'color': '#f97316',
     'titulo': 'Activación la mañana del partido',
     'resumen': '15-20 minutos por la mañana mejoran el rendimiento físico del partido.',
     'clave': '15-20 min',
     'detalle': ('Estiramientos, movilidad, core, resistencia de tren inferior y agilidad '
                 'reactiva la mañana del partido aumentaron la distancia recorrida a '
                 'intensidad media y alta y la cantidad de duelos, sin perjudicar nada del '
                 'rendimiento técnico.'),
     'aplica': 'Que la activación no se convierta en una sesión: el objetivo sigue siendo llegar fresco.'},

    {'n': 10, 'tipo': 'inferido', 'icono': 'wind', 'color': '#64748b',
     'titulo': 'Correr es parte del fútbol',
     'resumen': 'Los objetivos de carrera son una herramienta, no la meta del entrenamiento.',
     'clave': 'Con balón',
     'detalle': ('Los metros a alta velocidad y las exposiciones a velocidad máxima se '
                 'consiguen dentro de tareas de fútbol bien diseñadas, con balón e '
                 'interacción entre jugadores. Medirlos sirve para afinar la sesión, no '
                 'para sustituirla por carrera aislada.'),
     'aplica': 'Antes de añadir series sueltas, mira si la tarea con balón ya te da esos metros.'},

    {'n': 11, 'tipo': 'inferido', 'icono': 'refresh-cw', 'color': '#94a3b8',
     'titulo': 'Abrazar el caos',
     'resumen': 'Planifica el ideal, y luego adapta con criterio.',
     'clave': 'Adaptar',
     'detalle': ('Viajes, clima, cambios de horario, jugadores tocados: el plan perfecto se '
                 'rompe todas las semanas. Tener el microciclo ideal escrito es justo lo que '
                 'permite decidir bien cuando hay que cambiarlo, porque sabes qué estás '
                 'sacrificando y por qué.'),
     'aplica': 'Guarda el plan aunque sepas que va a cambiar. Es tu punto de referencia.'},
)

FUENTE = {
    'titulo': ('Los 11 principios informados por evidencia e inferidos de la '
               'periodización de microciclos en el fútbol de élite'),
    'autores': ('Buchheit M, Douchet T, Settembre M, McHugh D, Hader K, Verheijen R'),
    'publicacion': 'Sport Performance & Science Reports, 2024, Febrero, #218, v1',
    'licencia': 'Creative Commons BY 4.0',
    'url': 'https://sportperfsci.com',
}


# ═══════════════════════════════════════════════════════════════════════════
#  ARMAR Y LEER UN MICROCICLO
# ═══════════════════════════════════════════════════════════════════════════
DIAS_SEMANA = ('LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES', 'SÁBADO', 'DOMINGO')


def etiqueta_fecha(f):
    """'LUNES 11' — como se rotula la columna en la planilla impresa."""
    if not f:
        return ''
    return f'{DIAS_SEMANA[f.weekday()]} {f.day}'


def plantilla(rotacion, desde=None):
    """Los días que sugiere la evidencia para una rotación, ya rellenos.

    Es el punto de partida del planificador: el entrenador abre un microciclo
    nuevo y ya tiene la forma de la semana puesta, con la carga y la capacidad
    de cada día. Encima escribe lo suyo.
    """
    rotacion = rotacion if rotacion in ROTACIONES else 7
    desde = desde or date.today()
    salida = []
    for i, md in enumerate(ROTACIONES[rotacion]):
        guia = DIAS_MD[md]
        f = desde + timedelta(days=i)
        salida.append({
            'fecha': f.isoformat(),
            'etiqueta': etiqueta_fecha(f),
            'md': md,
            'carga': guia['carga'],
            'capacidad': guia['capacidad'],
            'lugar': '', 'hora': '', 'duracion': 0,
            'inicial': '', 'fisico': '', 'tecnico': '', 'tactico': '',
            'estrategico': '', 'psicologico': '', 'final': '',
        })
    return salida


def decorar(micro):
    """Añade a cada día lo que la plantilla necesita para pintarlo.

    Nada de esto se guarda: son la carga, la fase y el consejo del día,
    derivados de su posición respecto al partido.
    """
    dias = micro.get('dias') or []
    for d in dias:
        guia = DIAS_MD.get(d.get('md') or '', {})
        carga = d.get('carga') if d.get('carga') in CARGA_META else guia.get('carga', 'baja')
        d['_carga'] = CARGA_META.get(carga, CARGA_META['baja'])
        d['_carga_clave'] = carga
        d['_fase'] = FASE_META.get(guia.get('fase', 'adquisicion'), FASE_META['adquisicion'])
        d['_foco'] = guia.get('foco', '')
        d['_detalle'] = guia.get('detalle', '')
        d['_principios'] = guia.get('principios', ())
        #  Un día se considera escrito si tiene algo en cualquiera de sus
        #  bloques. Sirve para la barra de «cuánto llevas planificado».
        d['_escrito'] = any((d.get(k) or '').strip() for k, _ in CAMPOS_TEXTO)

    micro['_dias'] = dias
    micro['_rotacion'] = micro.get('rotacion') or len(dias) or 7
    micro['_aviso'] = AVISO_ROTACION.get(micro['_rotacion'], '')
    micro['_escritos'] = sum(1 for d in dias if d['_escrito'])
    micro['_desde'] = db.parse_fecha(micro.get('desde'))
    micro['_hasta'] = db.parse_fecha(micro.get('hasta'))
    #  Minutos de la semana: solo cuentan los días con duración puesta.
    micro['_minutos'] = sum(int(d.get('duracion') or 0) for d in dias)
    return micro


def _revisar(dias):
    """Los avisos de la guía sobre ESTE microciclo, no sobre el ideal.

    Es la parte que convierte la guía en algo útil: en vez de leer once
    principios, el entrenador ve qué se está saltando en la semana que acaba
    de escribir.
    """
    avisos = []
    por_md = {d.get('md'): d for d in dias}
    cargas = [d.get('carga') for d in dias]

    #  Se calcula aquí y no se lee `_escrito`: esa marca solo la pone
    #  `decorar()`, y a esta función también se la llama al guardar, cuando los
    #  días vienen recién limpiados y todavía no la tienen.
    def texto_de(dia):
        return ' '.join((dia.get(k) or '') for k, _ in CAMPOS_TEXTO).strip()

    #  Principio 2 — el día libre
    if 'MD+2' in por_md and por_md['MD+2'].get('carga') != 'descanso':
        avisos.append({'nivel': 'aviso', 'principio': 2,
                       'texto': 'MD+2 no está como descanso. Es donde menos lesiones se registran.'})
    if len(dias) >= 6 and 'descanso' not in cargas:
        avisos.append({'nivel': 'aviso', 'principio': 2,
                       'texto': 'La semana no tiene ningún día libre. Más de 5-6 días seguidos eleva el riesgo.'})

    #  Principio 8 — dos moderados seguidos antes del partido
    md2, md1 = por_md.get('MD-2'), por_md.get('MD-1')
    if md2 and md1 and md2.get('carga') in ('media', 'alta') and md1.get('carga') in ('media', 'alta'):
        avisos.append({'nivel': 'alerta', 'principio': 8,
                       'texto': 'MD-2 y MD-1 llevan carga seguida. Uno de los dos tiene que aflojar.'})

    #  Principio 6 — la exposición a velocidad máxima
    if md2 is not None:
        texto = texto_de(md2).lower()
        if md2.get('capacidad') != 'VELOCIDAD' and 'velocidad' not in texto:
            avisos.append({'nivel': 'aviso', 'principio': 6,
                           'texto': 'En MD-2 no aparece trabajo de velocidad máxima. Es el día que protege los isquiotibiales.'})

    #  Principio 5 — los dos días duros pegados
    duros = [i for i, d in enumerate(dias) if d.get('carga') == 'alta']
    if len(duros) >= 2 and any(b - a == 1 for a, b in zip(duros, duros[1:])):
        avisos.append({'nivel': 'info', 'principio': 5,
                       'texto': 'Tus dos días duros van seguidos. Intercalar uno suave deja correr más en el segundo.'})

    #  Principio 7 — el excéntrico en el tercer día tras el partido
    #  MD-4 (semana de 7) y MD-5 (semana de 8) SON el tercer día tras el
    #  partido anterior. Es el error fácil de cometer: se piensa «falta mucho
    #  para el partido» y se olvida que hace tres días hubo otro.
    for md in ('MD-4', 'MD-5'):
        dia = por_md.get(md)
        if dia is not None and 'excéntric' in texto_de(dia).lower():
            avisos.append({'nivel': 'alerta', 'principio': 7,
                           'texto': ('Hay trabajo excéntrico en %s, que es el tercer día '
                                     'tras el partido anterior. Ahí deja agujetas hasta el '
                                     'cuarto y quinto día: pásalo a MD+1.' % md)})

    #  Principio 3 — los suplentes
    md_mas_1 = por_md.get('MD+1')
    if md_mas_1 is not None and texto_de(md_mas_1):
        texto = texto_de(md_mas_1).lower()
        if not any(p in texto for p in ('suplent', 'compensa', 'no convocad', 'banca')):
            avisos.append({'nivel': 'info', 'principio': 3,
                           'texto': 'En MD+1 no se ve la compensación de los suplentes. Ellos necesitan lo contrario que los titulares.'})

    return avisos


# ═══════════════════════════════════════════════════════════════════════════
#  PANTALLAS
# ═══════════════════════════════════════════════════════════════════════════
@bp.route('/coach/microciclos')
@login_required
@roles.solo_pro('planes')
def c_microciclos():
    """La lista de microciclos del equipo."""
    fuera = _coach_o_fuera()
    if fuera:
        return fuera
    uid = db.equipo_id(current_user.id)
    micros = db.rows('fut_microcycles', 'microciclos', coach_id=uid,
                     _order='desde', _desc=True) or []
    for m in micros:
        decorar(m)
    return render_template('c_microciclos.html',
                           tab_activa='agenda', hide_tabbar=True,
                           micros=micros,
                           rotaciones=sorted(ROTACIONES, reverse=True),
                           avisos_rotacion=AVISO_ROTACION,
                           hoy=date.today().isoformat())


@bp.route('/coach/microciclos/<mid>')
@login_required
@roles.solo_pro('planes')
def c_microciclo(mid):
    """El planificador: la semana entera, editable."""
    fuera = _coach_o_fuera()
    if fuera:
        return fuera
    uid = db.equipo_id(current_user.id)
    micro = db.one('fut_microcycles', 'microciclo', id=mid, coach_id=uid)
    if not micro:
        abort(404)
    decorar(micro)
    return render_template('c_microciclo.html',
                           tab_activa='agenda', hide_tabbar=True,
                           micro=micro,
                           campos=CAMPOS_TEXTO,
                           bloques=BLOQUES_PRINCIPALES,
                           capacidades=CAPACIDADES,
                           cargas=CARGAS,
                           dias_md=DIAS_MD,
                           rotaciones=sorted(ROTACIONES, reverse=True),
                           principios=PRINCIPIOS,
                           avisos=_revisar(micro['_dias']),
                           fuente=FUENTE)


@bp.route('/coach/microciclos/guia')
@login_required
@roles.solo_pro('planes')
def c_microciclo_guia():
    """Los 11 principios, en limpio."""
    fuera = _coach_o_fuera()
    if fuera:
        return fuera
    #  Las cinco rotaciones dibujadas con su carga día a día: es la figura que
    #  resume el artículo entero y la que de verdad se consulta.
    formas = []
    for r in sorted(ROTACIONES, reverse=True):
        formas.append({
            'rotacion': r,
            'aviso': AVISO_ROTACION.get(r, ''),
            'dias': [{'md': md,
                      'carga': CARGA_META[DIAS_MD[md]['carga']],
                      'fase': FASE_META[DIAS_MD[md]['fase']],
                      'foco': DIAS_MD[md]['foco']}
                     for md in ROTACIONES[r]],
        })
    return render_template('c_microciclo_guia.html',
                           tab_activa='agenda', hide_tabbar=True,
                           principios=PRINCIPIOS,
                           formas=formas,
                           fases=FASES,
                           dias_md=DIAS_MD,
                           fuente=FUENTE)


# ═══════════════════════════════════════════════════════════════════════════
#  API
# ═══════════════════════════════════════════════════════════════════════════
def _guardia_coach():
    from .api import csrf_ok
    if not csrf_ok():
        return jsonify({'error': 'La sesión expiró. Recarga la página.'}), 400
    if getattr(current_user, 'role', '') != 'especialista':
        return jsonify({'error': 'Solo el cuerpo técnico planifica la semana.'}), 403
    if not roles.es_pro(current_user):
        return jsonify({'error': 'La planificación semanal es del plan Pro.',
                        'pro': True, 'url': url_for('futbol.planes')}), 402
    return None


def _minutos(v):
    """Los minutos de una sesión, venga como venga.

    El formulario manda un número, pero el servidor no puede fiarse de eso: un
    «90 min» escrito a mano reventaba la petición ENTERA y el entrenador perdía
    la semana que acababa de escribir por un campo.
    """
    try:
        return max(0, min(300, int(float(str(v).strip() or 0))))
    except (TypeError, ValueError):
        return 0


def _limpiar_dia(d):
    """Un día tal y como se guarda. Todo recortado y dentro de su vocabulario."""
    md = d.get('md') if d.get('md') in DIAS_MD else ''
    carga = d.get('carga') if d.get('carga') in CARGA_META else 'baja'
    salida = {
        'fecha': (d.get('fecha') or '')[:10],
        'etiqueta': (d.get('etiqueta') or '').strip()[:40],
        'md': md,
        'carga': carga,
        #  La capacidad admite texto libre a propósito: CAPACIDADES son las
        #  sugerencias, no una lista cerrada — cada cuerpo técnico tiene su
        #  vocabulario y no se le va a corregir.
        'capacidad': (d.get('capacidad') or '').strip()[:60],
        'lugar': (d.get('lugar') or '').strip()[:80],
        'hora': (d.get('hora') or '').strip()[:5],
        'duracion': _minutos(d.get('duracion')),
    }
    for clave, _ in CAMPOS_TEXTO:
        salida[clave] = (d.get(clave) or '').strip()[:600]
    return salida


@bp.route('/api/microciclo', methods=['POST'])
@login_required
def api_microciclo():
    """Crea o actualiza un microciclo entero.

    Siempre llega la semana completa: un microciclo se lee y se escribe de una
    pieza, como la planilla que representa.
    """
    error = _guardia_coach()
    if error:
        return error

    d = request.get_json(silent=True) or {}
    uid = db.equipo_id(current_user.id)

    nombre = (d.get('nombre') or '').strip()
    if len(nombre) < 3:
        return jsonify({'error': 'Ponle un nombre al microciclo.'}), 400

    try:
        rotacion = int(d.get('rotacion') or 7)
    except (TypeError, ValueError):
        rotacion = 7
    rotacion = rotacion if rotacion in ROTACIONES else 7

    dias = [_limpiar_dia(x) for x in (d.get('dias') or [])[:8]]
    if not dias:
        dias = plantilla(rotacion, db.parse_fecha(d.get('desde')))

    #  El rango de fechas sale de los días: es un dato derivado y así no puede
    #  contradecir a la planilla.
    fechas = sorted(f for f in (x['fecha'] for x in dias) if f)

    datos = {
        'nombre': nombre[:120],
        'lugar': (d.get('lugar') or '').strip()[:120],
        'rotacion': rotacion,
        'dias': dias,
        'desde': fechas[0] if fechas else None,
        'hasta': fechas[-1] if fechas else None,
        'recomendaciones': (d.get('recomendaciones') or '').strip()[:1200],
        'observaciones': (d.get('observaciones') or '').strip()[:1200],
        'cuerpo_tecnico': (d.get('cuerpo_tecnico') or '').strip()[:300],
        'actualizado': _ahora(),
    }

    mid = d.get('id')
    if mid:
        if not db.one('fut_microcycles', 'micro mio', id=mid, coach_id=uid):
            return jsonify({'error': 'Ese microciclo no es tuyo.'}), 403
        db.update('fut_microcycles', datos, 'micro up', id=mid, coach_id=uid,
                  obligatorio=True)
        return jsonify({'ok': True, 'id': mid, 'mensaje': 'Microciclo guardado.',
                        'avisos': _revisar(dias)})

    datos.update({'coach_id': uid, 'creado': _ahora()})
    fila = db.insert('fut_microcycles', datos, 'micro nuevo')
    if not fila:
        return jsonify({'error': 'No se pudo guardar el microciclo.'}), 500
    return jsonify({'ok': True, 'id': fila['id'], 'mensaje': 'Microciclo creado.',
                    'redirect': url_for('futbol.c_microciclo', mid=fila['id'])})


@bp.route('/api/microciclo/nuevo', methods=['POST'])
@login_required
def api_microciclo_nuevo():
    """Crea un microciclo ya con la forma que sugiere la evidencia."""
    error = _guardia_coach()
    if error:
        return error

    d = request.get_json(silent=True) or {}
    uid = db.equipo_id(current_user.id)
    try:
        rotacion = int(d.get('rotacion') or 7)
    except (TypeError, ValueError):
        rotacion = 7
    rotacion = rotacion if rotacion in ROTACIONES else 7

    desde = db.parse_fecha(d.get('desde')) or date.today()
    dias = plantilla(rotacion, desde)
    equipo = db.equipo_del_entrenador(uid) or {}

    fila = db.insert('fut_microcycles', {
        'coach_id': uid,
        'nombre': (d.get('nombre') or '').strip()[:120] or f'Microciclo {desde.strftime("%d/%m")}',
        'lugar': (d.get('lugar') or '').strip()[:120] or (equipo.get('nombre') or ''),
        'rotacion': rotacion,
        'dias': dias,
        'desde': dias[0]['fecha'],
        'hasta': dias[-1]['fecha'],
        'creado': _ahora(),
    }, 'micro plantilla')
    if not fila:
        return jsonify({'error': 'No se pudo crear el microciclo.'}), 500
    return jsonify({'ok': True, 'id': fila['id'],
                    'redirect': url_for('futbol.c_microciclo', mid=fila['id'])})


@bp.route('/api/microciclo/<mid>', methods=['DELETE'])
@login_required
def api_microciclo_borrar(mid):
    error = _guardia_coach()
    if error:
        return error
    db.delete('fut_microcycles', 'borrar micro', id=mid,
              coach_id=db.equipo_id(current_user.id), obligatorio=True)
    return jsonify({'ok': True, 'mensaje': 'Microciclo borrado.'})


@bp.route('/api/microciclo/<mid>/agendar', methods=['POST'])
@login_required
def api_microciclo_agendar(mid):
    """Vuelca la semana al calendario: un evento por día escrito.

    Es lo que cierra el círculo — el microciclo deja de ser una hoja y pasa a
    ser la agenda real del equipo, con su asistencia y sus estadísticas.
    """
    error = _guardia_coach()
    if error:
        return error

    uid = db.equipo_id(current_user.id)
    micro = db.one('fut_microcycles', 'micro agendar', id=mid, coach_id=uid)
    if not micro:
        return jsonify({'error': 'Ese microciclo no es tuyo.'}), 404

    creados = 0
    for d in (micro.get('dias') or []):
        fecha = (d.get('fecha') or '')[:10]
        if not fecha or d.get('carga') == 'descanso':
            continue

        #  Solo se agendan los días con contenido: un día en blanco en la
        #  planilla no es una sesión, es un hueco por rellenar.
        cuerpo = [f'{etiqueta}: {d[clave].strip()}'
                  for clave, etiqueta in CAMPOS_TEXTO if (d.get(clave) or '').strip()]
        if not cuerpo:
            continue

        es_partido = d.get('md') == 'MD'
        fila = db.insert('fut_events', {
            'coach_id': uid,
            'tipo': 'partido' if es_partido else 'entreno',
            'titulo': (f'{micro["nombre"]} · {d.get("md") or ""}').strip()[:120],
            'fecha': fecha,
            'hora': (d.get('hora') or '')[:5] or None,
            'lugar': (d.get('lugar') or micro.get('lugar') or '')[:120],
            'descripcion': ('\n'.join(cuerpo))[:1200],
            'duracion_min': int(d.get('duracion') or 0) or 90,
            'intensidad': {'partido': 'muy_alta', 'alta': 'alta', 'media': 'media',
                           'baja': 'baja', 'descanso': 'baja'}.get(d.get('carga'), 'media'),
            'estado': 'programado',
            'creado': _ahora(),
        }, 'evento del microciclo')
        if fila:
            creados += 1

    if not creados:
        return jsonify({'error': 'No hay ningún día escrito para agendar todavía.'}), 400
    return jsonify({'ok': True, 'n': creados,
                    'mensaje': f'{creados} sesión(es) en el calendario.',
                    'redirect': url_for('futbol.c_calendario')})
