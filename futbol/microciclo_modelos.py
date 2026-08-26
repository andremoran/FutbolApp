# -*- coding: utf-8 -*-
"""
futbol/microciclo_modelos.py — Una periodización por segmento.

`microciclos.py` es el motor: la planilla, el guardado, la gráfica, el volcado
al calendario. Aquí está lo que ese motor lee — y lo que cambia de verdad de un
segmento a otro:

  · qué días tiene la semana y qué se hace en cada uno   (`dias`, `rotaciones`)
  · cómo se llaman las filas de la planilla              (`campos`, `bloques`)
  · qué principios respaldan el plan                     (`principios`)
  · qué avisos se le dan sobre LA SEMANA QUE ESCRIBIÓ    (`revisar`)

Las CLAVES de todo lo que se guarda son las mismas en los tres modelos
(`inicial`, `fisico`, `tecnico`, `tactico`, `estrategico`, `psicologico`,
`final`); lo que cambia es la etiqueta. Así un entrenador puede pasar del
segmento de colegio al de semipro sin perder una línea de lo que había escrito:
la columna «Juego reducido» pasa a llamarse «Táctico» y el texto sigue ahí.

Los tres modelos existen por el mismo motivo. Un plan que no se puede cumplir
no se cumple a medias: se ignora entero, incluida la parte que sí servía. Un
profesor de colegio al que se le dice que su MD-2 debe llevar carreras por
encima del 95% de la velocidad máxima cierra la guía y no vuelve. Y con ella se
va también lo que de verdad le habría cambiado la temporada, que era el
calentamiento preventivo y la regla de las horas semanales.
"""

# ═══════════════════════════════════════════════════════════════════════════
#  VOCABULARIO COMÚN
# ═══════════════════════════════════════════════════════════════════════════
#  Todo lo que se escribe de un día. El orden es el de la planilla impresa: se
#  abre, se hace el grueso repartido en cinco bloques, y se cierra. Las claves
#  son las columnas de `fut_microcycles.dias` y NO cambian nunca.
CLAVES_CAMPOS = ('inicial', 'fisico', 'tecnico', 'tactico',
                 'estrategico', 'psicologico', 'final')

#  Nivel de carga del día. El `alto` es lo que mide la barra de la gráfica: no
#  es un dato del entrenador, es la forma de la semana de un vistazo.
CARGAS_BASE = (
    ('partido',  'Partido',   '#047857', 100),
    ('alta',     'Alta',      '#10b981',  82),
    ('media',    'Media',     '#f59e0b',  55),
    ('baja',     'Baja',      '#93c5fd',  30),
    ('descanso', 'Descanso',  '#e2e8f0',  10),
)

FASES_BASE = (
    ('recuperacion', 'Recuperación', '#93c5fd'),
    ('adquisicion',  'Adquisición',  '#10b981'),
    ('afinamiento',  'Afinamiento',  '#f59e0b'),
    ('partido',      'Partido',      '#047857'),
)


def texto_de(dia, campos=CLAVES_CAMPOS):
    """Todo lo escrito en un día, junto. Para buscar palabras dentro.

    Se calcula aquí y no se lee `_escrito`: esa marca solo la pone `decorar()`,
    y a `revisar` también se la llama al guardar, cuando los días vienen recién
    limpiados y todavía no la tienen.
    """
    return ' '.join((dia.get(k) or '') for k in campos).strip()


def _menciona(dia, *palabras):
    t = texto_de(dia).lower()
    return any(p in t for p in palabras)


