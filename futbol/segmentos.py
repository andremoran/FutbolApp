# -*- coding: utf-8 -*-
"""
futbol/segmentos.py — A quién entrena cada entrenador.

La app nació para un club profesional: cuerpo técnico completo, sesión diaria y
partido cada fin de semana. Toda la periodización de `microciclos.py` está
escrita sobre esa realidad, y está bien que así sea — es de donde sale la
evidencia.

El problema es que la mayoría de quien va a usar esto no vive ahí. Un equipo de
Segunda Categoría entrena tres tardes porque sus jugadores salen de trabajar a
las seis. Un colegio entrena dos veces entre clases y su objetivo no es ganar el
sábado: es que el chico siga jugando a los veinte años. Darles la planilla del
club profesional no es darles más, es darles algo que no pueden cumplir — y una
guía imposible de cumplir se ignora entera, incluida la parte que sí servía.

Por eso hay tres segmentos. No son etiquetas: cada uno decide

  · qué periodización se le ofrece al entrenador  (microciclo_modelos.py)
  · con qué palabras se le habla                  (VOCABULARIO)
  · contra qué evidencia se le avisa              (PRINCIPIOS de su modelo)
  · qué objetivos se le proponen                  (OBJETIVOS)
  · contra qué baremo se mide por defecto         (nivel_sugerido)

El segmento vive en el EQUIPO (`fut_teams.segmento`), nunca en la persona. El
jugador no elige: entra con el código de su entrenador y hereda el segmento de
ese equipo. Ver sql/schema_v14_segmentos.sql para el porqué.
"""
from . import db

PROFESIONAL = 'profesional'
SEMIPRO = 'semipro'
COLEGIO = 'colegio'

#  Por defecto, y con intención: todos los equipos que ya existen se crearon
#  con la app profesional y tienen que seguir viéndola igual. Un segmento nuevo
#  jamás puede cambiarle la plataforma a nadie por sorpresa.
POR_DEFECTO = PROFESIONAL


# ═══════════════════════════════════════════════════════════════════════════
#  LOS TRES SEGMENTOS
# ═══════════════════════════════════════════════════════════════════════════
#  El orden es el de la pantalla de alta, de menos a más estructura: es el
#  orden en que crece un entrenador, y deja arriba al que más va a usar esto.
SEGMENTOS = (
    {
        'clave': COLEGIO,
        'etiqueta': 'Colegio o escuela de formación',
        'corta': 'Colegio',
        'icono': 'book-open',
        'color': '#0ea5e9',
        'fondo': '#e0f2fe',
        'lema': 'Formar jugadores, no ganar el sábado',
        'descripcion': ('Intercolegial, escuelas de fútbol y categorías formativas. '
                        'Dos o tres sesiones a la semana, entre clases y deberes.'),
        'para_quien': ('Profesores de educación física, entrenadores de escuela '
                       'y categorías sub-10 a sub-18 de colegio.'),
        'realidad': ('El chico llega de clases, entrena 60-75 minutos y se va a hacer '
                     'deberes. Está creciendo, y unos crecen antes que otros. La '
                     'jornada intercolegial no es el objetivo: es una herramienta más.'),
        'edades': ('sub_10', 'sub_12', 'sub_14', 'sub_15', 'sub_16', 'sub_17', 'sub_18'),
        'nivel_baremo': 'formativo',
        'sesiones_semana': '2-3',
    },
    {
        'clave': SEMIPRO,
        'etiqueta': 'Semiprofesional o amateur competitivo',
        'corta': 'Semipro',
        'icono': 'shield',
        'color': '#f59e0b',
        'fondo': '#fef3c7',
        'lema': 'Competir de verdad con el tiempo que hay',
        'descripcion': ('Segunda categoría, ascenso, liga provincial, barrial fuerte y '
                        'universitario. Tres o cuatro sesiones por la tarde.'),
        'para_quien': ('Entrenadores de plantillas adultas cuyos jugadores trabajan '
                       'o estudian durante el día.'),
        'realidad': ('El jugador sale del trabajo y llega al entrenamiento ya cansado. '
                     'No hay fisioterapeuta ni GPS, la asistencia varía cada día y una '
                     'lesión le cuesta el sueldo, no solo la temporada.'),
        'edades': ('sub_18', 'sub_20', 'adulto'),
        'nivel_baremo': 'semipro',
        'sesiones_semana': '3-4',
    },
    {
        'clave': PROFESIONAL,
        'etiqueta': 'Club profesional o de élite',
        'corta': 'Profesional',
        'icono': 'award',
        'color': '#047857',
        'fondo': '#d1fae5',
        'lema': 'Llegar al partido en el mejor estado posible',
        'descripcion': ('Serie A, Serie B, reservas profesionales y selecciones. '
                        'Sesión diaria con cuerpo técnico completo.'),
        'para_quien': ('Cuerpos técnicos con preparador físico, dedicación completa '
                       'del jugador y competición semanal.'),
        'realidad': ('El jugador está disponible todos los días y su trabajo es jugar. '
                     'Hay datos, hay recuperación dirigida y el calendario manda.'),
        'edades': ('sub_18', 'sub_20', 'adulto'),
        'nivel_baremo': 'profesional',
        'sesiones_semana': '5-6',
    },
)

