# -*- coding: utf-8 -*-
"""
futbol/tests_catalogo.py — Las pruebas estándar y sus baremos.

Por qué vive en el código y no en la base de datos
──────────────────────────────────────────────────
Un baremo publicado (Cooper 1968, Bangsbo 2008, Haugen 2013…) es una constante,
no un dato del cliente. Sembrarlo en la base obligaría a repetir la siembra en
cada entorno y a vigilar que no se desincronicen; aquí se lee igual en local,
en Vercel y en el VPS, y se versiona con el resto del código.

Lo que SÍ va a la base: las pruebas que inventa el entrenador
(`fut_eval_templates`), los baremos que él ajusta (`fut_eval_ranges`) y los
resultados (`fut_eval_results`).

El problema que resuelven los baremos
─────────────────────────────────────
Un 2.400 m en Cooper es excelente para un sub-14 de escuelita y flojo para un
profesional. Por eso cada baremo está estratificado por CATEGORÍA DE EDAD ×
NIVEL COMPETITIVO, y la búsqueda cae hacia atrás cuando no hay coincidencia
exacta (ver `baremo_para`).

Fuentes de los valores
──────────────────────
  · Cooper KH (1968) JAMA — test de 12 minutos.
  · Bangsbo J, Iaia FM, Krustrup P (2008) Sports Med — Yo-Yo IR1/IR2.
  · Krustrup P et al. (2003) Med Sci Sports Exerc — Yo-Yo IR1 en fútbol de élite.
  · Haugen T, Tønnessen E, Seiler S (2013) Int J Sports Physiol Perform —
    velocidad y CMJ en futbolistas noruegos por nivel y sexo.
  · Getchell B (1979) — Illinois Agility Test.
  · Semenick D (1990) NSCA — T-Test.
  · Léger L et al. (1988) J Sports Sci — course navette 20 m.
  · Ali A et al. (2007) J Sports Sci — Loughborough Soccer Passing Test.
  · ACSM's Guidelines (10ª ed.) — sit and reach y composición corporal.
  · Council of Europe (1993) EUROFIT — salto horizontal y abdominales.
  · Reilly T, Bangsbo J, Franks A (2000) J Sports Sci — perfil antropométrico.
"""

# ─── Ejes de estratificación ────────────────────────────────────────────────
CATEGORIAS_EDAD = [
    ('sub_10', 'Sub-10'), ('sub_12', 'Sub-12'), ('sub_14', 'Sub-14'),
    ('sub_15', 'Sub-15'), ('sub_16', 'Sub-16'), ('sub_17', 'Sub-17'),
    ('sub_18', 'Sub-18'), ('sub_20', 'Sub-20'), ('adulto', 'Adulto'),
    ('general', 'General'),
]

NIVELES_COMPETITIVOS = [
    ('escuela',     'Escuela',          'Iniciación, sub-10 a sub-12'),
    ('formativo',   'Formativo',        'Academia, sub-13 a sub-16'),
    ('juvenil',     'Juvenil',          'Reservas y juveniles competitivos'),
    ('amateur',     'Amateur',          'Adulto de liga barrial o provincial'),
    ('semipro',     'Semiprofesional',  'Segunda categoría, ascenso'),
    ('profesional', 'Profesional',      'Serie A/B, ligas profesionales'),
    ('elite',       'Élite',            'Selección, torneos internacionales'),
    ('general',     'General',          'Sin contexto definido'),
]

# Orden de mejor a peor. El puntaje 0-100 sale de aquí.
NIVELES_RENDIMIENTO = [
    ('elite',     'Élite',      '#047857', '#d1fae5', 95),
    ('bueno',     'Bueno',      '#0f766e', '#ccfbf1', 78),
    ('promedio',  'Promedio',   '#475569', '#f1f5f9', 58),
    ('debil',     'A mejorar',  '#b45309', '#fef3c7', 38),
    ('muy_debil', 'Bajo',       '#b91c1c', '#fee2e2', 18),
]

NIVEL_META = {clave: {'etiqueta': et, 'color': c, 'fondo': f, 'puntaje': p}
              for clave, et, c, f, p in NIVELES_RENDIMIENTO}

MAYOR = 'mayor_mejor'      # más metros, más centímetros: mejor
MENOR = 'menor_mejor'      # menos segundos: mejor


def _campo(clave, etiqueta, unidad, minimo, maximo, decimales=2,
           ejemplo='', direccion=MENOR, principal=True, tipo='numero'):
    return {'clave': clave, 'etiqueta': etiqueta, 'unidad': unidad,
            'min': minimo, 'max': maximo, 'decimales': decimales,
            'ejemplo': ejemplo, 'direccion': direccion,
            'principal': principal, 'tipo': tipo}


def _nota(clave, etiqueta, ejemplo='7', principal=True):
    """Campo de valoración del entrenador, 1 a 10."""
    return _campo(clave, etiqueta, '/10', 1, 10, 0, ejemplo,
                  MAYOR, principal, tipo='nota')


# ═══════════════════════════════════════════════════════════════════════════
#  EL CATÁLOGO
# ═══════════════════════════════════════════════════════════════════════════
#  Cada prueba lleva:
#    campos    — qué se mide (una prueba puede medir varias cosas)
#    baremos   — {campo: {(edad, nivel): [elite, bueno, promedio, debil]}}
#                Los cuatro cortes definen los cinco niveles de rendimiento.
#    'general' como edad o nivel = "sirve para cualquiera"; la búsqueda cae
#    hacia ahí cuando no hay un baremo más específico.
# ═══════════════════════════════════════════════════════════════════════════