# ═══════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════
#  SEGMENTO 3 · PROFESIONAL
# ═══════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════
#  La periodización del fútbol de élite, tal y como estaba. No se ha tocado una
#  coma: es la que respalda la evidencia y es la que ya usan los equipos que
#  están dentro de la app.
#
#  Cada día se nombra por su distancia al partido: MD es el partido, MD+1 el
#  día siguiente, MD-1 la víspera. Es la notación del artículo y la que se usa
#  en el vestuario.
PRO_DIAS = {
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
PRO_ROTACIONES = {
    8: ('MD+1', 'MD+2', 'MD-5', 'MD-4', 'MD-3', 'MD-2', 'MD-1', 'MD'),
    7: ('MD+1', 'MD+2', 'MD-4', 'MD-3', 'MD-2', 'MD-1', 'MD'),
    6: ('MD+1', 'MD+2', 'MD-3', 'MD-2', 'MD-1', 'MD'),
    5: ('MD+1', 'MD-3', 'MD-2', 'MD-1', 'MD'),
    4: ('MD+1', 'MD-2', 'MD-1', 'MD'),
    3: ('MD+1', 'MD-1', 'MD'),
}

PRO_AVISO_ROTACION = {
    8: 'Semana larga: cabe un día extra de adquisición (MD-5) antes de los dos duros.',
    7: 'Semana completa: las tres fases caben enteras — recuperación, adquisición y afinamiento.',
    6: 'Se pierde un día de adquisición. Concentra la carrera a alta velocidad en MD-3.',
    5: 'Ya no cabe el descanso de MD+2. Si lo necesitas, quita una sesión, no el descanso.',
    4: 'No hay hueco para una sesión de alta intensidad. Prioriza recuperar y llegar fresco.',
    3: 'Solo recuperación y activación. Aquí el descanso en MD+1 vale más que cualquier sesión.',
}

PRO_CAPACIDADES = (
    'REGENERATIVO / PREVENTIVO', 'FUERZA', 'RESISTENCIA', 'VELOCIDAD',
    'VELOCIDAD DE REACCIÓN', 'POTENCIA', 'AGILIDAD', 'RECUPERACIÓN',
    'DESCANSO', 'PARTIDO',
)

PRO_CAMPOS = (
    ('inicial',     'Parte inicial'),
    ('fisico',      'Físico'),
    ('tecnico',     'Técnico'),
    ('tactico',     'Táctico'),
    ('estrategico', 'Estratégico'),
    ('psicologico', 'Psicológico'),
    ('final',       'Parte final'),
)

PRO_BLOQUES = (
    ('fisico',      'Físico',      'activity', '#3b82f6'),
    ('tecnico',     'Técnico',     'target',   '#10b981'),
    ('tactico',     'Táctico',     'command',  '#f59e0b'),
    ('estrategico', 'Estratégico', 'flag',     '#8b5cf6'),
    ('psicologico', 'Psicológico', 'heart',    '#ec4899'),
)

#  Resumen propio y accionable de cada principio del artículo, con el dato que
#  lo sostiene. Los nueve primeros salen de estudios; los dos últimos los
#  infieren los autores desde la lógica del juego.
PRO_PRINCIPIOS = (
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

PRO_FUENTES = (
    {'titulo': ('Los 11 principios informados por evidencia e inferidos de la '
                'periodización de microciclos en el fútbol de élite'),
     'autores': 'Buchheit M, Douchet T, Settembre M, McHugh D, Hader K, Verheijen R',
     'publicacion': 'Sport Performance & Science Reports, 2024, Febrero, #218, v1',
     'licencia': 'Creative Commons BY 4.0',
     'url': 'https://sportperfsci.com'},
)


def pro_revisar(dias):
    """Los avisos de la guía sobre ESTE microciclo, no sobre el ideal.

    Es la parte que convierte la guía en algo útil: en vez de leer once
    principios, el entrenador ve qué se está saltando en la semana que acaba
    de escribir.
    """
    avisos = []
    por_md = {d.get('md'): d for d in dias}
    cargas = [d.get('carga') for d in dias]

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
        if md2.get('capacidad') != 'VELOCIDAD' and not _menciona(md2, 'velocidad'):
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
        if dia is not None and _menciona(dia, 'excéntric', 'excentric'):
            avisos.append({'nivel': 'alerta', 'principio': 7,
                           'texto': ('Hay trabajo excéntrico en %s, que es el tercer día '
                                     'tras el partido anterior. Ahí deja agujetas hasta el '
                                     'cuarto y quinto día: pásalo a MD+1.' % md)})

    #  Principio 3 — los suplentes
    md_mas_1 = por_md.get('MD+1')
    if md_mas_1 is not None and texto_de(md_mas_1):
        if not _menciona(md_mas_1, 'suplent', 'compensa', 'no convocad', 'banca'):
            avisos.append({'nivel': 'info', 'principio': 3,
                           'texto': 'En MD+1 no se ve la compensación de los suplentes. Ellos necesitan lo contrario que los titulares.'})

    return avisos


# ═══════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════
#  SEGMENTO 2 · SEMIPROFESIONAL
# ═══════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════
#  La misma notación MD, porque el semipro también juega el domingo y porque es
#  el idioma que ya habla cualquier entrenador que se ha formado. Lo que cambia
#  es TODO lo demás, y cambia por una razón que no se puede rodear: el jugador
#  no está disponible.
#
#  Sale del trabajo a las seis, entrena de siete a nueve y al día siguiente
#  vuelve a trabajar. No hay fisioterapeuta que le trate el gemelo, no hay
#  gimnasio del club, no hay GPS que diga cuánto corrió, y la asistencia del
#  martes no es la del jueves. En esas condiciones, la periodización de élite no
#  es «ambiciosa»: es literalmente inaplicable. Tres cosas se caen solas —
#  el día de recuperación dirigida, el segundo día duro y el control del
#  descanso— y el modelo entero está construido encima de esas tres.
#
#  Lo que sí se puede sostener, y es lo que ordena este modelo:
#    · UN día duro a la semana, no dos.
#    · La velocidad máxima no se negocia: es lo primero que se cae y lo que
#      más lesiona cuando falta.
#    · La prevención sustituye al fisioterapeuta que no hay.
#    · Lo que no cabe en tres sesiones, no existe. Todo va con balón.
SEMI_DIAS = {
    'MD+1': {
        'carga': 'descanso', 'capacidad': 'RECUPERACIÓN AUTOGESTIONADA',
        'fase': 'recuperacion',
        'foco': 'Sin sesión. El jugador trabaja — dale tarea, no entrenamiento',
        'detalle': ('El lunes tu jugador está en su trabajo. Convocarlo para «soltar '
                    'piernas» le cuesta dos horas de transporte y le quita la única tarde '
                    'que tenía. Lo que sí funciona es mandarle la tarea por escrito: '
                    'caminar, movilidad de diez minutos, hidratarse y dormir. '
                    'Si hubo lesionados o tocados, ESTE es el día de verlos, no el martes '
                    'con el grupo entero esperando.'),
        'principios': (2, 3),
    },
    'MD+2': {
        'carga': 'media', 'capacidad': 'FUERZA PREVENTIVA', 'fase': 'adquisicion',
        'foco': 'Reencuentro — prevención, fuerza y volumen con balón',
        'detalle': ('La primera sesión de la semana es la que más gente reúne y la que '
                    'menos exige. Empieza por el bloque preventivo completo (el 11+ entero, '
                    'con los nórdicos): es el día en que hay tiempo y en que nadie llega '
                    'con la pierna cargada del partido. Después, volumen aeróbico dentro de '
                    'juego de posición. Nada de series de carrera: no te sobra el minuto.'),
        'principios': (1, 3, 5),
    },
    'MD-5': {
        'carga': 'media', 'capacidad': 'RESISTENCIA JUGADA', 'fase': 'adquisicion',
        'foco': 'Sesión extra de la semana larga — volumen y modelo de juego',
        'detalle': ('Solo aparece cuando hay ocho días entre partidos, que en semipro es '
                    'casi siempre por aplazamiento o fecha libre. Aprovéchala para el '
                    'trabajo colectivo largo que no cabe el resto de semanas, no para '
                    'meter un segundo día duro.'),
        'principios': (1, 8),
    },
    'MD-4': {
        'carga': 'alta', 'capacidad': 'ALTA INTENSIDAD', 'fase': 'adquisicion',
        'foco': 'El único día duro de la semana',
        'detalle': ('Aquí va todo lo exigente que tengas: juego reducido de alta '
                    'intensidad, aceleraciones, duelos. Es UN día, no dos. Con tres '
                    'sesiones semanales y jugadores que trabajan, el segundo día duro no '
                    'produce adaptación — produce bajas el domingo. '
                    'Y colócalo aquí y no más tarde: cuanto más cerca del partido, menos '
                    'margen tienes si alguien acaba tocado.'),
        'principios': (1, 4, 8),
    },
    'MD-3': {
        'carga': 'baja', 'capacidad': 'REGENERATIVO / OPCIONAL', 'fase': 'adquisicion',
        'foco': 'Día suave o libre — el que separa el día duro de la velocidad',
        'detalle': ('En una semana de cuatro sesiones, esta es la que se sacrifica primero '
                    'y hay que sacrificarla sin culpa. Si la haces, que sea corta y con '
                    'balón: rondos, posesión y balón parado. Intercalar un día suave entre '
                    'el duro y el de velocidad hace que el jueves se corra más rápido.'),
        'principios': (5, 6),
    },
    'MD-2': {
        'carga': 'media', 'capacidad': 'VELOCIDAD MÁXIMA', 'fase': 'afinamiento',
        'foco': 'Velocidad máxima y modelo de juego — la sesión que no se salta',
        'detalle': ('Si esta semana solo puedes salvar una cosa de toda la guía, salva '
                    'esta. Correr cerca de la velocidad máxima en los días previos al '
                    'partido se asocia a menos lesiones de isquiotibiales, y en semipro es '
                    'siempre lo primero que se elimina «porque no hay tiempo». '
                    'No hace falta un cronómetro: 4-6 carreras de 30-40 metros con arranque '
                    'lanzado y descanso completo entre ellas, dentro del calentamiento. '
                    'Después, el once y la idea del domingo.'),
        'principios': (6, 7),
    },
    'MD-1': {
        'carga': 'baja', 'capacidad': 'ACTIVACIÓN', 'fase': 'afinamiento',
        'foco': 'Sesión corta — 45 minutos y balón parado',
        'detalle': ('45 minutos rinden más que 75. La víspera no se entrena: se recuerda. '
                    'Balón parado a favor y en contra, la alineación, y a casa. '
                    'Si tu equipo entrena sábado y juega domingo, esta sesión es esta; si '
                    'entrenáis viernes, MD-1 queda libre y es aún mejor.'),
        'principios': (7, 9),
    },
    'MD': {
        'carga': 'partido', 'capacidad': 'PARTIDO', 'fase': 'partido',
        'foco': 'Partido — y la única toma de datos de la semana',
        'detalle': ('Sin GPS, el partido es donde ves de verdad quién está. Anota los '
                    'minutos de cada uno: es el dato que decide la semana siguiente, '
                    'porque el que jugó 90 y el que no jugó nada no pueden entrenar igual '
                    'el martes.'),
        'principios': (3, 10),
    },
}

#  Las mismas rotaciones que el profesional — son posiciones respecto al
#  partido, no sesiones. Lo que cambia es lo que hay dentro de cada posición:
#  en una semana de siete días el semipro entrena tres veces y descansa cuatro,
#  donde el profesional entrena cinco.
SEMI_ROTACIONES = dict(PRO_ROTACIONES)

SEMI_AVISO_ROTACION = {
    8: 'Semana larga: te cabe una sesión más (MD-5). Úsala para volumen colectivo, no para un segundo día duro.',
    7: 'Semana normal: tres sesiones y la víspera. Suficiente si el día duro es de verdad duro.',
    6: 'Cabe una sesión menos. Junta el trabajo preventivo con el día de velocidad.',
    5: 'Dos sesiones. Que una sea de velocidad y balón parado, y la otra puramente colectiva.',
    4: 'Entre semana. No metas carga: aquí se recupera, se repasa y se juega.',
    3: 'Dos partidos casi seguidos. Solo activación — y si tienes fondo de plantilla, rota.',
}

SEMI_CAPACIDADES = (
    'RECUPERACIÓN AUTOGESTIONADA', 'FUERZA PREVENTIVA', 'RESISTENCIA JUGADA',
    'ALTA INTENSIDAD', 'VELOCIDAD MÁXIMA', 'REGENERATIVO / OPCIONAL',
    'ACTIVACIÓN', 'BALÓN PARADO', 'DESCANSO', 'PARTIDO',
)

SEMI_CAMPOS = (
    ('inicial',     'Calentamiento preventivo'),
    ('fisico',      'Físico'),
    ('tecnico',     'Técnico'),
    ('tactico',     'Táctico'),
    ('estrategico', 'Balón parado'),
    ('psicologico', 'Grupo y cabeza'),
    ('final',       'Vuelta a la calma y tarea'),
)

SEMI_BLOQUES = (
    ('fisico',      'Físico',        'activity', '#3b82f6'),
    ('tecnico',     'Técnico',       'target',   '#10b981'),
    ('tactico',     'Táctico',       'command',  '#f59e0b'),
    ('estrategico', 'Balón parado',  'flag',     '#8b5cf6'),
    ('psicologico', 'Grupo y cabeza', 'heart',   '#ec4899'),
)

SEMI_PRINCIPIOS = (
    {'n': 1, 'tipo': 'evidencia', 'icono': 'target', 'color': '#f59e0b',
     'titulo': 'Un solo día duro',
     'resumen': 'Con tres sesiones y jugadores que trabajan, el segundo día duro no adapta: rompe.',
     'clave': '1 por semana',
     'detalle': ('La periodización de élite reparte la carga en DOS días de adquisición '
                 'porque tiene cinco sesiones y un día entero de recuperación dirigida '
                 'entre medias. Quítale eso y los dos días duros se convierten en carga '
                 'acumulada sin ventana de recuperación. En una semana de tres sesiones, '
                 'el día duro es MD-4 y los otros dos son de contenido, no de carga.'),
     'aplica': 'Si la gráfica de tu semana tiene dos barras altas, baja una.'},

    {'n': 2, 'tipo': 'inferido', 'icono': 'briefcase', 'color': '#64748b',
     'titulo': 'La fatiga del trabajo cuenta',
     'resumen': 'Tu jugador llega cansado de algo que tú no planificaste.',
     'clave': 'Carga invisible',
     'detalle': ('Un albañil, un repartidor o un estudiante en semana de exámenes llega al '
                 'entrenamiento con una fatiga que ningún GPS mide y que ninguna planilla '
                 'recoge. La única herramienta que funciona sin material es preguntar: una '
                 'escala de 0 a 10 de cómo se siente al llegar, y el esfuerzo percibido de '
                 'la sesión al salir. Multiplicando ese esfuerzo por los minutos tienes la '
                 'carga de la sesión (Foster, 2001) sin gastar un dólar.'),
     'aplica': 'Pregunta antes de empezar. Si tres llegan por debajo de 5, esa sesión ya no es la que escribiste.'},

    {'n': 3, 'tipo': 'evidencia', 'icono': 'users', 'color': '#8b5cf6',
     'titulo': 'El que jugó y el que no',
     'resumen': 'Quien acumula pocos minutos y poca carrera rápida se lesiona más cuando por fin juega.',
     'clave': 'Compensar',
     'detalle': ('Es el mismo principio del fútbol de élite y en semipro pesa más, porque '
                 'aquí los suplentes no tienen partido de filial donde compensar. El que no '
                 'jugó el domingo necesita el martes lo contrario que el que jugó noventa: '
                 'carrera rápida y minutos, no descarga.'),
     'aplica': 'Anota los minutos de cada partido. Es el único registro de carga que vas a tener.'},

    {'n': 4, 'tipo': 'evidencia', 'icono': 'dribbble', 'color': '#10b981',
     'titulo': 'Todo con balón',
     'resumen': 'El juego reducido da intensidad, técnica y decisión en el mismo minuto.',
     'clave': 'Juego reducido',
     'detalle': ('Los formatos reducidos alcanzan intensidades cardiovasculares comparables '
                 'a las del trabajo interválico de carrera, y encima entrenan el juego. '
                 'Cuando tienes 90 minutos de campo tres veces por semana, cada minuto '
                 'gastado en carrera aislada es un minuto que no dedicaste a jugar. '
                 'La intensidad se ajusta con el tamaño del campo y el número de jugadores.'),
     'aplica': 'Antes de programar series, mira si un 4v4 en campo grande te da lo mismo.'},

    {'n': 5, 'tipo': 'evidencia', 'icono': 'shield', 'color': '#ef4444',
     'titulo': 'La prevención sustituye al fisioterapeuta que no tienes',
     'resumen': 'El calentamiento estructurado y el nórdico son lo de mayor retorno del semipro.',
     'clave': '11+ y nórdicos',
     'detalle': ('Un calentamiento estructurado de unos 20 minutos —carrera, fuerza de '
                 'core, equilibrio y pliometría— redujo alrededor de un tercio las lesiones '
                 'en fútbol amateur (Soligard y cols., BMJ 2008). El ejercicio nórdico de '
                 'isquiotibiales, por su parte, reduce a aproximadamente la mitad las '
                 'lesiones de isquios en las revisiones que lo han estudiado. '
                 'Ninguna de las dos cosas cuesta dinero ni material.'),
     'aplica': 'Que el bloque preventivo sea la primera línea de MD+2, y no lo que se recorta cuando llegáis tarde.'},

    {'n': 6, 'tipo': 'evidencia', 'icono': 'zap', 'color': '#dc2626',
     'titulo': 'La velocidad máxima no se negocia',
     'resumen': 'Es lo primero que se elimina por falta de tiempo, y lo que más caro sale.',
     'clave': '4-6 carreras',
     'detalle': ('Exponer al jugador a velocidades cercanas a su máximo en los días previos '
                 'al partido se asocia a menos lesiones de isquiotibiales. Y no hace falta '
                 'ni cronómetro ni pista: 4-6 carreras de 30-40 metros con arranque lanzado, '
                 'con descanso completo entre ellas, metidas dentro del calentamiento de '
                 'MD-2. Son ocho minutos.'),
     'aplica': 'Si esta semana vas mal de tiempo, quita el vídeo, no las carreras.'},

    {'n': 7, 'tipo': 'evidencia', 'icono': 'trending-down', 'color': '#14b8a6',
     'titulo': 'La víspera se recuerda, no se entrena',
     'resumen': '45 minutos dejan mejor salto y mejor sprint el día siguiente que 75.',
     'clave': '45 min',
     'detalle': ('Es de los pocos hallazgos del fútbol de élite que se traslada tal cual, '
                 'porque no depende de tener recursos: depende de saber parar. En semipro '
                 'la tentación es la contraria — como se entrena poco, la víspera se '
                 'aprovecha. Y así se llega al domingo con las piernas del sábado.'),
     'aplica': 'Balón parado, alineación y a casa. Si necesitas más, el problema está en MD-4.'},

    {'n': 8, 'tipo': 'inferido', 'icono': 'user-x', 'color': '#0ea5e9',
     'titulo': 'La sesión tiene que funcionar con 12 y con 22',
     'resumen': 'La asistencia varía cada día, y una sesión que solo sale completa no sale nunca.',
     'clave': 'Plan B escrito',
     'detalle': ('En semipro el turno de trabajo, el examen y el bus mandan más que la '
                 'convocatoria. Diseñar la sesión para 20 jugadores y encontrarte 13 obliga '
                 'a improvisar delante del grupo, y lo que se improvisa es siempre lo mismo: '
                 'un partidillo. Escribir el formato alternativo al lado del principal '
                 'cuesta un minuto y salva la sesión.'),
     'aplica': 'Al lado de cada tarea, anota en qué se convierte si vienen seis menos.'},

    {'n': 9, 'tipo': 'inferido', 'icono': 'home', 'color': '#8b5cf6',
     'titulo': 'Enseñarle a cuidarse solo',
     'resumen': 'Cuatro de los siete días de la semana no los controlas tú.',
     'clave': 'Los días que no viene',
     'detalle': ('El club profesional controla la comida, el sueño y la recuperación de sus '
                 'jugadores. Tú controlas tres tardes. Todo lo demás —dormir, comer, '
                 'hidratarse, no jugar un campeonato barrial el sábado— depende de que el '
                 'jugador entienda por qué importa. Esa formación es parte del plan, y '
                 'ocupa dos minutos al final de cada sesión.'),
     'aplica': 'Escribe la tarea del día libre en la casilla de vuelta a la calma. Que salga por escrito.'},

    {'n': 10, 'tipo': 'inferido', 'icono': 'calendar', 'color': '#94a3b8',
     'titulo': 'El calendario real manda',
     'resumen': 'Aplazamientos, campos sin luz y torneos relámpago: la semana ideal casi nunca ocurre.',
     'clave': 'Adaptar',
     'detalle': ('En categorías de ascenso el calendario cambia con días de aviso. Tener el '
                 'plan escrito es lo que te permite decidir bien cuando toca cambiarlo, '
                 'porque sabes qué estás quitando. La diferencia entre improvisar y adaptar '
                 'es exactamente esa hoja.'),
     'aplica': 'Guarda la semana aunque sepas que va a cambiar. Y cuando cambie, guarda la nueva.'},
)

SEMI_FUENTES = (
    {'titulo': ('Los 11 principios informados por evidencia e inferidos de la '
                'periodización de microciclos en el fútbol de élite'),
     'autores': 'Buchheit M, Douchet T, Settembre M, McHugh D, Hader K, Verheijen R',
     'publicacion': 'Sport Performance & Science Reports, 2024, #218',
     'licencia': 'Creative Commons BY 4.0',
     'url': 'https://sportperfsci.com',
     'nota': 'Base de la periodización. Aquí se adapta a tres sesiones semanales.'},
    {'titulo': 'Comprehensive warm-up programme to prevent injuries in young female footballers',
     'autores': 'Soligard T, Myklebust G, Steffen K y cols.',
     'publicacion': 'BMJ, 2008;337:a2469',
     'nota': 'El calentamiento estructurado («11+») en fútbol amateur.'},
    {'titulo': 'Including the Nordic hamstring exercise in injury prevention programmes',
     'autores': 'van Dyk N, Behan FP, Whiteley R',
     'publicacion': 'British Journal of Sports Medicine, 2019',
     'nota': 'Metaanálisis del ejercicio nórdico en lesiones de isquiotibiales.'},
    {'titulo': 'A new approach to monitoring exercise training',
     'autores': 'Foster C, Florhaug JA, Franklin J y cols.',
     'publicacion': 'Journal of Strength and Conditioning Research, 2001',
     'nota': 'Esfuerzo percibido × minutos: medir la carga sin material.'},
    {'titulo': 'Physiology of small-sided games training in football',
     'autores': 'Hill-Haas SV, Dawson B, Impellizzeri FM, Coutts AJ',
     'publicacion': 'Sports Medicine, 2011;41(3):199-220',
     'nota': 'Por qué el juego reducido sustituye al trabajo de carrera.'},
)


def semi_revisar(dias):
    """Los avisos propios del semiprofesional.

    Vigilan lo que de verdad se rompe en este segmento, que no es lo mismo que
    se rompe en un club profesional: aquí el error caro es planificar como si
    el jugador estuviera disponible.
    """
    avisos = []
    por_md = {d.get('md'): d for d in dias}
    escritos = [d for d in dias if texto_de(d)]

    #  Principio 1 — un solo día duro
    duros = [d for d in dias if d.get('carga') == 'alta']
    if len(duros) >= 2:
        avisos.append({'nivel': 'alerta', 'principio': 1,
                       'texto': ('Hay %d días de carga alta. Con jugadores que trabajan, el '
                                 'segundo no adapta: llega en forma de baja el domingo.'
                                 % len(duros))})

    #  Principio 2 — el lunes
    md_mas_1 = por_md.get('MD+1')
    if md_mas_1 is not None and md_mas_1.get('carga') not in ('descanso', 'baja'):
        avisos.append({'nivel': 'aviso', 'principio': 2,
                       'texto': 'MD+1 lleva carga. Tus jugadores trabajan ese día: mándales tarea, no sesión.'})

    #  Principio 5 — la prevención, en toda la semana
    if escritos and not any(_menciona(d, 'nórdic', 'nordic', 'excéntric', 'excentric',
                                      'prevent', '11+', 'core', 'propiocep')
                            for d in escritos):
        avisos.append({'nivel': 'alerta', 'principio': 5,
                       'texto': ('En toda la semana no aparece trabajo preventivo. Sin '
                                 'fisioterapeuta, es lo único que te queda entre un jugador '
                                 'y un mes de baja.')})

    #  Principio 6 — la velocidad máxima
    md2 = por_md.get('MD-2')
    if md2 is not None and escritos:
        if md2.get('capacidad') != 'VELOCIDAD MÁXIMA' and not _menciona(md2, 'velocidad', 'sprint', 'lanzad'):
            avisos.append({'nivel': 'alerta', 'principio': 6,
                           'texto': ('En MD-2 no hay velocidad máxima. Son ocho minutos, y es '
                                     'lo que más caro sale de quitar.')})

    #  Principio 7 — la víspera
    md1 = por_md.get('MD-1')
    if md1 is not None:
        if int(md1.get('duracion') or 0) > 60:
            avisos.append({'nivel': 'aviso', 'principio': 7,
                           'texto': ('La víspera dura %s minutos. 45 dejan mejor salto y mejor '
                                     'sprint el día del partido.' % md1.get('duracion'))})
        if md1.get('carga') in ('alta', 'media') and (por_md.get('MD-2') or {}).get('carga') in ('alta', 'media'):
            avisos.append({'nivel': 'alerta', 'principio': 7,
                           'texto': 'MD-2 y MD-1 llevan carga seguida. La víspera tiene que aflojar.'})

    #  Principio 8 — el plan B
    #  Solo cuando la semana ya está bastante escrita: avisar de esto en un
    #  microciclo a medias es ruido, y el ruido enseña a ignorar los avisos.
    if len(escritos) >= 3 and not any(_menciona(d, 'si falta', 'si vienen', 'alternativ',
                                                'plan b', 'menos jugadores')
                                      for d in escritos):
        avisos.append({'nivel': 'info', 'principio': 8,
                       'texto': ('No hay ninguna alternativa escrita por si vienen menos. Un '
                                 'formato de repuesto al lado de cada tarea salva la sesión.')})

    #  Principio 9 — la tarea del día libre
    if escritos and not any((d.get('final') or '').strip() for d in escritos):
        avisos.append({'nivel': 'info', 'principio': 9,
                       'texto': ('Ninguna sesión cierra con tarea para casa. Cuatro de los '
                                 'siete días de la semana no los controlas tú.')})

    #  El exceso de sesiones: el error de entusiasmo del entrenador nuevo.
    if len(escritos) >= 6:
        avisos.append({'nivel': 'aviso', 'principio': 1,
                       'texto': ('Has escrito %d sesiones. En semipro eso no es un plan '
                                 'ambicioso: es una lista de a quién vas a perder primero.'
                                 % len(escritos))})

    return avisos


# ═══════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════
#  SEGMENTO 1 · COLEGIO
# ═══════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════
#  Aquí se rompe la notación MD, y se rompe a propósito.
#
#  MD-4 significa «cuatro días antes del partido». Esa cuenta solo tiene sentido
#  si el partido es el punto al que se dirige todo. En un colegio no lo es: la
#  jornada intercolegial es una tarde de un sábado y puede no haberla en tres
#  semanas. Lo que sí existe todas las semanas es la semana lectiva — lunes a
#  viernes, clases, deberes y dos o tres tardes de cancha.
#
#  Así que aquí los días se llaman por lo que son: S1, S2, S3 (las sesiones),
#  LIBRE (el día que hay clase y no hay equipo, que también forma parte del
#  plan), PREVIA y JORNADA. Y el objetivo del plan no es llegar al sábado: es
#  que el chico llegue a los veinte años jugando.
#
#  La consecuencia práctica es que este modelo avisa de cosas que a un
#  profesional le parecerían raras —cuántas horas totales acumula el chico, si
#  alguien se queda sin jugar, si aparece la palabra «suplente»— y no avisa de
#  casi nada de lo que vigila el modelo de élite.
COL_DIAS = {
    'S1': {
        'carga': 'media', 'capacidad': 'COORDINACIÓN Y TÉCNICA', 'fase': 'adquisicion',
        'foco': 'La sesión de aprender — coordinación, técnica individual y mucho balón',
        'detalle': ('La primera sesión de la semana es la de enseñar, no la de cansar. '
                    'Agilidad, equilibrio, coordinación y velocidad de gesto; después '
                    'técnica individual con el balón en los pies el máximo de tiempo '
                    'posible. Entre los 7 y los 12 años esta sesión vale más que ninguna '
                    'otra cosa que puedas programar, porque es cuando el aprendizaje motor '
                    'rinde de verdad. '
                    'Regla de oro: cuenta los minutos en que cada chico tiene un balón. Si '
                    'son menos de la mitad de la sesión, la tarea está mal montada.'),
        'principios': (1, 6, 7),
    },
    'S2': {
        'carga': 'alta', 'capacidad': 'JUEGO REDUCIDO', 'fase': 'adquisicion',
        'foco': 'La sesión de jugar — formatos reducidos, todos dentro',
        'detalle': ('La sesión más exigente de la semana, y la que más se parece a jugar. '
                    'Formatos pequeños —3v3, 4v4— con muchos equipos y rotación continua: '
                    'nadie mirando desde la banda. En espacios reducidos el chico toca el '
                    'balón muchas más veces, decide muchas más veces y se divierte mucho '
                    'más que en un 11v11, que a estas edades es sobre todo esperar. '
                    '«Alta» aquí quiere decir intensa y alegre, no dura.'),
        'principios': (2, 7),
    },
    'S3': {
        'carga': 'media', 'capacidad': 'SITUACIONES DE JUEGO', 'fase': 'afinamiento',
        'foco': 'Cómo vamos a jugar — situaciones, roles y fuerza con peso corporal',
        'detalle': ('La sesión previa a la jornada: situaciones de partido a media '
                    'intensidad, quién juega dónde y por qué. Es también el hueco natural '
                    'del trabajo de fuerza con el propio peso —saltos, sentadillas, planchas, '
                    'nórdicos adaptados—, que en chicos supervisados es seguro y reduce '
                    'lesiones. El mito de que la fuerza «frena el crecimiento» está desmentido '
                    'desde hace décadas; lo que sí hace daño es la técnica sin corregir.'),
        'principios': (4, 8),
    },
    'S4': {
        'carga': 'media', 'capacidad': 'MULTIDEPORTE', 'fase': 'adquisicion',
        'foco': 'Sesión abierta — otros deportes, otros gestos',
        'detalle': ('Cuando la semana da para una cuarta sesión, la mejor inversión no es '
                    'más fútbol: es otra cosa. Baloncesto, atletismo, natación, juegos de '
                    'lucha. La variedad de movimiento construye al atleta que después '
                    'sostiene al futbolista, y retrasa la especialización temprana, que es '
                    'el factor de riesgo más consistente de lesión por sobreuso y de '
                    'abandono en el deporte juvenil.'),
        'principios': (5,),
    },
    'PREVIA': {
        'carga': 'baja', 'capacidad': 'ACTIVACIÓN', 'fase': 'afinamiento',
        'foco': 'Día antes de la jornada — corto, y que duerman',
        'detalle': ('Media hora de balón y a casa. Lo que de verdad decide cómo van a '
                    'competir mañana no es esta sesión: es que duerman. En deportistas '
                    'adolescentes, dormir menos de ocho horas se asocia a un riesgo de '
                    'lesión sustancialmente mayor (Milewski y cols., 2014), y en semana de '
                    'exámenes eso lo decides tú al elegir la hora del entrenamiento.'),
        'principios': (9, 11),
    },
    'JORNADA': {
        'carga': 'partido', 'capacidad': 'JORNADA', 'fase': 'partido',
        'foco': 'Jornada intercolegial — todos juegan',
        'detalle': ('Los minutos de juego son el estímulo formativo más potente que existe '
                    'a estas edades: dejar a un chico sin jugar para asegurar el resultado '
                    'es sacarlo del proceso por el que está ahí. Reparte los minutos antes '
                    'de salir de casa y dilo en voz alta, para que nadie lo dude. '
                    'Y vigila tu propio comportamiento en la banda: la presión del adulto '
                    'por el resultado es el mejor predictor de que un chico deje el deporte.'),
        'principios': (2, 3, 10),
    },
    'LIBRE': {
        'carga': 'descanso', 'capacidad': 'CLASES Y DESCANSO', 'fase': 'recuperacion',
        'foco': 'Día lectivo sin equipo — y eso también es parte del plan',
        'detalle': ('El día sin entrenamiento no es un hueco en la planilla: es el día en '
                    'que el chico hace deberes, duerme y juega por su cuenta. Ponerlo por '
                    'escrito sirve para dos cosas: para que la familia vea el plan completo '
                    'y para que tú no cedas a la tentación de llenarlo cuando se acerque '
                    'una jornada importante.'),
        'principios': (5, 11),
    },
    'DESCANSO': {
        'carga': 'descanso', 'capacidad': 'DESCANSO', 'fase': 'recuperacion',
        'foco': 'Fin de semana libre — que juegue a otra cosa',
        'detalle': ('Sin actividad del equipo. Si el chico quiere jugar en la calle o hacer '
                    'otro deporte, mejor: eso es exactamente lo que le conviene.'),
        'principios': (5,),
    },
}

#  Aquí «rotación» no cuenta días entre partidos: cuenta los días que abarca la
#  semana que estás planificando. La clave sigue siendo un número de 3 a 8
#  porque es lo que admite la base (`fut_micro_rotacion_valida`), pero lo que
#  significa es otra cosa y así se le dice al entrenador.
COL_ROTACIONES = {
    8: ('S1', 'LIBRE', 'S2', 'LIBRE', 'S3', 'S4', 'PREVIA', 'JORNADA'),
    7: ('S1', 'LIBRE', 'S2', 'LIBRE', 'S3', 'JORNADA', 'DESCANSO'),
    6: ('S1', 'LIBRE', 'S2', 'LIBRE', 'S3', 'JORNADA'),
    5: ('S1', 'LIBRE', 'S2', 'LIBRE', 'S3'),
    4: ('S1', 'LIBRE', 'S2', 'JORNADA'),
    3: ('S1', 'LIBRE', 'S2'),
}

COL_AVISO_ROTACION = {
    8: 'Semana larga con jornada: te cabe la sesión de multideporte. Es la que más construye a esta edad.',
    7: 'Semana lectiva completa con jornada el sábado. Tres sesiones y dos días de clases sin equipo.',
    6: 'Tres sesiones y jornada. Es la semana típica del intercolegial.',
    5: 'Semana lectiva sin jornada: la mejor para enseñar. Sin partido, la sesión puede durar más en técnica.',
    4: 'Dos sesiones y jornada. Con tan poco, prioriza el juego reducido sobre el ensayo táctico.',
    3: 'Dos sesiones sueltas. Semana de exámenes o de receso: mantén el hábito, no busques carga.',
}

COL_CAPACIDADES = (
    'COORDINACIÓN Y TÉCNICA', 'JUEGO REDUCIDO', 'SITUACIONES DE JUEGO',
    'FUERZA CON PESO CORPORAL', 'VELOCIDAD Y AGILIDAD', 'MULTIDEPORTE',
    'RESISTENCIA JUGADA', 'ACTIVACIÓN', 'CLASES Y DESCANSO', 'DESCANSO', 'JORNADA',
)

COL_CAMPOS = (
    ('inicial',     'Calentamiento y activación'),
    ('fisico',      'Coordinación y ABC'),
    ('tecnico',     'Técnica individual'),
    ('tactico',     'Juego reducido'),
    ('estrategico', 'Situaciones de partido'),
    ('psicologico', 'Valores y clima'),
    ('final',       'Vuelta a la calma y despedida'),
)

COL_BLOQUES = (
    ('fisico',      'Coordinación y ABC',     'activity', '#3b82f6'),
    ('tecnico',     'Técnica individual',     'target',   '#10b981'),
    ('tactico',     'Juego reducido',         'command',  '#f59e0b'),
    ('estrategico', 'Situaciones de partido', 'flag',     '#8b5cf6'),
    ('psicologico', 'Valores y clima',        'heart',    '#ec4899'),
)

COL_PRINCIPIOS = (
    {'n': 1, 'tipo': 'evidencia', 'icono': 'trending-up', 'color': '#0ea5e9',
     'titulo': 'No se periodiza para el sábado: se periodiza para crecer',
     'resumen': 'El plan de la semana responde a la etapa de desarrollo del chico, no al calendario.',
     'clave': 'Largo plazo',
     'detalle': ('Los modelos de desarrollo deportivo a largo plazo ordenan la formación por '
                 'etapas —aprender a moverse, aprender a entrenar, entrenar para entrenar— y '
                 'cada una tiene su contenido. Antes de la pubertad el rendimiento del '
                 'trabajo de coordinación y técnica es máximo; después se abre la ventana de '
                 'la fuerza y de la resistencia. Programar contra el rival del sábado en vez '
                 'de contra la etapa desperdicia los años que no vuelven.'),
     'aplica': 'Pregúntate qué debería saber hacer este grupo en junio, no el sábado.'},

    {'n': 2, 'tipo': 'inferido', 'icono': 'users', 'color': '#10b981',
     'titulo': 'Todos juegan',
     'resumen': 'El minuto de juego es el estímulo. Sentar al que va más lento es sacarlo del proceso.',
     'clave': 'Minutos repartidos',
     'detalle': ('En categorías de formación el reparto de minutos suele seguir al nivel '
                 'actual, y el nivel actual sigue en buena parte a la fecha de nacimiento y '
                 'al momento del estirón: los nacidos a principio de año están '
                 'sistemáticamente sobrerrepresentados en las selecciones juveniles (efecto '
                 'de la edad relativa, documentado en fútbol desde los años noventa). Al '
                 'chico que va detrás no le falta talento: le faltan meses. Quitarle minutos '
                 'por eso convierte una diferencia temporal en una definitiva.'),
     'aplica': 'Reparte los minutos ANTES del partido y dilo delante de todos.'},

    {'n': 3, 'tipo': 'evidencia', 'icono': 'activity', 'color': '#f59e0b',
     'titulo': 'El estirón manda',
     'resumen': 'Durante el pico de crecimiento el mismo entrenamiento pesa el doble.',
     'clave': 'Talla cada 3 meses',
     'detalle': ('Alrededor del pico de velocidad de crecimiento —típicamente entre los 12 y '
                 'los 15 años en chicos, antes en chicas— el hueso crece más rápido que el '
                 'tendón, y ahí aparecen la Osgood-Schlatter, la enfermedad de Sever y las '
                 'lesiones por sobreuso. El chico se vuelve además más torpe durante unos '
                 'meses, y suele interpretarse como falta de actitud. '
                 'Medir la talla cada tres meses y anotarla cuesta cinco minutos por '
                 'trimestre y te dice a quién bajarle el volumen de saltos y de carrera.'),
     'aplica': 'Al que pegó el estirón: menos volumen de impacto, más técnica y paciencia.'},

    {'n': 4, 'tipo': 'evidencia', 'icono': 'anchor', 'color': '#6366f1',
     'titulo': 'Fuerza sí, y desde pronto',
     'resumen': 'El entrenamiento de fuerza supervisado en niños es seguro y reduce lesiones.',
     'clave': 'Peso corporal',
     'detalle': ('Es de los puntos con más consenso en la literatura y de los peor '
                 'entendidos en la cancha: la fuerza bien supervisada en edades infantiles y '
                 'juveniles mejora el rendimiento, reduce el riesgo de lesión y NO afecta al '
                 'crecimiento. El mito contrario ha costado generaciones de chicos sin base. '
                 'No hace falta gimnasio: peso corporal, saltos, gomas, trepa y juegos de '
                 'lucha. La regla es técnica antes que carga, siempre.'),
     'aplica': 'Diez minutos de fuerza con peso corporal en S3, todas las semanas.'},

    {'n': 5, 'tipo': 'evidencia', 'icono': 'shuffle', 'color': '#8b5cf6',
     'titulo': 'Ni especialización temprana ni exceso de horas',
     'resumen': 'Más horas semanales de un solo deporte que años tiene el chico se asocia a más lesiones.',
     'clave': 'Horas ≤ edad',
     'detalle': ('En las series pediátricas sobre deporte juvenil, dos indicadores aparecen '
                 'una y otra vez ligados a la lesión por sobreuso: dedicar a deporte '
                 'organizado más horas semanales que años de edad, y competir en un solo '
                 'deporte durante más meses al año que los demás. Practicar varios deportes '
                 'hasta pasada la pubertad se asocia además a mejor rendimiento adulto y a '
                 'menos abandono. '
                 'Y ojo: tú ves solo tus horas. El chico puede estar además en la selección '
                 'del colegio, en una escuela por su cuenta y en un campeonato barrial.'),
     'aplica': 'Pregunta al grupo cuántas horas juegan FUERA de aquí. Puede que tu semana no sea su semana.'},

    {'n': 6, 'tipo': 'evidencia', 'icono': 'target', 'color': '#047857',
     'titulo': 'La ventana de la coordinación',
     'resumen': 'Lo que se aprende de movimiento antes de la pubertad no se recupera después.',
     'clave': '7 a 12 años',
     'detalle': ('La etapa previa al estirón es donde el sistema nervioso aprende más rápido '
                 'a coordinar: agilidad, equilibrio, control del cuerpo y técnica fina. Es '
                 'reversible en parte, pero nunca sale tan barato como en esos años. '
                 'Gastar esas temporadas en trabajo físico general o en esquemas tácticos es '
                 'el error más caro de la formación, precisamente porque no se ve: el equipo '
                 'gana igual, y la factura llega ocho años después.'),
     'aplica': 'Si el grupo es sub-12, que la mitad de cada sesión sea balón en los pies.'},

    {'n': 7, 'tipo': 'evidencia', 'icono': 'dribbble', 'color': '#0d9488',
     'titulo': 'Se aprende jugando, y en espacios pequeños',
     'resumen': 'En 4v4 el chico toca el balón y decide muchas más veces que en 8v8 u 11v11.',
     'clave': 'Formatos pequeños',
     'detalle': ('Los estudios que comparan formatos en fútbol formativo coinciden en la '
                 'dirección: al reducir el número de jugadores y el tamaño del campo se '
                 'multiplican los contactos con el balón, los pases, los uno contra uno y '
                 'los goles por jugador. Más repeticiones, más decisiones y más diversión en '
                 'el mismo tiempo de sesión. El 11v11 a estas edades es sobre todo esperar '
                 'a que el balón llegue.'),
     'aplica': 'Antes de montar una tarea, cuenta cuántas veces va a tocar el balón el que menos toque.'},

    {'n': 8, 'tipo': 'evidencia', 'icono': 'shield', 'color': '#ef4444',
     'titulo': 'Calentar es la clase de prevención',
     'resumen': 'Un calentamiento estructurado reduce de forma marcada las lesiones en fútbol infantil.',
     'clave': '15-20 min',
     'detalle': ('El programa de calentamiento estructurado adaptado a edades infantiles '
                 '(«11+ Kids») redujo de forma sustancial las lesiones en ensayos '
                 'controlados con niños de 7 a 13 años, y en los estudios en categorías '
                 'mayores el efecto va en la misma dirección. Carrera con cambios de '
                 'dirección, equilibrio a una pierna, caídas, core y saltos. '
                 'A esta edad además no hay que venderlo como prevención: son juegos.'),
     'aplica': 'Que el calentamiento sea siempre el mismo bloque. La repetición es lo que lo hace funcionar.'},

    {'n': 9, 'tipo': 'evidencia', 'icono': 'moon', 'color': '#6366f1',
     'titulo': 'Dormir es parte del entrenamiento',
     'resumen': 'El adolescente que duerme menos de ocho horas se lesiona bastante más.',
     'clave': '8 horas',
     'detalle': ('En deportistas adolescentes, dormir habitualmente menos de ocho horas se '
                 'asoció a un riesgo de lesión notablemente mayor —del orden del doble— en '
                 'el estudio de Milewski y colaboradores. El sueño pesa ahí más que las '
                 'horas de entrenamiento a la semana. '
                 'La hora a la que acaba tu sesión y la cantidad de deberes que tienen esa '
                 'noche son, literalmente, variables de tu plan.'),
     'aplica': 'En semana de exámenes, sesión más temprana y más corta. No es blandura, es planificación.'},

    {'n': 10, 'tipo': 'evidencia', 'icono': 'heart', 'color': '#ec4899',
     'titulo': 'Se van cuando deja de ser divertido',
     'resumen': 'El abandono no se explica por la derrota, sino por el clima que crea el adulto.',
     'clave': 'Clima de maestría',
     'detalle': ('Las revisiones sobre abandono en deporte juvenil apuntan siempre a lo '
                 'mismo: los chicos siguen cuando se divierten, tienen amigos y sienten que '
                 'mejoran, y se van cuando hay presión por el resultado, comparación '
                 'constante y poca sensación de competencia. Un clima orientado a la mejora '
                 '—se valora el esfuerzo y el progreso— sostiene la motivación mucho mejor '
                 'que uno orientado a ganar. '
                 'El adulto de la banda es la variable con más peso, y es la que tú controlas '
                 'del todo.'),
     'aplica': 'Al final de cada sesión, di en voz alta una cosa que mejoró CADA chico. Sin excepciones.'},

    {'n': 11, 'tipo': 'inferido', 'icono': 'book', 'color': '#94a3b8',
     'titulo': 'La escuela va primero, y conviene decirlo',
     'resumen': 'El equipo se planifica alrededor del calendario académico, no al revés.',
     'clave': 'Calendario lectivo',
     'detalle': ('Exámenes, entregas y el bus de vuelta a casa son restricciones reales, y '
                 'el chico que tiene que elegir entre entrenar y aprobar acaba dejando el '
                 'equipo. Anticiparlo en la planilla —marcar la semana de exámenes como '
                 'semana ligera— evita la elección. '
                 'Además es lo que le hace ganar la confianza de las familias, y sin las '
                 'familias en un colegio no hay proyecto que dure dos temporadas.'),
     'aplica': 'Pide el calendario de exámenes al empezar el trimestre y planifica encima de él.'},
)

COL_FUENTES = (
    {'titulo': 'Long-Term Athlete Development',
     'autores': 'Balyi I, Way R, Higgs C',
     'publicacion': 'Human Kinetics, 2013',
     'nota': 'El marco de etapas de formación por edad de desarrollo.'},
    {'titulo': 'The Youth Physical Development Model',
     'autores': 'Lloyd RS, Oliver JL',
     'publicacion': 'Strength and Conditioning Journal, 2012;34(3):61-72',
     'nota': 'Qué capacidad entrenar en qué momento del crecimiento.'},
    {'titulo': 'Youth resistance training: position statement',
     'autores': 'Faigenbaum AD, Kraemer WJ, Blimkie CJR y cols.',
     'publicacion': 'Journal of Strength and Conditioning Research, 2009;23:S60-S79',
     'nota': 'La fuerza supervisada en niños es segura y recomendable.'},
    {'titulo': 'Sports-specialized intensive training and the risk of injury in young athletes',
     'autores': 'Jayanthi NA, LaBella CR, Fischer D, Pasulka J, Dugas LR',
     'publicacion': 'American Journal of Sports Medicine, 2015;43(4):794-801',
     'nota': 'Horas semanales, especialización temprana y lesión por sobreuso.'},
    {'titulo': 'A multinational cluster-randomised controlled trial to assess the efficacy of «11+ Kids»',
     'autores': 'Rössler R, Verhagen E, Rommers N y cols.',
     'publicacion': 'Sports Medicine, 2018',
     'nota': 'Calentamiento preventivo en fútbol infantil de 7 a 13 años.'},
    {'titulo': 'Chronic lack of sleep is associated with increased sports injuries in adolescent athletes',
     'autores': 'Milewski MD, Skaggs DL, Bishop GA y cols.',
     'publicacion': 'Journal of Pediatric Orthopaedics, 2014;34(2):129-133',
     'nota': 'Dormir menos de ocho horas y riesgo de lesión.'},
    {'titulo': 'A systematic review of dropout from organized sport among children and youth',
     'autores': 'Crane J, Temple V',
     'publicacion': 'European Physical Education Review, 2015;21(1):114-131',
     'nota': 'Por qué dejan de jugar: el clima, no el resultado.'},
    {'titulo': 'The relative age effect in youth soccer across Europe',
     'autores': 'Helsen WF, van Winckel J, Williams AM',
     'publicacion': 'Journal of Sports Sciences, 2005;23(6):629-636',
     'nota': 'Los nacidos a principio de año dominan las selecciones juveniles.'},
)


def col_revisar(dias):
    """Los avisos propios de un colegio.

    Vigilan lo que se rompe en formación, que casi nunca es la carga: es que
    alguien se quede sin jugar, que el chico acumule horas de tres sitios a la
    vez, o que la semana no tenga un solo día en que el equipo lo deje en paz.
    """
    avisos = []
    escritos = [d for d in dias if texto_de(d)]
    sesiones = [d for d in dias
                if (d.get('md') or '').startswith('S') and d.get('carga') != 'descanso']
    #  Casi todas las reglas miran solo las sesiones YA ESCRITAS. Una semana
    #  recién creada está en blanco por definición, y regañar a alguien por no
    #  haber escrito todavía lo que acaba de abrir es la forma más rápida de
    #  enseñarle a ignorar los avisos.
    sesiones_escritas = [d for d in sesiones if texto_de(d)]

    #  Principio 5 — las horas de la semana
    minutos = sum(int(d.get('duracion') or 0) for d in dias
                  if d.get('carga') != 'descanso')
    horas = minutos / 60.0
    if horas > 6:
        avisos.append({'nivel': 'aviso', 'principio': 5,
                       'texto': ('La semana suma %.1f horas de equipo. Recuerda que a eso hay '
                                 'que sumarle lo que el chico juega FUERA: la referencia es '
                                 'no pasar de tantas horas como años tiene.' % horas)})

    #  Principio 5 y 11 — algún día sin equipo
    if len(dias) >= 5 and not any(d.get('md') in ('LIBRE', 'DESCANSO') for d in dias):
        avisos.append({'nivel': 'aviso', 'principio': 11,
                       'texto': ('La semana no tiene ningún día sin equipo. Los deberes y el '
                                 'sueño también van en el plan.')})

    #  Principio 2 — el lenguaje que delata el problema
    for d in escritos:
        if _menciona(d, 'suplent', 'banquillo', 'los que juegan', 'titular'):
            avisos.append({'nivel': 'alerta', 'principio': 2,
                           'texto': ('Aparecen titulares y suplentes en la planilla. En '
                                     'formación los minutos son el estímulo: si alguien no '
                                     'juega, no está entrenando.')})
            break

    #  Principio 8 — el calentamiento
    if sesiones_escritas and not all((d.get('inicial') or '').strip()
                                     for d in sesiones_escritas):
        avisos.append({'nivel': 'aviso', 'principio': 8,
                       'texto': ('Hay sesiones sin calentamiento escrito. Es el bloque con más '
                                 'retorno de toda la semana, y funciona por repetirlo igual.')})

    #  Principio 7 — se aprende jugando
    if len(escritos) >= 2 and not any(_menciona(d, 'juego', 'reducido', '3v3', '4v4', '5v5',
                                                'partidillo', 'rondo', 'posesión', 'posesion')
                                      for d in escritos):
        avisos.append({'nivel': 'aviso', 'principio': 7,
                       'texto': ('En toda la semana no aparece juego. A esta edad el juego '
                                 'reducido enseña más que cualquier ejercicio analítico.')})

    #  Principio 4 — la fuerza
    if len(escritos) >= 3 and not any(_menciona(d, 'fuerza', 'salto', 'sentadilla', 'plancha',
                                                'core', 'peso corporal', 'trepa')
                                      for d in escritos):
        avisos.append({'nivel': 'info', 'principio': 4,
                       'texto': ('No hay trabajo de fuerza con peso corporal. Diez minutos a '
                                 'la semana son seguros y bajan el riesgo de lesión.')})

    #  Principio 6 — la ventana de la coordinación
    if sesiones_escritas and not any(_menciona(d, 'coordina', 'agilidad', 'equilibrio',
                                               'técnica', 'tecnica', 'conducción',
                                               'conduccion')
                                     for d in sesiones_escritas):
        avisos.append({'nivel': 'aviso', 'principio': 6,
                       'texto': ('No se ve coordinación ni técnica individual. Son los años en '
                                 'que eso sale barato; después ya no.')})

    #  Principio 9 y 1 — la duración de la sesión
    largas = [d for d in sesiones if int(d.get('duracion') or 0) > 90]
    if largas:
        avisos.append({'nivel': 'aviso', 'principio': 9,
                       'texto': ('Hay %d sesión(es) de más de 90 minutos. En formación, entre '
                                 '60 y 75 se aprovechan mejor y dejan la tarde para estudiar.'
                                 % len(largas))})

    #  Principio 10 — el clima
    if len(escritos) >= 2 and not any((d.get('psicologico') or '').strip() for d in escritos):
        avisos.append({'nivel': 'info', 'principio': 10,
                       'texto': ('La columna de valores y clima está vacía toda la semana. Es '
                                 'la que decide si el año que viene siguen viniendo.')})

    return avisos


# ═══════════════════════════════════════════════════════════════════════════
#  LOS TRES MODELOS
# ═══════════════════════════════════════════════════════════════════════════
def _modelo(clave, titulo, intro, textos, dias, rotaciones, aviso_rotacion,
            capacidades, campos, bloques, principios, fuentes, revisar,
            cargas=CARGAS_BASE, fases=FASES_BASE):
    return {
        'segmento': clave,
        'titulo': titulo,
        'intro': intro,
        #  Las cuatro frases del formulario de alta. Están aquí y no en
        #  `segmentos.VOCABULARIO` porque hablan de la periodización, no del
        #  equipo: en un colegio «el primer día» no es el siguiente al partido.
        'nombre_rotacion': textos['rotacion'],
        'primer_dia': textos['primer_dia'],
        'intro_nueva': textos['intro_nueva'],
        'ejemplo_nombre': textos['ejemplo_nombre'],
        'vacio': textos['vacio'],
        'dias': dias,
        'rotaciones': rotaciones,
        'aviso_rotacion': aviso_rotacion,
        'capacidades': capacidades,
        'campos': campos,
        'bloques': bloques,
        'principios': principios,
        'fuentes': fuentes,
        'fuente': fuentes[0],
        'revisar': revisar,
        'cargas': cargas,
        'fases': fases,
        'carga_meta': {c: {'etiqueta': e, 'color': col, 'alto': h}
                       for c, e, col, h in cargas},
        'fase_meta': {c: {'etiqueta': e, 'color': col} for c, e, col in fases},
        'claves_campos': tuple(c for c, _ in campos),
    }


MODELOS = {
    'profesional': _modelo(
        'profesional',
        'Periodización del microciclo profesional',
        ('La semana va de partido a partido y cada día se nombra por su distancia al '
         'siguiente. Tres fases: recuperar, cargar y afinar.'),
        {'rotacion': 'Días entre partidos',
         'primer_dia': 'Primer día (el siguiente al partido)',
         'intro_nueva': ('Elige cuántos días separan un partido del siguiente. La semana '
                         'nace con la carga y la capacidad de cada día ya puestas.'),
         'ejemplo_nombre': 'Ej: Microciclo 7 — jornada 12',
         'vacio': ('Crea tu primer microciclo arriba. Puedes empezar por la semana de 7 '
                   'días, que es la que cabe entera.')},
        PRO_DIAS, PRO_ROTACIONES, PRO_AVISO_ROTACION, PRO_CAPACIDADES,
        PRO_CAMPOS, PRO_BLOQUES, PRO_PRINCIPIOS, PRO_FUENTES, pro_revisar),

    'semipro': _modelo(
        'semipro',
        'La semana semiprofesional',
        ('Tres o cuatro sesiones, jugadores que trabajan y ningún fisioterapeuta. '
         'Un solo día duro, la velocidad intocable y la prevención en el sitio de honor.'),
        {'rotacion': 'Días entre partidos',
         'primer_dia': 'Primer día (el siguiente al partido)',
         'intro_nueva': ('Elige cuántos días separan un partido del siguiente. La semana '
                         'nace con las sesiones repartidas y los días libres marcados: '
                         'aquí el descanso también es parte del plan.'),
         'ejemplo_nombre': 'Ej: Semana 12 — visita a Otavalo',
         'vacio': ('Crea tu primera semana arriba. La de 7 días trae tres entrenamientos '
                   'y la víspera, que es lo que de verdad cabe.')},
        SEMI_DIAS, SEMI_ROTACIONES, SEMI_AVISO_ROTACION, SEMI_CAPACIDADES,
        SEMI_CAMPOS, SEMI_BLOQUES, SEMI_PRINCIPIOS, SEMI_FUENTES, semi_revisar),

    'colegio': _modelo(
        'colegio',
        'La semana escolar',
        ('Aquí la semana no va de partido a partido: va de lunes a viernes, con clases '
         'en medio. El objetivo no es ganar la jornada — es que sigan jugando dentro de '
         'diez años.'),
        {'rotacion': 'Días que abarca la semana',
         'primer_dia': 'Primer día de la semana',
         'intro_nueva': ('Elige cuántos días abarca la semana que vas a planificar. Nace '
                         'con las sesiones, los días de clase sin equipo y la jornada ya '
                         'colocados.'),
         'ejemplo_nombre': 'Ej: Semana 5 — sub-14',
         'vacio': ('Crea tu primera semana arriba. La de 6 días trae tres sesiones y la '
                   'jornada, que es la semana típica del intercolegial.')},
        COL_DIAS, COL_ROTACIONES, COL_AVISO_ROTACION, COL_CAPACIDADES,
        COL_CAMPOS, COL_BLOQUES, COL_PRINCIPIOS, COL_FUENTES, col_revisar),
}


def de_segmento(clave):
    """El modelo de periodización de un segmento. Nunca devuelve None."""
    return MODELOS.get((clave or '').strip().lower()) or MODELOS['profesional']