SEGMENTO_META = {s['clave']: s for s in SEGMENTOS}
CLAVES = tuple(s['clave'] for s in SEGMENTOS)


def valido(clave):
    """Normaliza cualquier cosa que llegue de fuera a un segmento real."""
    clave = (clave or '').strip().lower()
    return clave if clave in SEGMENTO_META else POR_DEFECTO


def meta(clave):
    """La ficha del segmento. Nunca devuelve None: siempre hay un segmento."""
    return SEGMENTO_META[valido(clave)]


# ═══════════════════════════════════════════════════════════════════════════
#  EL VOCABULARIO
# ═══════════════════════════════════════════════════════════════════════════
#  Las mismas pantallas, las mismas columnas de la base, otras palabras. Un
#  profesor de colegio no tiene «plantilla» ni «titulares»: tiene un grupo y
#  todos juegan. Llamar a las cosas como las llama quien las usa no es cosmética
#  — es lo que hace que la guía se lea en vez de saltársela.
#
#  Las CLAVES nunca cambian (son las columnas de `fut_microcycles.dias`); solo
#  cambia la etiqueta. Así un entrenador puede cambiar de segmento y lo que
#  tenía escrito sigue estando donde estaba.
VOCABULARIO = {
    PROFESIONAL: {
        'microciclo': 'Microciclo',
        'microciclos': 'Microciclos',
        'microciclo_un': 'un microciclo',
        'semana': 'la semana entre partidos',
        'partido': 'Partido',
        'partidos': 'Partidos',
        'plantilla': 'Plantilla',
        'jugadores': 'jugadores',
        'sesion': 'Sesión',
        'sesiones': 'sesiones',
        'grupo_a': 'titulares',
        'grupo_b': 'suplentes',
        'guia': 'Guía de periodización',
        'rotacion': 'Días entre partidos',
    },
    SEMIPRO: {
        'microciclo': 'Semana de trabajo',
        'microciclos': 'Semanas de trabajo',
        'microciclo_un': 'una semana',
        'semana': 'la semana entre partidos',
        'partido': 'Partido',
        'partidos': 'Partidos',
        'plantilla': 'Plantilla',
        'jugadores': 'jugadores',
        'sesion': 'Entrenamiento',
        'sesiones': 'entrenamientos',
        'grupo_a': 'los que jugaron',
        'grupo_b': 'los que no jugaron',
        'guia': 'Guía de la semana semiprofesional',
        'rotacion': 'Días entre partidos',
    },
    COLEGIO: {
        'microciclo': 'Semana escolar',
        'microciclos': 'Semanas escolares',
        'microciclo_un': 'una semana',
        'semana': 'la semana lectiva',
        'partido': 'Jornada',
        'partidos': 'Jornadas',
        'plantilla': 'Grupo',
        'jugadores': 'chicos',
        'sesion': 'Sesión',
        'sesiones': 'sesiones',
        'grupo_a': 'todos',
        'grupo_b': 'todos',
        'guia': 'Guía de formación',
        'rotacion': 'Días que abarca la semana',
    },
}


def palabras(clave):
    """El diccionario de palabras del segmento, listo para la plantilla."""
    return VOCABULARIO[valido(clave)]