CATALOGO = {

    # ─────────────────────────── RESISTENCIA ───────────────────────────────
    'cooper': {
        'nombre': 'Test de Cooper (12 min)',
        'categoria': 'fisico',
        'subcategoria': 'Resistencia aeróbica',
        'icono': 'activity',
        'descripcion': 'Máxima distancia recorrida corriendo durante 12 minutos.',
        'protocolo': (
            'Pista marcada cada 50 m. El jugador corre 12 minutos exactos '
            'intentando cubrir la mayor distancia posible; puede caminar si lo '
            'necesita, pero no parar. Se anotan los metros al sonar el silbato. '
            'Conviene medirlo con el equipo descansado y a la misma hora del día.'),
        'fuente': 'Cooper KH (1968), JAMA 203(3):201-204',
        'formula': 'VO₂máx ≈ (metros − 504,9) / 44,73',
        'campos': [
            _campo('distancia', 'Distancia', 'm', 800, 5000, 0, '2800', MAYOR),
        ],
        'baremos': {
            'distancia': {
                ('general', 'elite'):       [3200, 2950, 2750, 2500],
                ('general', 'profesional'): [3050, 2850, 2650, 2400],
                ('general', 'semipro'):     [2900, 2700, 2500, 2250],
                ('general', 'amateur'):     [2750, 2550, 2350, 2100],
                ('sub_20', 'general'):      [2950, 2750, 2550, 2300],
                ('sub_18', 'general'):      [2850, 2650, 2450, 2200],
                ('sub_17', 'general'):      [2750, 2550, 2350, 2100],
                ('sub_16', 'general'):      [2650, 2450, 2250, 2000],
                ('sub_15', 'general'):      [2550, 2350, 2150, 1900],
                ('sub_14', 'general'):      [2400, 2200, 2000, 1780],
                ('sub_12', 'general'):      [2200, 2000, 1820, 1600],
                ('sub_10', 'general'):      [1950, 1780, 1600, 1400],
                ('general', 'general'):     [2800, 2600, 2400, 2150],
            },
        },
    },

    'yoyo_ir1': {
        'nombre': 'Yo-Yo Intermittent Recovery 1',
        'categoria': 'fisico',
        'subcategoria': 'Resistencia intermitente',
        'icono': 'repeat',
        'descripcion': 'Resistencia con recuperación incompleta: el esfuerzo real del fútbol.',
        'protocolo': (
            'Ida y vuelta de 20 m siguiendo las señales sonoras, con 10 s de '
            'trote de recuperación entre series. Se acaba a la segunda vez que '
            'no se llega a tiempo a la línea. Se anota el último nivel completado '
            'y la distancia total. Es la prueba de resistencia más específica '
            'que hay para fútbol.'),
        'fuente': 'Bangsbo, Iaia & Krustrup (2008), Sports Med 38(1):37-51',
        'formula': 'VO₂máx ≈ distancia (m) × 0,0084 + 36,4',
        'campos': [
            _campo('distancia', 'Distancia total', 'm', 200, 3600, 0, '1840', MAYOR),
            _campo('nivel', 'Nivel alcanzado', '', 1, 23, 1, '18.5', MAYOR, principal=False),
        ],
        'baremos': {
            'distancia': {
                ('general', 'elite'):       [2400, 2120, 1880, 1600],
                ('general', 'profesional'): [2200, 1960, 1720, 1480],
                ('general', 'semipro'):     [2000, 1760, 1520, 1280],
                ('general', 'amateur'):     [1760, 1520, 1280, 1040],
                ('sub_20', 'general'):      [2160, 1920, 1680, 1400],
                ('sub_18', 'general'):      [2040, 1800, 1560, 1320],
                ('sub_17', 'general'):      [1920, 1680, 1440, 1200],
                ('sub_16', 'general'):      [1760, 1520, 1320, 1080],
                ('sub_15', 'general'):      [1600, 1400, 1200, 960],
                ('sub_14', 'general'):      [1440, 1240, 1040, 840],
                ('general', 'general'):     [2000, 1760, 1520, 1240],
            },
        },
    },

    'course_navette': {
        'nombre': 'Course Navette (20 m)',
        'categoria': 'fisico',
        'subcategoria': 'Resistencia aeróbica',
        'icono': 'activity',
        'descripcion': 'Ida y vuelta de 20 m a ritmo creciente marcado por señales.',
        'protocolo': (
            'Dos líneas a 20 m. El jugador va y viene siguiendo las señales, que '
            'se aceleran cada minuto (un palier). Termina cuando falla dos veces '
            'seguidas. Se anota el palier alcanzado con su fracción (ej. 11,5).'),
        'fuente': 'Léger L et al. (1988), J Sports Sci 6(2):93-101',
        'formula': 'VO₂máx ≈ 31,025 + 3,238·v − 3,248·edad + 0,1536·v·edad',
        'campos': [
            _campo('palier', 'Palier alcanzado', '', 1, 21, 1, '12.5', MAYOR),
        ],
        'baremos': {
            'palier': {
                ('general', 'elite'):       [14.0, 13.0, 12.0, 10.5],
                ('general', 'profesional'): [13.5, 12.5, 11.5, 10.0],
                ('general', 'amateur'):     [12.0, 11.0, 10.0, 8.5],
                ('sub_17', 'general'):      [12.5, 11.5, 10.5, 9.0],
                ('sub_15', 'general'):      [11.5, 10.5, 9.5, 8.0],
                ('sub_14', 'general'):      [10.5, 9.5, 8.5, 7.0],
                ('general', 'general'):     [13.0, 12.0, 11.0, 9.5],
            },
        },
    },

    'vo2max': {
        'nombre': 'VO₂ máximo',
        'categoria': 'fisico',
        'subcategoria': 'Resistencia aeróbica',
        'icono': 'wind',
        'descripcion': 'Consumo máximo de oxígeno, medido o estimado.',
        'protocolo': (
            'Anota el valor que dé el laboratorio, el pulsómetro o la fórmula de '
            'Cooper / Yo-Yo. Sirve para seguir la evolución aunque cambie la '
            'prueba con la que se estimó, siempre que se anote de dónde sale.'),
        'fuente': 'Reilly, Bangsbo & Franks (2000), J Sports Sci 18(9):669-683',
        'campos': [
            _campo('vo2', 'VO₂ máx', 'ml/kg/min', 25, 90, 1, '58.5', MAYOR),
        ],
        'baremos': {
            'vo2': {
                ('general', 'elite'):       [65, 61, 57, 52],
                ('general', 'profesional'): [62, 58, 54, 49],
                ('general', 'semipro'):     [58, 54, 50, 46],
                ('general', 'amateur'):     [54, 50, 46, 42],
                ('sub_17', 'general'):      [60, 56, 52, 47],
                ('sub_15', 'general'):      [56, 52, 48, 44],
                ('general', 'general'):     [60, 56, 52, 47],
            },
        },
    },

    # ─────────────────────────── VELOCIDAD ─────────────────────────────────
    'sprint_10m': {
        'nombre': 'Sprint 10 m',
        'categoria': 'fisico',
        'subcategoria': 'Aceleración',
        'icono': 'zap',
        'descripcion': 'Capacidad de arranque: los primeros 10 metros.',
        'protocolo': (
            'Salida de parado, pie adelantado a 50 cm de la línea. El cronómetro '
            'arranca al primer movimiento (o con fotocélula). Dos intentos con '
            '3 minutos de descanso; se anota el mejor. Sin viento a favor.'),
        'fuente': 'Haugen, Tønnessen & Seiler (2013), IJSPP 8(2):148-156',
        'campos': [
            _campo('tiempo', 'Tiempo', 's', 1.0, 3.5, 2, '1.78', MENOR),
        ],
        'baremos': {
            'tiempo': {
                ('general', 'elite'):       [1.70, 1.76, 1.83, 1.92],
                ('general', 'profesional'): [1.73, 1.79, 1.86, 1.95],
                ('general', 'semipro'):     [1.77, 1.83, 1.90, 1.99],
                ('general', 'amateur'):     [1.82, 1.89, 1.97, 2.06],
                ('sub_18', 'general'):      [1.76, 1.82, 1.89, 1.98],
                ('sub_17', 'general'):      [1.79, 1.85, 1.92, 2.01],
                ('sub_16', 'general'):      [1.83, 1.89, 1.96, 2.05],
                ('sub_15', 'general'):      [1.87, 1.94, 2.02, 2.11],
                ('sub_14', 'general'):      [1.93, 2.00, 2.09, 2.19],
                ('sub_12', 'general'):      [2.05, 2.14, 2.24, 2.36],
                ('general', 'general'):     [1.76, 1.82, 1.90, 1.99],
            },
        },
    },

    'sprint_20m': {
        'nombre': 'Sprint 20 m',
        'categoria': 'fisico',
        'subcategoria': 'Velocidad',
        'icono': 'zap',
        'descripcion': 'Velocidad en la distancia que más se repite en un partido.',
        'protocolo': (
            'Salida de parado. Dos conos a 20 m, cronómetro al primer movimiento. '
            'Dos intentos con 3 min de descanso, se anota el mejor. '
            'La mayoría de sprints de un partido no pasan de 20 m.'),
        'fuente': 'Haugen, Tønnessen & Seiler (2013), IJSPP 8(2):148-156',
        'campos': [
            _campo('tiempo', 'Tiempo', 's', 2.0, 5.5, 2, '3.02', MENOR),
        ],
        'baremos': {
            'tiempo': {
                ('general', 'elite'):       [2.94, 3.02, 3.11, 3.23],
                ('general', 'profesional'): [2.99, 3.07, 3.16, 3.28],
                ('general', 'semipro'):     [3.05, 3.13, 3.22, 3.35],
                ('general', 'amateur'):     [3.12, 3.21, 3.31, 3.45],
                ('sub_18', 'general'):      [3.02, 3.10, 3.19, 3.31],
                ('sub_17', 'general'):      [3.07, 3.15, 3.24, 3.37],
                ('sub_16', 'general'):      [3.13, 3.21, 3.31, 3.44],
                ('sub_15', 'general'):      [3.20, 3.29, 3.40, 3.54],
                ('sub_14', 'general'):      [3.30, 3.40, 3.52, 3.67],
                ('sub_12', 'general'):      [3.52, 3.64, 3.78, 3.96],
                ('general', 'general'):     [3.00, 3.09, 3.19, 3.31],
            },
        },
    },

    'sprint_30m': {
        'nombre': 'Sprint 30 m',
        'categoria': 'fisico',
        'subcategoria': 'Velocidad',
        'icono': 'zap',
        'descripcion': 'Velocidad punta con lanzamiento completo.',
        'protocolo': (
            'Dos conos a 30 m, salida de parado. Cronómetro al primer movimiento '
            'o fotocélulas en ambos extremos. Dos intentos con 4 min de descanso; '
            'se anota el mejor. Si además cronometras el paso por los 10 m, tienes '
            'aceleración y velocidad punta en la misma carrera.'),
        'fuente': 'Haugen, Tønnessen & Seiler (2013), IJSPP 8(2):148-156',
        'campos': [
            _campo('tiempo', 'Tiempo', 's', 3.0, 8.0, 2, '4.20', MENOR),
        ],
        'baremos': {
            'tiempo': {
                ('general', 'elite'):       [4.02, 4.14, 4.27, 4.44],
                ('general', 'profesional'): [4.10, 4.22, 4.35, 4.52],
                ('general', 'semipro'):     [4.19, 4.31, 4.44, 4.62],
                ('general', 'amateur'):     [4.30, 4.43, 4.57, 4.76],
                ('sub_18', 'general'):      [4.15, 4.27, 4.40, 4.57],
                ('sub_17', 'general'):      [4.22, 4.34, 4.47, 4.65],
                ('sub_16', 'general'):      [4.31, 4.43, 4.57, 4.75],
                ('sub_15', 'general'):      [4.42, 4.55, 4.69, 4.88],
                ('sub_14', 'general'):      [4.57, 4.71, 4.86, 5.07],
                ('sub_12', 'general'):      [4.90, 5.06, 5.24, 5.48],
                ('general', 'general'):     [4.12, 4.24, 4.38, 4.55],
            },
        },
    },

    'rsa': {
        'nombre': 'Sprints repetidos (RSA 6×30 m)',
        'categoria': 'fisico',
        'subcategoria': 'Velocidad resistida',
        'icono': 'repeat',
        'descripcion': 'Aguantar la velocidad cuando hay que repetirla.',
        'protocolo': (
            'Seis sprints de 30 m con 20 s de recuperación pasiva entre uno y '
            'otro. Se anota el tiempo medio y el peor. El índice de fatiga '
            '—cuánto se cae del mejor al peor— importa más que el tiempo suelto: '
            'por debajo del 5 % es excelente.'),
        'fuente': 'Rampinini E et al. (2007), Int J Sports Med 28(3):228-235',
        'formula': 'Índice de fatiga = (peor − mejor) / mejor × 100',
        'campos': [
            _campo('media', 'Tiempo medio', 's', 3.0, 8.0, 2, '4.42', MENOR),
            _campo('peor', 'Peor tiempo', 's', 3.0, 9.0, 2, '4.71', MENOR, principal=False),
            _campo('fatiga', 'Índice de fatiga', '%', 0, 30, 1, '4.8', MENOR, principal=False),
        ],
        'baremos': {
            'media': {
                ('general', 'elite'):       [4.20, 4.33, 4.47, 4.65],
                ('general', 'profesional'): [4.29, 4.42, 4.56, 4.74],
                ('general', 'amateur'):     [4.50, 4.64, 4.79, 4.99],
                ('sub_17', 'general'):      [4.42, 4.55, 4.69, 4.88],
                ('sub_15', 'general'):      [4.63, 4.77, 4.92, 5.12],
                ('general', 'general'):     [4.32, 4.45, 4.59, 4.78],
            },
            'fatiga': {
                ('general', 'general'):     [3.5, 5.0, 6.5, 8.5],
            },
        },
    },

    # ─────────────────────────── POTENCIA ──────────────────────────────────
    'cmj': {
        'nombre': 'Salto con contramovimiento (CMJ)',
        'categoria': 'fisico',
        'subcategoria': 'Potencia de piernas',
        'icono': 'trending-up',
        'descripcion': 'Potencia del tren inferior con el ciclo estiramiento-acortamiento.',
        'protocolo': (
            'Manos en la cadera para que no ayuden los brazos. Desde de pie, el '
            'jugador se agacha rápido hasta media sentadilla y salta lo más alto '
            'posible; cae en el mismo sitio. Tres intentos, se anota el mejor. '
            'Sirve alfombra de contacto, app de móvil a cámara lenta o el método '
            'de la tiza en la pared.'),
        'fuente': 'Haugen, Tønnessen & Seiler (2013), IJSPP 8(2):148-156',
        'campos': [
            _campo('altura', 'Altura', 'cm', 10, 80, 1, '42.5', MAYOR),
        ],
        'baremos': {
            'altura': {
                ('general', 'elite'):       [46, 42, 38, 33],
                ('general', 'profesional'): [44, 40, 36, 31],
                ('general', 'semipro'):     [41, 37, 33, 29],
                ('general', 'amateur'):     [38, 34, 30, 26],
                ('sub_18', 'general'):      [43, 39, 35, 30],
                ('sub_17', 'general'):      [41, 37, 33, 28],
                ('sub_16', 'general'):      [38, 34, 30, 26],
                ('sub_15', 'general'):      [35, 31, 27, 23],
                ('sub_14', 'general'):      [32, 28, 24, 20],
                ('sub_12', 'general'):      [27, 24, 20, 17],
                ('general', 'general'):     [42, 38, 34, 29],
            },
        },
    },

    'sj': {
        'nombre': 'Salto sin contramovimiento (SJ)',
        'categoria': 'fisico',
        'subcategoria': 'Potencia de piernas',
        'icono': 'trending-up',
        'descripcion': 'Fuerza explosiva pura, sin aprovechar el rebote elástico.',
        'protocolo': (
            'El jugador se queda quieto 3 segundos en media sentadilla (90°) y '
            'salta sin bajar más. Manos en la cadera. Comparado con el CMJ da el '
            'índice elástico: si el CMJ supera al SJ en menos del 5 %, hay poco '
            'aprovechamiento elástico y toca trabajar pliometría.'),
        'fuente': 'Bosco C, Luhtanen P, Komi PV (1983), Eur J Appl Physiol 50:273-282',
        'formula': 'Índice elástico = (CMJ − SJ) / SJ × 100',
        'campos': [
            _campo('altura', 'Altura', 'cm', 10, 75, 1, '38.0', MAYOR),
        ],
        'baremos': {
            'altura': {
                ('general', 'elite'):       [42, 38, 34, 30],
                ('general', 'profesional'): [40, 36, 32, 28],
                ('general', 'amateur'):     [35, 31, 27, 23],
                ('sub_17', 'general'):      [37, 33, 29, 25],
                ('sub_15', 'general'):      [32, 28, 24, 21],
                ('general', 'general'):     [38, 34, 30, 26],
            },
        },
    },

    'abalakov': {
        'nombre': 'Salto Abalakov',
        'categoria': 'fisico',
        'subcategoria': 'Potencia de piernas',
        'icono': 'trending-up',
        'descripcion': 'Salto máximo con ayuda de brazos: lo que se usa al rematar de cabeza.',
        'protocolo': (
            'Igual que el CMJ pero con los brazos libres y carrera de cero pasos. '
            'Es el salto que de verdad hace un central al despejar de cabeza. '
            'Suele dar entre 4 y 8 cm más que el CMJ.'),
        'fuente': 'Abalakov (1938); baremos de Reilly, Bangsbo & Franks (2000)',
        'campos': [
            _campo('altura', 'Altura', 'cm', 15, 90, 1, '50.0', MAYOR),
        ],
        'baremos': {
            'altura': {
                ('general', 'elite'):       [56, 51, 46, 40],
                ('general', 'profesional'): [53, 48, 43, 38],
                ('general', 'amateur'):     [46, 42, 37, 32],
                ('sub_17', 'general'):      [49, 44, 39, 34],
                ('sub_15', 'general'):      [42, 38, 33, 28],
                ('general', 'general'):     [51, 46, 41, 36],
            },
        },
    },

    'salto_horizontal': {
        'nombre': 'Salto horizontal a pies juntos',
        'categoria': 'fisico',
        'subcategoria': 'Potencia de piernas',
        'icono': 'move-horizontal',
        'descripcion': 'Potencia horizontal. No hace falta más que una cinta métrica.',
        'protocolo': (
            'De pie tras la línea, pies juntos. Salta hacia adelante con impulso '
            'de brazos y cae con los dos pies. Se mide de la línea al talón más '
            'retrasado. Tres intentos, se anota el mejor.'),
        'fuente': 'EUROFIT, Council of Europe (1993)',
        'campos': [
            _campo('distancia', 'Distancia', 'cm', 80, 320, 0, '215', MAYOR),
        ],
        'baremos': {
            'distancia': {
                ('general', 'elite'):       [255, 240, 225, 205],
                ('general', 'profesional'): [245, 230, 215, 195],
                ('general', 'amateur'):     [230, 215, 200, 180],
                ('sub_18', 'general'):      [240, 225, 210, 190],
                ('sub_16', 'general'):      [225, 210, 195, 175],
                ('sub_14', 'general'):      [200, 185, 170, 152],
                ('sub_12', 'general'):      [175, 162, 148, 132],
                ('general', 'general'):     [240, 225, 210, 190],
            },
        },
    },

    # ─────────────────────────── AGILIDAD ──────────────────────────────────
    'illinois': {
        'nombre': 'Test de agilidad de Illinois',
        'categoria': 'fisico',
        'subcategoria': 'Agilidad',
        'icono': 'shuffle',
        'descripcion': 'Cambios de dirección a alta velocidad en circuito cerrado.',
        'protocolo': (
            'Circuito de 10 m de largo por 5 de ancho, con 4 conos en el centro '
            'separados 3,3 m. Se sale tumbado boca abajo con las manos a la altura '
            'de los hombros; a la señal se recorre el circuito en zig-zag. '
            'Un intento por jugador con 5 min de recuperación si se repite.'),
        'fuente': 'Getchell B (1979), Physical Fitness: A Way of Life, 2ª ed.',
        'campos': [
            _campo('tiempo', 'Tiempo', 's', 12, 30, 2, '15.80', MENOR),
        ],
        'baremos': {
            'tiempo': {
                ('general', 'elite'):       [15.00, 15.60, 16.30, 17.20],
                ('general', 'profesional'): [15.20, 15.90, 16.60, 17.50],
                ('general', 'amateur'):     [15.90, 16.60, 17.40, 18.30],
                ('sub_17', 'general'):      [15.60, 16.30, 17.00, 17.90],
                ('sub_15', 'general'):      [16.30, 17.00, 17.80, 18.70],
                ('general', 'general'):     [15.20, 15.90, 16.70, 17.60],
            },
        },
    },

    'test_505': {
        'nombre': 'Test 505 (cambio de dirección)',
        'categoria': 'fisico',
        'subcategoria': 'Agilidad',
        'icono': 'corner-up-left',
        'descripcion': 'Frenar y volver a acelerar en 180°: el gesto del lateral.',
        'protocolo': (
            'Lanzamiento de 10 m, se cronometra desde los 5 m antes de la línea de '
            'giro: el jugador pisa la línea, gira 180° y vuelve a cruzar los 5 m. '
            'Se mide con cada pierna por separado; una diferencia mayor al 10 % '
            'entre lados es una asimetría a corregir.'),
        'fuente': 'Draper JA & Lancaster MG (1985), Aust J Sci Med Sport 17(1):15-18',
        'campos': [
            _campo('derecha', 'Giro pierna derecha', 's', 1.8, 4.0, 2, '2.35', MENOR),
            _campo('izquierda', 'Giro pierna izquierda', 's', 1.8, 4.0, 2, '2.38',
                   MENOR, principal=False),
        ],
        'baremos': {
            'derecha': {
                ('general', 'elite'):       [2.20, 2.30, 2.42, 2.56],
                ('general', 'profesional'): [2.25, 2.36, 2.48, 2.62],
                ('general', 'amateur'):     [2.36, 2.48, 2.60, 2.75],
                ('sub_17', 'general'):      [2.30, 2.41, 2.53, 2.68],
                ('general', 'general'):     [2.26, 2.37, 2.49, 2.63],
            },
            'izquierda': {
                ('general', 'elite'):       [2.20, 2.30, 2.42, 2.56],
                ('general', 'profesional'): [2.25, 2.36, 2.48, 2.62],
                ('general', 'amateur'):     [2.36, 2.48, 2.60, 2.75],
                ('sub_17', 'general'):      [2.30, 2.41, 2.53, 2.68],
                ('general', 'general'):     [2.26, 2.37, 2.49, 2.63],
            },
        },
    },

    't_test': {
        'nombre': 'T-Test',
        'categoria': 'fisico',
        'subcategoria': 'Agilidad',
        'icono': 'shuffle',
        'descripcion': 'Agilidad en cuatro direcciones: frente, lateral y espalda.',
        'protocolo': (
            'Cuatro conos en T: 10 m de frente y 5 m a cada lado. Se corre de '
            'frente al cono central, desplazamiento lateral al izquierdo, lateral '
            'hasta el derecho, vuelta al centro y de espaldas hasta la salida. '
            'Los pies no se cruzan en el desplazamiento lateral y hay que tocar '
            'cada cono con la mano.'),
        'fuente': 'Semenick D (1990), NSCA Journal 12(1):36-37',
        'campos': [
            _campo('tiempo', 'Tiempo', 's', 7, 18, 2, '10.20', MENOR),
        ],
        'baremos': {
            'tiempo': {
                ('general', 'elite'):       [9.20, 9.70, 10.30, 11.00],
                ('general', 'profesional'): [9.50, 10.00, 10.60, 11.30],
                ('general', 'amateur'):     [10.10, 10.70, 11.40, 12.20],
                ('sub_17', 'general'):      [9.90, 10.50, 11.10, 11.90],
                ('sub_15', 'general'):      [10.50, 11.10, 11.80, 12.60],
                ('general', 'general'):     [9.50, 10.10, 10.70, 11.50],
            },
        },
    },

    # ─────────────────────── FLEXIBILIDAD Y FUERZA ─────────────────────────
    'sit_and_reach': {
        'nombre': 'Flexión de tronco (sit and reach)',
        'categoria': 'fisico',
        'subcategoria': 'Flexibilidad',
        'icono': 'minimize-2',
        'descripcion': 'Flexibilidad de isquiotibiales y zona lumbar.',
        'protocolo': (
            'Sentado, piernas estiradas y pies contra el cajón. Empuja la regla '
            'hacia delante despacio, sin rebotes, y aguanta 2 segundos. Cero es '
            'la punta del pie: negativo si no llega. Mejor hacerlo caliente, '
            'después de trotar.'),
        'fuente': "ACSM's Guidelines for Exercise Testing and Prescription, 10ª ed.",
        'campos': [
            _campo('distancia', 'Distancia', 'cm', -25, 45, 1, '8.0', MAYOR),
        ],
        'baremos': {
            'distancia': {
                ('general', 'general'):  [16, 9, 2, -5],
                ('adulto', 'general'):   [16, 9, 2, -5],
                ('sub_17', 'general'):   [18, 11, 4, -3],
                ('sub_15', 'general'):   [20, 13, 6, -1],
            },
        },
    },

    'abdominales_30s': {
        'nombre': 'Abdominales en 30 segundos',
        'categoria': 'fisico',
        'subcategoria': 'Fuerza resistencia',
        'icono': 'activity',
        'descripcion': 'Resistencia de la musculatura del tronco.',
        'protocolo': (
            'Tumbado, rodillas a 90°, manos en las sienes y pies sujetos. Sube '
            'hasta tocar las rodillas con los codos y baja hasta apoyar la espalda. '
            'Se cuentan las repeticiones completas en 30 s.'),
        'fuente': 'EUROFIT, Council of Europe (1993)',
        'campos': [
            _campo('repeticiones', 'Repeticiones', '', 0, 60, 0, '28', MAYOR),
        ],
        'baremos': {
            'repeticiones': {
                ('general', 'general'):  [30, 26, 22, 18],
                ('sub_17', 'general'):   [29, 25, 21, 17],
                ('sub_15', 'general'):   [26, 22, 19, 15],
                ('sub_14', 'general'):   [23, 20, 17, 13],
            },
        },
    },

    'plancha': {
        'nombre': 'Plancha isométrica',
        'categoria': 'fisico',
        'subcategoria': 'Fuerza resistencia',
        'icono': 'minus',
        'descripcion': 'Estabilidad del núcleo, clave para prevenir lesiones.',
        'protocolo': (
            'Apoyo en antebrazos y puntas de los pies, cuerpo en línea recta. Se '
            'cronometra hasta que la cadera cae o se levanta. Se corta a los 4 '
            'minutos: más allá deja de medir el núcleo y mide la tolerancia.'),
        'fuente': 'McGill SM (2007), Low Back Disorders, 2ª ed.',
        'campos': [
            _campo('tiempo', 'Tiempo aguantado', 's', 0, 300, 0, '95', MAYOR),
        ],
        'baremos': {
            'tiempo': {
                ('general', 'general'):  [150, 110, 75, 45],
                ('sub_15', 'general'):   [120, 90, 60, 35],
            },
        },
    },

    # ───────────────────────── ANTROPOMETRÍA ───────────────────────────────
    'antropometria': {
        'nombre': 'Perfil antropométrico',
        'categoria': 'antropometria',
        'subcategoria': 'Composición corporal',
        'icono': 'user',
        'descripcion': 'Talla, peso y grasa corporal para seguir el crecimiento.',
        'protocolo': (
            'Talla descalzo con el occipital, la espalda y los talones en la pared. '
            'Peso en ropa ligera y en ayunas si se puede. El porcentaje de grasa, '
            'con plicómetro (fórmula de Faulkner, 4 pliegues) o bioimpedancia; '
            'anota siempre con cuál, porque no son intercambiables. En categorías '
            'formativas esto no evalúa: sirve para vigilar el estirón.'),
        'fuente': 'Reilly, Bangsbo & Franks (2000); Faulkner JA (1968)',
        'formula': 'IMC = peso (kg) / talla (m)²',
        'campos': [
            _campo('estatura', 'Estatura', 'cm', 110, 215, 1, '176.0', MAYOR, principal=False),
            _campo('peso', 'Peso', 'kg', 25, 130, 1, '70.5', MAYOR, principal=False),
            _campo('grasa', 'Grasa corporal', '%', 3, 40, 1, '11.5', MENOR),
        ],
        'baremos': {
            'grasa': {
                ('general', 'elite'):       [8.5, 10.5, 12.5, 15.0],
                ('general', 'profesional'): [9.0, 11.0, 13.0, 15.5],
                ('general', 'amateur'):     [10.0, 12.5, 15.0, 18.0],
                ('sub_17', 'general'):      [9.5, 11.5, 13.5, 16.0],
                ('sub_15', 'general'):      [10.5, 12.5, 15.0, 17.5],
                ('general', 'general'):     [9.5, 11.5, 13.5, 16.0],
            },
        },
    },

    # ──────────────────────────── TÉCNICA ──────────────────────────────────
    'lspt': {
        'nombre': 'Loughborough Soccer Passing Test',
        'categoria': 'tecnico',
        'subcategoria': 'Pase',
        'icono': 'target',
        'descripcion': 'El test de pase con más respaldo científico que existe.',
        'protocolo': (
            'Cuadrado de 12 × 9,5 m con cuatro bancos de colores alrededor, cada '
            'uno con una diana de 60 cm. Se hacen 16 pases (4 a cada color) '
            'siguiendo el color que canta el evaluador, saliendo siempre del área '
            'central. Al tiempo bruto se le suman penalizaciones: +5 s por fallar '
            'el banco, +3 s por dar fuera de la diana, +3 s por salirse del área, '
            '+2 s por tocar de más y −1 s por dar en la diana.'),
        'fuente': 'Ali A et al. (2007), J Sports Sci 25(13):1461-1470',
        'formula': 'Tiempo final = tiempo bruto + penalizaciones − bonificaciones',
        'campos': [
            _campo('tiempo_final', 'Tiempo final', 's', 25, 140, 1, '52.0', MENOR),
            _campo('tiempo_bruto', 'Tiempo bruto', 's', 20, 130, 1, '45.0',
                   MENOR, principal=False),
            _campo('penalizacion', 'Penalización', 's', 0, 90, 0, '7',
                   MENOR, principal=False),
        ],
        'baremos': {
            'tiempo_final': {
                ('general', 'elite'):       [44, 50, 57, 66],
                ('general', 'profesional'): [47, 53, 60, 70],
                ('general', 'amateur'):     [55, 62, 70, 82],
                ('sub_17', 'general'):      [52, 59, 67, 78],
                ('sub_15', 'general'):      [58, 66, 75, 87],
                ('general', 'general'):     [48, 55, 63, 73],
            },
        },
    },

    'pase_precision': {
        'nombre': 'Precisión de pase (10 intentos)',
        'categoria': 'tecnico',
        'subcategoria': 'Pase',
        'icono': 'target',
        'descripcion': 'Diez pases a portería pequeña desde 20 m.',
        'protocolo': (
            'Portería de 1 m de ancho a 20 metros. Diez pases con el interior, '
            'balón parado, alternando pierna cada cinco. Se cuentan los que entran '
            'sin tocar los postes.'),
        'fuente': 'Adaptado de Mor D & Christian V (1979), Mor-Christian GSAT',
        'campos': [
            _campo('aciertos', 'Pases acertados', '/10', 0, 10, 0, '7', MAYOR),
        ],
        'baremos': {
            'aciertos': {
                ('general', 'elite'):       [9, 8, 6, 4],
                ('general', 'profesional'): [8, 7, 6, 4],
                ('general', 'amateur'):     [7, 6, 4, 3],
                ('sub_15', 'general'):      [7, 5, 4, 2],
                ('general', 'general'):     [8, 7, 5, 3],
            },
        },
    },

    'conduccion_slalom': {
        'nombre': 'Conducción en slalom',
        'categoria': 'tecnico',
        'subcategoria': 'Conducción',
        'icono': 'wind',
        'descripcion': 'Control del balón a velocidad entre conos.',
        'protocolo': (
            'Ocho conos en línea separados 1,5 m, con 3 m desde la salida hasta el '
            'primero. Se conduce en zig-zag hasta el final y se vuelve. Cada cono '
            'derribado o saltado suma 2 s. Dos intentos, se anota el mejor.'),
        'fuente': 'Adaptado de Mor-Christian General Soccer Ability Test (1979)',
        'campos': [
            _campo('tiempo', 'Tiempo', 's', 8, 40, 2, '14.50', MENOR),
            _campo('errores', 'Conos derribados', '', 0, 16, 0, '1',
                   MENOR, principal=False),
        ],
        'baremos': {
            'tiempo': {
                ('general', 'elite'):       [13.0, 14.2, 15.6, 17.4],
                ('general', 'profesional'): [13.6, 14.8, 16.2, 18.0],
                ('general', 'amateur'):     [15.0, 16.4, 18.0, 20.0],
                ('sub_17', 'general'):      [14.4, 15.7, 17.2, 19.1],
                ('sub_15', 'general'):      [15.6, 17.0, 18.6, 20.7],
                ('general', 'general'):     [13.8, 15.1, 16.6, 18.4],
            },
        },
    },

    'remate_precision': {
        'nombre': 'Precisión de remate',
        'categoria': 'tecnico',
        'subcategoria': 'Remate',
        'icono': 'crosshair',
        'descripcion': 'Diez remates puntuados por zona de portería.',
        'protocolo': (
            'Portería reglamentaria dividida en zonas: escuadras 4 puntos, bajo los '
            'palos 3, resto del marco 1. Diez remates desde el borde del área, '
            'cinco con cada pierna, balón parado. Máximo 40 puntos.'),
        'fuente': 'Adaptado de Rösch D et al. (2000), Am J Sports Med 28(5 suppl)',
        'campos': [
            _campo('puntos', 'Puntos', 'pts', 0, 40, 0, '22', MAYOR),
            _campo('goles', 'Remates a puerta', '/10', 0, 10, 0, '8',
                   MAYOR, principal=False),
        ],
        'baremos': {
            'puntos': {
                ('general', 'elite'):       [30, 25, 19, 13],
                ('general', 'profesional'): [27, 22, 17, 11],
                ('general', 'amateur'):     [22, 18, 13, 8],
                ('sub_17', 'general'):      [24, 19, 14, 9],
                ('sub_15', 'general'):      [20, 16, 11, 7],
                ('general', 'general'):     [26, 21, 16, 10],
            },
        },
    },

    'juegos_malabares': {
        'nombre': 'Toques de balón (dominadas)',
        'categoria': 'tecnico',
        'subcategoria': 'Control',
        'icono': 'circle',
        'descripcion': 'Sensibilidad y control del balón en el aire.',
        'protocolo': (
            'Toques seguidos sin que el balón caiga, alternando pie derecho, pie '
            'izquierdo y muslo. No valen dos toques seguidos con la misma '
            'superficie. Dos intentos, se anota el mejor. Es la prueba favorita de '
            'los chicos y sirve para engancharlos a entrenar por su cuenta.'),
        'fuente': 'Uso extendido en formación; sin baremo publicado con muestra amplia',
        'campos': [
            _campo('toques', 'Toques alternados', '', 0, 500, 0, '45', MAYOR),
        ],
        'baremos': {
            'toques': {
                ('general', 'general'):  [80, 45, 22, 10],
                ('sub_15', 'general'):   [60, 35, 18, 8],
                ('sub_12', 'general'):   [40, 22, 12, 5],
            },
        },
    },

    'control_orientado': {
        'nombre': 'Control orientado',
        'categoria': 'tecnico',
        'subcategoria': 'Control',
        'icono': 'rotate-cw',
        'descripcion': 'Recibir y salir jugando al primer toque.',
        'protocolo': (
            'Un pasador envía el balón desde 15 m; el jugador controla y sale hacia '
            'el cono que se le cante en el momento de la recepción. Diez '
            'repeticiones. El entrenador puntúa de 1 a 10 el conjunto: primer toque, '
            'orientación del cuerpo y velocidad de salida.'),
        'fuente': 'Valoración observacional del cuerpo técnico',
        'campos': [
            _nota('nota', 'Nota del entrenador', '7'),
        ],
        'baremos': {
            'nota': {('general', 'general'): [9, 7, 6, 4]},
        },
    },

    'regate_1v1': {
        'nombre': 'Regate en 1 contra 1',
        'categoria': 'tecnico',
        'subcategoria': 'Regate',
        'icono': 'user-x',
        'descripcion': 'Capacidad de superar al defensor en corto.',
        'protocolo': (
            'Cinco situaciones de 1v1 en un pasillo de 10 × 15 m contra un defensor '
            'activo, con el objetivo de cruzar la línea de fondo con el balón '
            'controlado. Se cuentan los ganados y se pone una nota de 1 a 10.'),
        'fuente': 'Valoración observacional del cuerpo técnico',
        'campos': [
            _campo('ganados', '1v1 ganados', '/5', 0, 5, 0, '3', MAYOR),
            _nota('nota', 'Nota del entrenador', '7', principal=False),
        ],
        'baremos': {
            'ganados': {('general', 'general'): [4, 3, 2, 1]},
            'nota':    {('general', 'general'): [9, 7, 6, 4]},
        },
    },

    'golpeo_largo': {
        'nombre': 'Golpeo de larga distancia',
        'categoria': 'tecnico',
        'subcategoria': 'Pase',
        'icono': 'send',
        'descripcion': 'Alcance y precisión en el cambio de orientación.',
        'protocolo': (
            'Cinco golpeos desde parado a un círculo de 5 m de radio situado a 40 m. '
            'Se cuentan los que caen dentro y se anota la distancia máxima alcanzada '
            'en un golpeo libre.'),
        'fuente': 'Valoración observacional del cuerpo técnico',
        'campos': [
            _campo('aciertos', 'Golpeos al círculo', '/5', 0, 5, 0, '3', MAYOR),
            _campo('distancia', 'Distancia máxima', 'm', 15, 90, 0, '52',
                   MAYOR, principal=False),
        ],
        'baremos': {
            'aciertos': {('general', 'general'): [4, 3, 2, 1]},
            'distancia': {
                ('general', 'profesional'): [65, 57, 50, 42],
                ('sub_17', 'general'):      [58, 51, 44, 37],
                ('sub_15', 'general'):      [50, 44, 38, 31],
                ('general', 'general'):     [60, 53, 46, 39],
            },
        },
    },

    # ──────────────────────────── TÁCTICA ──────────────────────────────────
    'perfil_tactico': {
        'nombre': 'Perfil táctico (6 dimensiones)',
        'categoria': 'tactico',
        'subcategoria': 'Lectura de juego',
        'icono': 'map',
        'descripcion': 'Lo que el entrenador ve en el partido, puesto en números.',
        'protocolo': (
            'Se rellena después de observar al jugador en dos o tres partidos, no '
            'en un entrenamiento suelto. Cada dimensión de 1 a 10. Conviene que lo '
            'hagan dos miembros del cuerpo técnico por separado y comparar: si '
            'hay más de 2 puntos de diferencia, hablarlo antes de anotar.'),
        'fuente': 'Adaptado de Kannekens R et al. (2011), Scand J Med Sci Sports',
        'campos': [
            _nota('posicionamiento', 'Posicionamiento sin balón'),
            _nota('toma_decision', 'Toma de decisión', principal=False),
            _nota('lectura', 'Lectura del juego', principal=False),
            _nota('presion', 'Presión y basculación', principal=False),
            _nota('transiciones', 'Transiciones', principal=False),
            _nota('juego_colectivo', 'Juego colectivo', principal=False),
        ],
        'baremos': {c: {('general', 'general'): [9, 7, 6, 4]}
                    for c in ('posicionamiento', 'toma_decision', 'lectura',
                              'presion', 'transiciones', 'juego_colectivo')},
    },

    # ──────────────────────────── MENTAL ───────────────────────────────────
    'perfil_mental': {
        'nombre': 'Perfil mental (5 dimensiones)',
        'categoria': 'mental',
        'subcategoria': 'Observación',
        'icono': 'eye',
        'descripcion': 'Aspectos psicológicos observados por el cuerpo técnico.',
        'protocolo': (
            'Lo rellena el entrenador desde lo que ve, no el jugador. NO es un '
            'diagnóstico clínico ni sustituye al psicólogo deportivo: si algo '
            'preocupa, se deriva. El check-in de bienestar del jugador es otra cosa '
            'y sus respuestas son confidenciales.'),
        'fuente': 'Adaptado de Gucciardi DF et al. (2015), J Pers 83(1):26-44',
        'campos': [
            _nota('concentracion', 'Concentración'),
            _nota('confianza', 'Confianza', principal=False),
            _nota('presion', 'Manejo de la presión', principal=False),
            _nota('disciplina', 'Disciplina y compromiso', principal=False),
            _nota('liderazgo', 'Liderazgo', principal=False),
        ],
        'baremos': {c: {('general', 'general'): [9, 7, 6, 4]}
                    for c in ('concentracion', 'confianza', 'presion',
                              'disciplina', 'liderazgo')},
    },

    'reaccion': {
        'nombre': 'Tiempo de reacción',
        'categoria': 'mental',
        'subcategoria': 'Atención',
        'icono': 'zap',
        'descripcion': 'Velocidad de respuesta a un estímulo visual.',
        'protocolo': (
            'Prueba de la regla: el evaluador sujeta una regla de 30 cm en '
            'vertical entre los dedos del jugador y la suelta sin avisar. Se anota '
            'a cuántos centímetros la atrapa. Tres intentos, se promedia. '
            'También sirve cualquier app de tiempo de reacción, anotando ms.'),
        'fuente': 'Del Rossi G et al. (2014), J Athl Train 49(2):189-193',
        'campos': [
            _campo('centimetros', 'Centímetros de caída', 'cm', 3, 30, 1, '14.0', MENOR),
        ],
        'baremos': {
            'centimetros': {
                ('general', 'general'): [11.0, 14.0, 18.0, 23.0],
            },
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  CONSULTA
# ═══════════════════════════════════════════════════════════════════════════
CATEGORIAS = [
    ('fisico',        'Físicas',        '🏃', 'Resistencia, velocidad, potencia y agilidad'),
    ('tecnico',       'Técnicas',       '⚽', 'Pase, control, conducción y remate'),
    ('tactico',       'Tácticas',       '🧠', 'Lectura de juego y posicionamiento'),
    ('mental',        'Mentales',       '💚', 'Concentración, confianza y presión'),
    ('antropometria', 'Antropometría',  '📏', 'Talla, peso y composición corporal'),
]

CATEGORIA_META = {c: {'etiqueta': e, 'emoji': em, 'descripcion': d}
                  for c, e, em, d in CATEGORIAS}


def test(clave):
    """Devuelve la prueba del catálogo, o None si la clave no existe."""
    t = CATALOGO.get(clave)
    if not t:
        return None
    return dict(t, clave=clave)


def tests_por_categoria(categoria=None):
    salida = []
    for clave, t in CATALOGO.items():
        if categoria and t['categoria'] != categoria:
            continue
        salida.append(dict(t, clave=clave))
    return sorted(salida, key=lambda t: (t['categoria'], t.get('subcategoria', ''), t['nombre']))


def campo_principal(t):
    """El campo que manda al puntuar y al ordenar el ranking."""
    for c in t.get('campos', []):
        if c.get('principal'):
            return c
    return (t.get('campos') or [None])[0]


def baremo_para(clave_test, campo, categoria_edad='general', nivel='general'):
    """Busca el baremo más específico que exista, cayendo hacia atrás.

    Orden de búsqueda:
      1. (edad exacta, nivel exacto)
      2. (edad exacta, general)
      3. (general, nivel exacto)
      4. (general, general)
    Si no hay ninguno devuelve None y el resultado se guarda sin nivel: es
    preferible no clasificar a clasificar contra un listón que no corresponde.
    """
    t = CATALOGO.get(clave_test)
    if not t:
        return None
    tabla = (t.get('baremos') or {}).get(campo)
    if not tabla:
        return None
    for par in ((categoria_edad, nivel), (categoria_edad, 'general'),
                ('general', nivel), ('general', 'general')):
        if par in tabla:
            cortes = tabla[par]
            return {'cortes': cortes, 'edad': par[0], 'nivel': par[1],
                    'fuente': t.get('fuente', '')}
    return None


def direccion_de(clave_test, campo):
    t = CATALOGO.get(clave_test) or {}
    for c in t.get('campos', []):
        if c['clave'] == campo:
            return c.get('direccion', MAYOR)
    return MAYOR


def clasificar(valor, cortes, direccion):
    """Sitúa un valor entre los cuatro cortes del baremo.

    `cortes` va SIEMPRE de mejor a peor: [élite, bueno, promedio, débil].
    Con 'menor_mejor' (tiempos) la comparación se invierte, porque 4,02 s es
    mejor que 4,14 s.
    """
    if valor is None or not cortes or len(cortes) < 4:
        return None
    e, b, p, d = cortes[:4]
    if direccion == MENOR:
        if valor <= e:
            return 'elite'
        if valor <= b:
            return 'bueno'
        if valor <= p:
            return 'promedio'
        if valor <= d:
            return 'debil'
        return 'muy_debil'
    if valor >= e:
        return 'elite'
    if valor >= b:
        return 'bueno'
    if valor >= p:
        return 'promedio'
    if valor >= d:
        return 'debil'
    return 'muy_debil'


def puntaje_de(valor, cortes, direccion):
    """Convierte el valor a una escala 0-100 comparable entre pruebas distintas.

    Se interpola dentro del tramo en el que cae, para que dos jugadores del
    mismo nivel no empaten y para que una mejora pequeña se note en la gráfica
    aunque no cambie de nivel.
    """
    if valor is None or not cortes or len(cortes) < 4:
        return None
    e, b, p, d = [float(x) for x in cortes[:4]]
    valor = float(valor)
    # Se trabaja siempre "mayor es mejor": con tiempos se invierte el signo.
    if direccion == MENOR:
        valor, e, b, p, d = -valor, -e, -b, -p, -d

    tramos = [(e, 95, 100), (b, 78, 95), (p, 58, 78), (d, 38, 58)]
    if valor >= e:
        # Por encima de élite: de 95 a 100, saturando a una distancia de medio tramo.
        margen = max(abs(e - b), 1e-6)
        return int(min(100, 95 + 5 * min(1.0, (valor - e) / margen)))
    anterior = e
    for i, (corte, base, techo) in enumerate(tramos[1:], start=1):
        if valor >= corte:
            rango = max(anterior - corte, 1e-6)
            return int(round(base + (techo - base) * (valor - corte) / rango))
        anterior = corte
    # Por debajo de "débil": de 0 a 38.
    margen = max(abs(p - d), 1e-6)
    return int(max(0, round(38 * max(0.0, 1 - (d - valor) / margen))))


def evaluar_valor(clave_test, campo, valor, categoria_edad='general', nivel='general'):
    """Nivel + puntaje + baremo usado, todo de una."""
    baremo = baremo_para(clave_test, campo, categoria_edad, nivel)
    if not baremo:
        return {'nivel': None, 'puntaje': None, 'baremo': None}
    direccion = direccion_de(clave_test, campo)
    nivel_r = clasificar(valor, baremo['cortes'], direccion)
    return {
        'nivel': nivel_r,
        'puntaje': puntaje_de(valor, baremo['cortes'], direccion),
        'baremo': baremo,
        'direccion': direccion,
        'meta': NIVEL_META.get(nivel_r or ''),
    }


def resumen_baremo(clave_test, campo, categoria_edad='general', nivel='general'):
    """Texto tipo «Élite ≤ 4,02 s · Bueno ≤ 4,14 s · …» para enseñar el listón."""
    baremo = baremo_para(clave_test, campo, categoria_edad, nivel)
    if not baremo:
        return ''
    t = CATALOGO.get(clave_test) or {}
    unidad = next((c.get('unidad', '') for c in t.get('campos', [])
                   if c['clave'] == campo), '')
    signo = '≤' if direccion_de(clave_test, campo) == MENOR else '≥'
    etiquetas = ['Élite', 'Bueno', 'Promedio', 'A mejorar']
    partes = []
    for etq, corte in zip(etiquetas, baremo['cortes']):
        num = f'{corte:g}'
        partes.append(f'{etq} {signo} {num}{(" " + unidad) if unidad else ""}')
    return ' · '.join(partes)


def categoria_por_edad(anio_nacimiento, hoy=None):
    """Traduce el año de nacimiento a la categoría con la que se compara."""
    if not anio_nacimiento:
        return 'general'
    from datetime import date
    año = (hoy or date.today()).year
    try:
        edad = año - int(anio_nacimiento)
    except (TypeError, ValueError):
        return 'general'
    if edad >= 20:
        return 'adulto'
    if edad >= 19:
        return 'sub_20'
    # El más ajustado que le quede grande: un chico de 15 se compara en sub-15.
    for tope in (10, 12, 14, 15, 16, 17, 18):
        if edad <= tope:
            return f'sub_{tope}'
    return 'sub_20'


def nivel_sugerido(categoria_edad):
    """Nivel competitivo por defecto cuando el entrenador aún no lo configuró."""
    return {
        'sub_10': 'escuela', 'sub_12': 'escuela',
        'sub_14': 'formativo', 'sub_15': 'formativo', 'sub_16': 'formativo',
        'sub_17': 'juvenil', 'sub_18': 'juvenil', 'sub_20': 'juvenil',
    }.get(categoria_edad, 'amateur')