# ═══════════════════════════════════════════════════════════════════════════
#  LOS OBJETIVOS
# ═══════════════════════════════════════════════════════════════════════════
#  Qué se persigue en cada segmento, en orden de importancia. Se enseñan al
#  elegir el segmento y en la cabecera de la guía. Son distintos de verdad: el
#  profesional busca llegar al partido, el semipro busca llegar a fin de
#  temporada entero, y el colegio busca que el chico siga jugando dentro de
#  diez años. Si el objetivo no cambia, el plan tampoco cambia.
OBJETIVOS = {
    PROFESIONAL: (
        ('Rendir el día del partido', 'Toda la semana se ordena alrededor de llegar fresco y preparado.'),
        ('Sostener la carga de la temporada', 'Acumular sin romperse, con la disponibilidad como primer indicador.'),
        ('Afinar el detalle', 'Balón parado, plan de partido y ajustes contra un rival concreto.'),
        ('Cuidar el activo', 'Cada jugador lesionado es un coste directo del club.'),
    ),
    SEMIPRO: (
        ('Llegar a fin de temporada con la plantilla entera', 'Sin fisioterapeuta, la prevención es lo único que evita perder a un jugador un mes.'),
        ('Rendir con tres sesiones', 'Lo que no cabe en la semana no existe. Todo lo importante va con balón.'),
        ('Que el jugador se cuide solo', 'El club no controla su descanso ni su comida: hay que enseñarle qué hacer los días que no viene.'),
        ('Competir el domingo', 'Ganar sigue siendo el objetivo — pero no a costa de los tres puntos siguientes.'),
    ),
    COLEGIO: (
        ('Que siga jugando dentro de diez años', 'El abandono, no la derrota, es el fracaso real de esta etapa.'),
        ('Construir al atleta antes que al futbolista', 'Coordinación, fuerza y variedad de movimiento: lo que después no se recupera.'),
        ('Que todos jueguen', 'Los minutos de juego son el estímulo formativo. Sentar a los que van más lentos es sacarlos del proceso.'),
        ('Cuidar el cuerpo que está creciendo', 'El estirón cambia lo que un chico puede soportar, y no llega a todos el mismo año.'),
        ('Ganar la jornada, si sale', 'Es una herramienta de aprendizaje, no la vara con la que se mide el trabajo.'),
    ),
}


def objetivos(clave):
    return OBJETIVOS[valido(clave)]


# ═══════════════════════════════════════════════════════════════════════════
#  QUÉ MEDIR EN CADA SEGMENTO
# ═══════════════════════════════════════════════════════════════════════════
#  El catálogo tiene 58 pruebas avaladas. Para un club profesional eso es una
#  biblioteca; para un profesor de colegio es un muro. Abre la pantalla, ve
#  «VO2máx directo» y «Dinamometría manual», entiende que esto no es para él y
#  no vuelve — aunque catorce de esas pruebas se las pueda tomar mañana con una
#  cinta métrica y un cronómetro.
#
#  Así que cada segmento trae SU batería: las pruebas por las que empezar, en
#  el orden en que conviene tomarlas. No se esconde nada — las 58 siguen ahí
#  debajo—, solo se dice cuáles son las suyas.
BATERIA = {
    COLEGIO: (
        #  La talla va PRIMERA y no es un adorno: es la que detecta el estirón,
        #  y el estirón es lo que decide cuánta carga de impacto aguanta cada
        #  chico ese trimestre. Repetida cada tres meses vale más que cualquier
        #  otra cosa que se mida en formación.
        'antropometria',
        'course_navette',       # resistencia — la de toda la vida en el colegio
        'salto_horizontal',     # potencia, con una cinta métrica
        'sprint_20m',           # velocidad, con cronómetro de mano basta
        'illinois',             # agilidad, ocho conos
        'sit_and_reach',        # flexibilidad
        'conduccion_conos',     # técnica
        'dominio_balon_fifa',   # control — y además les encanta
    ),
    SEMIPRO: (
        'antropometria',
        'yoyo_ir1',             # el estándar del fútbol: conos y un audio
        'sprint_30m',
        'cmj',                  # salto: lo que primero cae cuando hay fatiga
        'test_505',             # cambio de dirección
        'rsa',                  # repetir sprints — el partido es esto
        'conduccion_conos',
        'lspt',                 # técnica bajo presión
    ),
    PROFESIONAL: (
        'antropometria',
        'sprint_10m',
        'sprint_30m',
        'cmj',
        'yoyo_ir1',
        'rsa',
        'test_505',
        'lspt',
    ),
}

#  Pruebas que piden material de laboratorio o electrónica de medición. Existen
#  y están bien: en un club profesional se toman. Lo que no puede pasar es que
#  un colegio las intente y se frustre, así que en los segmentos que no tienen
#  ese material se avisa ANTES de abrirlas, no después de citar al grupo.
PRUEBAS_CON_MATERIAL = frozenset((
    'vo2max',              # analizador de gases
    'dinamometria',        # dinamómetro
    'squat_1rm',           # barra, discos y jaula
    'ift_30_15',           # audio + pista larga + control de velocidad
    'margaria_kalamen',    # plataforma de contacto en escaleras
    'rast',                # fotocélulas
    'tiro_potencia_radar',  # radar
    'y_balance',           # kit Y-Balance
))


def bateria(clave):
    """Las pruebas por las que empieza un equipo de este segmento."""
    return BATERIA[valido(clave)]


def avisa_material(clave):
    """Si a este segmento hay que advertirle de las pruebas con laboratorio."""
    return valido(clave) != PROFESIONAL


# ═══════════════════════════════════════════════════════════════════════════
#  PRIMEROS PASOS
# ═══════════════════════════════════════════════════════════════════════════
#  El camino más corto desde «acabo de entrar» hasta «esto ya me sirve», y es
#  distinto en cada segmento porque el destino es distinto.
#
#  El profesional llega antes teniendo gente, midiéndola y agendando. El
#  semipro necesita ANTES decir contra qué se mide, o sus pruebas salen
#  comparadas con un baremo que no es el suyo. Y el colegio necesita la talla,
#  que es lo único que le dice cuánta carga aguanta cada chico ese trimestre.
#
#  `clave` es la señal que marca el paso como hecho; la calcula la vista.
PASOS = {
    #  El profesional no se toca: son los tres de SetupChecklist.tsx, con sus
    #  mismas palabras. Su recorrido ya funcionaba.
    PROFESIONAL: (
        {'clave': 'plantilla', 'ruta': 'futbol.c_equipo', 'ico': 'user-plus',
         'et': 'Agregá tu primer jugador',
         'pista': 'Sumá jugadores manualmente o con el código de equipo'},
        {'clave': 'evaluacion', 'ruta': 'futbol.c_evaluaciones', 'ico': 'clipboard',
         'et': 'Evaluá a un jugador',
         'pista': 'Cargá su ficha técnica, física y mental'},
        {'clave': 'evento', 'ruta': 'futbol.c_calendario', 'ico': 'calendar',
         'et': 'Programá un entrenamiento',
         'pista': 'Creá tu primer evento en la agenda'},
    ),
    SEMIPRO: (
        {'clave': 'plantilla', 'ruta': 'futbol.c_equipo', 'ico': 'user-plus',
         'et': 'Arma tu plantilla',
         'pista': 'Con tu código de equipo, o apuntándolos a mano si no tienen cuenta'},
        {'clave': 'nivel', 'ruta': 'futbol.c_equipo_editar', 'ico': 'sliders',
         'et': 'Di contra qué se mide tu equipo',
         'pista': 'Sin esto, las pruebas se comparan con un baremo que no es el tuyo'},
        {'clave': 'evaluacion', 'ruta': 'futbol.c_evaluaciones', 'ico': 'clipboard',
         'et': 'Toma la primera prueba',
         'pista': 'Empieza por el Yo-Yo: conos, un audio y una tarde'},
        {'clave': 'microciclo', 'ruta': 'futbol.c_microciclos', 'ico': 'grid',
         'et': 'Escribe tu semana de trabajo',
         'pista': 'Tres entrenamientos y la víspera. El plan te avisa si te pasas'},
    ),
    COLEGIO: (
        {'clave': 'plantilla', 'ruta': 'futbol.c_equipo', 'ico': 'user-plus',
         'et': 'Arma tu grupo',
         'pista': 'Apúntalos a mano; en el colegio casi nadie tiene cuenta'},
        {'clave': 'nivel', 'ruta': 'futbol.c_equipo_editar', 'ico': 'sliders',
         'et': 'Elige la categoría de edad',
         'pista': 'Un sub-14 no puede medirse contra la marca de un adulto'},
        {'clave': 'talla', 'ruta': 'futbol.c_evaluaciones', 'ico': 'activity',
         'et': 'Mide la talla de todos',
         'pista': 'Es lo que detecta el estirón, y el estirón decide cuánto aguanta cada uno'},
        {'clave': 'microciclo', 'ruta': 'futbol.c_microciclos', 'ico': 'grid',
         'et': 'Escribe tu semana escolar',
         'pista': 'Dos o tres sesiones y los días de clase. También cuentan'},
    ),
}


def pasos(clave):
    return PASOS[valido(clave)]


# ═══════════════════════════════════════════════════════════════════════════
#  LO QUE LA IA TIENE QUE SABER
# ═══════════════════════════════════════════════════════════════════════════
#  Sin esto, el asistente le contesta a un profesor de colegio con protocolos
#  de élite: doble sesión, gimnasio, control de carga con GPS. Es un consejo
#  correcto para un club y una tontería para él — y basta una respuesta así
#  para que deje de preguntar.
#
#  Va en el prompt como una restricción explícita, no como un matiz. Los
#  modelos siguen mucho mejor un «NUNCA propongas X» que un «ten en cuenta que».
IA = {
    PROFESIONAL: {
        'quien': ('Entrena a un club PROFESIONAL: sesión diaria, cuerpo técnico '
                  'completo y partido cada fin de semana.'),
        'nunca': '',
    },
    SEMIPRO: {
        'quien': ('Entrena a un equipo SEMIPROFESIONAL o amateur competitivo. Sus '
                  'jugadores TRABAJAN o ESTUDIAN de día y entrenan tres o cuatro '
                  'tardes por semana. No hay fisioterapeuta, ni gimnasio del club, '
                  'ni GPS, y la asistencia cambia cada día.'),
        'nunca': ('- NUNCA propongas doble sesión, trabajo con máquinas de gimnasio, '
                  'recuperación dirigida ni nada que necesite estar disponible a diario.\n'
                  '- Da por hecho UN solo día duro por semana. Si propones más, te '
                  'equivocas.\n'
                  '- Prioriza siempre lo que se hace con balón, conos y peso corporal.\n'
                  '- La prevención de lesiones (calentamiento estructurado, nórdicos) '
                  'es lo de mayor valor aquí: recuérdala cuando venga a cuento.'),
    },
    COLEGIO: {
        'quien': ('Entrena en un COLEGIO o escuela de formación: chicos en edad '
                  'escolar, muchos en pleno crecimiento, dos o tres sesiones por '
                  'semana entre clases y deberes. El objetivo no es ganar la jornada: '
                  'es que sigan jugando dentro de diez años.'),
        'nunca': ('- NUNCA propongas cargas de adulto, trabajo de gimnasio con pesos '
                  'libres, dobles sesiones ni especialización temprana en una posición.\n'
                  '- NUNCA sugieras dejar a un chico sin jugar para asegurar un '
                  'resultado: los minutos SON el entrenamiento a esta edad.\n'
                  '- Prioriza el juego reducido, la coordinación y la técnica sobre el '
                  'trabajo físico analítico.\n'
                  '- Ten presentes el estirón, el sueño y los deberes: son parte del '
                  'plan, no excusas.\n'
                  '- Habla de aprender y de disfrutar, no de rendir.'),
    },
}


def guia_ia(clave):
    """Las dos líneas que el asistente necesita para no dar consejos de otro mundo."""
    return IA[valido(clave)]


# ═══════════════════════════════════════════════════════════════════════════
#  RESOLVER EL SEGMENTO
# ═══════════════════════════════════════════════════════════════════════════
def de_equipo(equipo):
    """El segmento de una ficha de equipo ya leída.

    Acepta el equipo provisional que compone `db.equipo_del_entrenador` cuando
    todavía no hay fila en `fut_teams`: ahí no hay segmento y cae al de por
    defecto, que es justo lo que se quiere.
    """
    return valido((equipo or {}).get('segmento'))


def del_entrenador(coach_id):
    """El segmento del equipo de un entrenador.

    Se cachea DENTRO de la petición. No es optimización prematura: al guardar
    una tanda de evaluaciones se resuelve el contexto de cada jugador uno por
    uno, y sin caché eso es una consulta a Supabase por jugador — con veinte en
    la plantilla, cuatro segundos de espera por una respuesta que es la misma
    veinte veces. El segmento no puede cambiar en mitad de una petición.
    """
    if not coach_id:
        return POR_DEFECTO

    cache = _cache()
    clave = str(coach_id)
    if clave in cache:
        return cache[clave]

    eq = db.one('fut_teams', 'segmento equipo', coach_id=coach_id) or {}
    cache[clave] = valido(eq.get('segmento'))
    return cache[clave]


def _cache():
    """El diccionario de segmentos ya resueltos en esta petición.

    Fuera de una petición —un script suelto, una prueba— devuelve uno nuevo
    cada vez, que es lo mismo que no cachear.
    """
    from flask import g, has_request_context
    if not has_request_context():
        return {}
    if not hasattr(g, '_fut_segmentos'):
        g._fut_segmentos = {}
    return g._fut_segmentos


def del_usuario(usuario):
    """El segmento de quien está mirando la pantalla, sea quien sea.

    El entrenador lo lee de su equipo. El jugador lo hereda del equipo al que
    se unió con el código — que es exactamente lo que el CEO pidió: el jugador
    no elige nada, cae donde esté su entrenador.
    """
    if not usuario or not getattr(usuario, 'id', None):
        return POR_DEFECTO
    if getattr(usuario, 'role', '') == 'especialista':
        return del_entrenador(db.equipo_id(usuario.id))
    #  `entrenador_del_jugador` devuelve la FICHA del entrenador, no su id — y
    #  ese entrenador puede ser un asistente, así que se pasa por `equipo_id`
    #  para acabar en el principal, que es quien tiene la fila de `fut_teams`.
    coach = db.entrenador_del_jugador(usuario.id)
    if not coach or not coach.get('id'):
        return POR_DEFECTO
    return del_entrenador(db.equipo_id(coach['id']))


def guardar(coach_id, clave):
    """Cambia el segmento del equipo.

    Obligatorio a propósito, por el mismo motivo que `guardar_contexto`: si se
    perdiera en silencio el entrenador leería «Listo» y seguiría planificando
    con el modelo de otro segmento. Aquí mentir sale caro.
    """
    from datetime import datetime, timezone
    clave = valido(clave)
    eq = db.one('fut_teams', 'equipo segmento', coach_id=coach_id)
    if eq:
        db.update('fut_teams', {'segmento': clave}, 'segmento up',
                  obligatorio=True, id=eq['id'])
    else:
        db.insert('fut_teams', {
            'coach_id': coach_id, 'nombre': 'Mi equipo', 'segmento': clave,
            'creado': datetime.now(timezone.utc).isoformat(),
        }, 'segmento nuevo', obligatorio=True)
    #  Si no se limpia, lo que se lea después en ESTA misma petición sería el
    #  segmento viejo: justo el caso de guardar y volver a pintar la pantalla.
    _cache().pop(str(coach_id), None)
    return clave


def sembrar(coach_id, clave):
    """Deja el segmento puesto al crear la cuenta. Sin obligar.

    Va en el camino del registro, y ahí un fallo de Supabase no puede costarle
    la cuenta a nadie: si no se puede escribir, el entrenador entra igual en el
    segmento por defecto y lo cambia desde los ajustes de su equipo.
    """
    try:
        return guardar(coach_id, clave)
    except Exception:            # noqa: BLE001 — el alta es más importante
        return POR_DEFECTO


def nivel_sugerido(clave):
    """El nivel competitivo por defecto de un equipo de este segmento.

    Solo se usa cuando el entrenador NO ha configurado «Nivel del equipo»: en
    cuanto lo toca, manda lo que él eligió. Un colegio con una selección muy
    buena puede querer medirse contra juvenil, y debe poder.

    Existe porque el respaldo anterior era `amateur` para cualquier plantilla
    adulta sin configurar, y eso comparaba a los jugadores de un club
    profesional contra el baremo de una liga barrial. El resultado salía
    inflado y el entrenador no tenía forma de saber por qué.
    """
    return meta(clave)['nivel_baremo']
