# -*- coding: utf-8 -*-
"""
futbol/tests_catalogo.py — Las pruebas del catálogo y sus baremos.

QUÉ SE CONSERVA DEL MVP Y QUÉ SE AÑADE
──────────────────────────────────────
Las 14 primeras pruebas son EXACTAMENTE las de la app original
(polansols/FutbolApp, sql/evaluation_system_safe.sql): mismo nombre, misma
descripción, mismas instrucciones, mismas claves de campo, mismas unidades,
mismos rangos y mismo orden. Quien venía de la app no debe notar ni una
palabra distinta — el usuario ya sabe cómo se toma cada prueba y cambiarle el
texto le obliga a releerlo todo.

Lo que se mejora es la BASE, que antes no existía: cada marca se compara con
un baremo publicado, estratificado por categoría de edad × nivel competitivo,
y sale con su nivel (élite/bueno/promedio/a mejorar/bajo) y un puntaje 0-100
comparable entre pruebas. En la app original la tabla `test_reference_ranges`
que consultaba `utils/referenceRanges.ts` no llegó a existir, así que los
números se guardaban sin interpretar.

Debajo de las 14 hay pruebas ADICIONALES, en las mismas tres familias del MVP
(físico, técnico, mental) para no cambiar la estructura de la pantalla.

Por qué los baremos viven en el código y no en la base
──────────────────────────────────────────────────────
Un baremo publicado es una constante, no un dato del cliente. Sembrarlo
obligaría a repetir la siembra en cada entorno y a vigilar que no se
desincronicen; aquí se lee igual en local, en Vercel y en el VPS.

Fuentes de los cortes
─────────────────────
  · Cooper KH (1968) JAMA — test de 12 minutos.
  · Bangsbo J, Iaia FM, Krustrup P (2008) Sports Med — Yo-Yo IR1/IR2.
  · Krustrup P et al. (2003) Med Sci Sports Exerc — Yo-Yo IR1 en élite.
  · Haugen T, Tønnessen E, Seiler S (2013) IJSPP — velocidad y CMJ por nivel.
  · Rampinini E et al. (2007) Int J Sports Med — sprints repetidos.
  · Getchell B (1979) — Illinois Agility Test.
  · Semenick D (1990) NSCA — T-Test.
  · Léger L et al. (1988) J Sports Sci — course navette 20 m.
  · Ali A et al. (2007) J Sports Sci — Loughborough Soccer Passing Test.
  · ACSM's Guidelines (10ª ed.) — sit and reach y composición corporal.
  · Council of Europe (1993) EUROFIT — salto horizontal y abdominales.
  · Reilly T, Bangsbo J, Franks A (2000) J Sports Sci — perfil antropométrico.
  · Bosco C, Luhtanen P, Komi PV (1983) Eur J Appl Physiol — salto sin
    contramovimiento.
  · Draper JA & Lancaster MG (1985) Aust J Sci Med Sport — test 505.
  · Mor D & Christian V (1979) — Mor-Christian General Soccer Ability Test.
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
    """Campo de valoración del entrenador, 1 a 10 (el `rating` del MVP)."""
    return _campo(clave, etiqueta, '/10', 1, 10, 0, ejemplo,
                  MAYOR, principal, tipo='nota')


# ═══════════════════════════════════════════════════════════════════════════
#  BLOQUE A — LAS 14 PRUEBAS DEL MVP, SIN TOCAR
# ═══════════════════════════════════════════════════════════════════════════
#  Nombre, descripción, instrucciones, claves de campo, etiquetas, unidades,
#  rangos, decimales, ejemplos, icono y orden: copiados literalmente de
#  sql/evaluation_system_safe.sql. Lo único añadido es `baremos` y `fuente`.
# ═══════════════════════════════════════════════════════════════════════════

_MVP = {

    'sprint_30m': {
        'nombre': 'Sprint 30m',
        'categoria': 'fisico',
        'orden': 10,
        'icono': 'zap',
        'descripcion': 'Test de velocidad pura en 30 metros',
        'protocolo': ('Marca dos conos separados 30 metros. El jugador sale de '
                      'parado y corre al máximo hasta el segundo cono.'),
        'fuente': 'Haugen, Tønnessen & Seiler (2013), IJSPP 8(2):148-156',
        'campos': [
            _campo('time_seconds', 'Tiempo', 's', 3, 10, 2, '4.32', MENOR),
        ],
        'baremos': {
            'time_seconds': {
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

    'sprint_10m': {
        'nombre': 'Sprint 10m',
        'categoria': 'fisico',
        'orden': 11,
        'icono': 'zap',
        'descripcion': 'Test de aceleración pura en 10 metros',
        'protocolo': ('Mide la capacidad de arranque. Sale parado, cronómetro '
                      'al primer paso.'),
        'fuente': 'Haugen, Tønnessen & Seiler (2013), IJSPP 8(2):148-156',
        'campos': [
            _campo('time_seconds', 'Tiempo', 's', 1, 5, 2, '1.85', MENOR),
        ],
        'baremos': {
            'time_seconds': {
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

    'cooper': {
        'nombre': 'Test Cooper (12 min)',
        'categoria': 'fisico',
        'orden': 20,
        'icono': 'activity',
        'descripcion': 'Resistencia aeróbica — máxima distancia en 12 minutos',
        'protocolo': ('El jugador corre 12 minutos en una pista marcada. Anota '
                      'los metros totales.'),
        'fuente': 'Cooper KH (1968), JAMA 203(3):201-204',
        'formula': 'VO₂máx ≈ (metros − 504,9) / 44,73',
        'campos': [
            _campo('distance_meters', 'Distancia', 'm', 1000, 4500, 0, '2800', MAYOR),
        ],
        'baremos': {
            'distance_meters': {
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
        'nombre': 'Yo-Yo Intermittent Recovery',
        'categoria': 'fisico',
        'orden': 21,
        'icono': 'activity',
        'descripcion': 'Resistencia con recuperación incompleta — específico de fútbol',
        'protocolo': 'Carreras de 20m ida y vuelta con 10s de descanso entre series.',
        'fuente': 'Bangsbo, Iaia & Krustrup (2008), Sports Med 38(1):37-51',
        'formula': 'VO₂máx ≈ distancia (m) × 0,0084 + 36,4',
        # El orden de los campos es el del MVP (nivel y luego distancia); la
        # DISTANCIA es la principal porque es la medida con la que trabaja la
        # literatura, pero eso solo afecta al ranking, no a lo que se ve.
        'campos': [
            _campo('level', 'Nivel alcanzado', '', 1, 23, 1, '17.5', MAYOR,
                   principal=False),
            _campo('total_distance', 'Distancia total', 'm', 0, 3000, 0, '1240', MAYOR),
        ],
        'baremos': {
            'total_distance': {
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

    'cmj': {
        'nombre': 'Salto Vertical (CMJ)',
        'categoria': 'fisico',
        'orden': 30,
        'icono': 'trending-up',
        'descripcion': 'Potencia de tren inferior — counter-movement jump',
        'protocolo': ('El jugador se agacha y salta verticalmente con brazos '
                      'libres. Mide la altura del salto.'),
        'fuente': 'Haugen, Tønnessen & Seiler (2013), IJSPP 8(2):148-156',
        'campos': [
            _campo('height_cm', 'Altura', 'cm', 20, 80, 1, '42.5', MAYOR),
        ],
        'baremos': {
            'height_cm': {
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

    'rsa': {
        'nombre': 'Sprint Repetido (RSA)',
        'categoria': 'fisico',
        'orden': 31,
        'icono': 'repeat',
        'descripcion': 'Capacidad de repetir sprints — 6x30m con 20s recuperación',
        'protocolo': ('Mide la fatiga acumulada. Promedio de los 6 sprints y el '
                      'peor tiempo.'),
        'fuente': 'Rampinini E et al. (2007), Int J Sports Med 28(3):228-235',
        'formula': 'Índice de fatiga = (peor − mejor) / mejor × 100',
        'campos': [
            _campo('avg_time', 'Tiempo promedio', 's', 3, 10, 2, '4.42', MENOR),
            _campo('worst_time', 'Peor tiempo', 's', 3, 10, 2, '4.78', MENOR,
                   principal=False),
        ],
        'baremos': {
            'avg_time': {
                ('general', 'elite'):       [4.20, 4.33, 4.47, 4.65],
                ('general', 'profesional'): [4.29, 4.42, 4.56, 4.74],
                ('general', 'amateur'):     [4.50, 4.64, 4.79, 4.99],
                ('sub_17', 'general'):      [4.42, 4.55, 4.69, 4.88],
                ('sub_15', 'general'):      [4.63, 4.77, 4.92, 5.12],
                ('general', 'general'):     [4.32, 4.45, 4.59, 4.78],
            },
        },
    },

    'sit_and_reach': {
        'nombre': 'Flexibilidad (Sit and Reach)',
        'categoria': 'fisico',
        'orden': 40,
        'icono': 'minimize-2',
        'descripcion': 'Flexibilidad de cadena posterior',
        'protocolo': ('Sentado con piernas extendidas, empuja una regla hacia '
                      'adelante. Negativo si no llega al pie.'),
        'fuente': "ACSM's Guidelines for Exercise Testing and Prescription, 10ª ed.",
        'campos': [
            _campo('distance_cm', 'Distancia', 'cm', -20, 40, 1, '12.0', MAYOR),
        ],
        'baremos': {
            'distance_cm': {
                ('general', 'general'):  [16, 9, 2, -5],
                ('adulto', 'general'):   [16, 9, 2, -5],
                ('sub_17', 'general'):   [18, 11, 4, -3],
                ('sub_15', 'general'):   [20, 13, 6, -1],
            },
        },
    },

    'pase_precision': {
        'nombre': 'Precisión de Pase',
        'categoria': 'tecnico',
        'orden': 50,
        'icono': 'target',
        'descripcion': '10 pases a un objetivo a 20m — cuenta los acertados',
        'protocolo': ('El jugador hace 10 pases con borde interno a una portería '
                      'pequeña a 20m.'),
        'fuente': 'Adaptado de Mor D & Christian V (1979), Mor-Christian GSAT',
        'campos': [
            _campo('successful', 'Pases acertados', '/10', 0, 10, 0, '7', MAYOR),
        ],
        'baremos': {
            'successful': {
                ('general', 'elite'):       [9, 8, 6, 4],
                ('general', 'profesional'): [8, 7, 6, 4],
                ('general', 'amateur'):     [7, 6, 4, 3],
                ('sub_15', 'general'):      [7, 5, 4, 2],
                ('general', 'general'):     [8, 7, 5, 3],
            },
        },
    },

    'conduccion_conos': {
        'nombre': 'Conducción con Conos',
        'categoria': 'tecnico',
        'orden': 60,
        'icono': 'wind',
        'descripcion': 'Slalom entre 8 conos en zig-zag — mide tiempo',
        'protocolo': ('Marca 8 conos en línea separados 1.5m. Conduce el balón en '
                      'zig-zag, vuelta completa.'),
        'fuente': 'Adaptado de Mor-Christian General Soccer Ability Test (1979)',
        'campos': [
            _campo('time_seconds', 'Tiempo', 's', 5, 30, 2, '12.50', MENOR),
            _campo('errors', 'Errores (toques fuera)', '', 0, 10, 0, '1', MENOR,
                   principal=False),
        ],
        'baremos': {
            'time_seconds': {
                ('general', 'elite'):       [13.0, 14.2, 15.6, 17.4],
                ('general', 'profesional'): [13.6, 14.8, 16.2, 18.0],
                ('general', 'amateur'):     [15.0, 16.4, 18.0, 20.0],
                ('sub_17', 'general'):      [14.4, 15.7, 17.2, 19.1],
                ('sub_15', 'general'):      [15.6, 17.0, 18.6, 20.7],
                ('general', 'general'):     [13.8, 15.1, 16.6, 18.4],
            },
        },
    },

    'tiros_porteria': {
        'nombre': 'Tiros a Portería',
        'categoria': 'tecnico',
        'orden': 61,
        'icono': 'target',
        'descripcion': 'Puntuación por zonas — 5 tiros desde frontal del área',
        'protocolo': ('Divide la portería en zonas (esquinas 3pts, palos 2pts, '
                      'centro 1pt). Suma 5 tiros.'),
        'fuente': 'Adaptado de Rösch D et al. (2000), Am J Sports Med 28(5 suppl)',
        'campos': [
            _campo('score', 'Puntos totales', 'pts', 0, 15, 0, '8', MAYOR),
            _campo('goals', 'Goles', '', 0, 5, 0, '3', MAYOR, principal=False),
        ],
        'baremos': {
            'score': {
                ('general', 'elite'):       [12, 10, 7, 5],
                ('general', 'profesional'): [11, 9, 6, 4],
                ('general', 'amateur'):     [9, 7, 5, 3],
                ('sub_17', 'general'):      [10, 8, 5, 3],
                ('sub_15', 'general'):      [8, 6, 4, 2],
                ('general', 'general'):     [11, 9, 6, 4],
            },
        },
    },

    'control_orientado': {
        'nombre': 'Control Orientado',
        'categoria': 'tecnico',
        'orden': 62,
        'icono': 'rotate-cw',
        'descripcion': 'Recepción y giro evaluado por escala 1-10',
        'protocolo': ('Pasador envía balón al jugador, controla y gira hacia un '
                      'cono específico.'),
        'fuente': 'Valoración observacional del cuerpo técnico',
        'campos': [
            _nota('rating', 'Nota', '7'),
        ],
        'baremos': {'rating': {('general', 'general'): [9, 7, 6, 4]}},
    },

    'regate_1v1': {
        'nombre': 'Regate 1v1',
        'categoria': 'tecnico',
        'orden': 63,
        'icono': 'user-x',
        'descripcion': 'Capacidad de superar al defensor — escala 1-10',
        'protocolo': '5 situaciones de 1v1 contra un defensor pasivo o activo.',
        'fuente': 'Valoración observacional del cuerpo técnico',
        'campos': [
            _nota('rating', 'Nota', '7'),
            _campo('successful', '1v1 ganados', '/5', 0, 5, 0, '3', MAYOR,
                   principal=False),
        ],
        'baremos': {
            'rating':     {('general', 'general'): [9, 7, 6, 4]},
            'successful': {('general', 'general'): [4, 3, 2, 1]},
        },
    },

    'perfil_mental': {
        'nombre': 'Perfil Mental (5 dimensiones)',
        'categoria': 'mental',
        'orden': 70,
        'icono': 'eye',
        'descripcion': 'Evaluación observacional de aspectos psicológicos clave',
        'protocolo': 'Basado en la observación del coach. NO es diagnóstico clínico.',
        'fuente': 'Adaptado de Gucciardi DF et al. (2015), J Pers 83(1):26-44',
        'campos': [
            _nota('concentration', 'Concentración'),
            _nota('confidence', 'Confianza', principal=False),
            _nota('pressure_handling', 'Manejo de presión', principal=False),
            _nota('discipline', 'Disciplina', principal=False),
            _nota('leadership', 'Liderazgo', principal=False),
        ],
        'baremos': {c: {('general', 'general'): [9, 7, 6, 4]}
                    for c in ('concentration', 'confidence', 'pressure_handling',
                              'discipline', 'leadership')},
    },

    'checkin_diario': {
        'nombre': 'Check-in Diario',
        'categoria': 'mental',
        'orden': 71,
        'icono': 'sunrise',
        'descripcion': 'Estado del jugador antes del entrenamiento — rápido',
        'protocolo': 'Pregunta breve al jugador al llegar al entreno.',
        'fuente': 'Valoración rápida del cuerpo técnico',
        'campos': [
            _nota('energy', 'Energía', '8'),
            _nota('motivation', 'Motivación', '8', principal=False),
            _nota('sleep_quality', 'Calidad de sueño', '7', principal=False),
        ],
        'baremos': {c: {('general', 'general'): [9, 7, 6, 4]}
                    for c in ('energy', 'motivation', 'sleep_quality')},
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  BLOQUE B — PRUEBAS AÑADIDAS
# ═══════════════════════════════════════════════════════════════════════════
#  Van en las MISMAS tres familias del MVP para no cambiar la estructura de la
#  pantalla, y con un `orden` alto para que aparezcan después de las 14 de
#  siempre. Son opcionales: quien solo use las del MVP no las ve nunca.
# ═══════════════════════════════════════════════════════════════════════════

_EXTRA = {

    # ─── Resistencia ───────────────────────────────────────────────────────
    'course_navette': {
        'nombre': 'Course Navette (20 m)',
        'categoria': 'fisico', 'orden': 120, 'icono': 'activity',
        'descripcion': 'Ida y vuelta de 20 m a ritmo creciente marcado por señales.',
        'protocolo': ('Dos líneas a 20 m. El jugador va y viene siguiendo las '
                      'señales, que se aceleran cada minuto (un palier). Termina '
                      'cuando falla dos veces seguidas. Se anota el palier '
                      'alcanzado con su fracción (ej. 11,5).'),
        'fuente': 'Léger L et al. (1988), J Sports Sci 6(2):93-101',
        'campos': [_campo('palier', 'Palier alcanzado', '', 1, 21, 1, '12.5', MAYOR)],
        'baremos': {'palier': {
            ('general', 'elite'):       [14.0, 13.0, 12.0, 10.5],
            ('general', 'profesional'): [13.5, 12.5, 11.5, 10.0],
            ('general', 'amateur'):     [12.0, 11.0, 10.0, 8.5],
            ('sub_17', 'general'):      [12.5, 11.5, 10.5, 9.0],
            ('sub_15', 'general'):      [11.5, 10.5, 9.5, 8.0],
            ('sub_14', 'general'):      [10.5, 9.5, 8.5, 7.0],
            ('general', 'general'):     [13.0, 12.0, 11.0, 9.5],
        }},
    },

    'vo2max': {
        'nombre': 'VO₂ máximo',
        'categoria': 'fisico', 'orden': 121, 'icono': 'wind',
        'descripcion': 'Consumo máximo de oxígeno, medido o estimado.',
        'protocolo': ('Anota el valor que dé el laboratorio, el pulsómetro o la '
                      'fórmula de Cooper / Yo-Yo. Sirve para seguir la evolución '
                      'aunque cambie la prueba con la que se estimó, siempre que '
                      'se anote de dónde sale.'),
        'fuente': 'Reilly, Bangsbo & Franks (2000), J Sports Sci 18(9):669-683',
        'campos': [_campo('vo2', 'VO₂ máx', 'ml/kg/min', 25, 90, 1, '58.5', MAYOR)],
        'baremos': {'vo2': {
            ('general', 'elite'):       [65, 61, 57, 52],
            ('general', 'profesional'): [62, 58, 54, 49],
            ('general', 'semipro'):     [58, 54, 50, 46],
            ('general', 'amateur'):     [54, 50, 46, 42],
            ('sub_17', 'general'):      [60, 56, 52, 47],
            ('sub_15', 'general'):      [56, 52, 48, 44],
            ('general', 'general'):     [60, 56, 52, 47],
        }},
    },

    # ─── Velocidad y potencia ──────────────────────────────────────────────
    'sprint_20m': {
        'nombre': 'Sprint 20 m',
        'categoria': 'fisico', 'orden': 130, 'icono': 'zap',
        'descripcion': 'Velocidad en la distancia que más se repite en un partido.',
        'protocolo': ('Salida de parado. Dos conos a 20 m, cronómetro al primer '
                      'movimiento. Dos intentos con 3 min de descanso, se anota '
                      'el mejor.'),
        'fuente': 'Haugen, Tønnessen & Seiler (2013), IJSPP 8(2):148-156',
        'campos': [_campo('time_seconds', 'Tiempo', 's', 2, 5.5, 2, '3.02', MENOR)],
        'baremos': {'time_seconds': {
            ('general', 'elite'):       [2.94, 3.02, 3.11, 3.23],
            ('general', 'profesional'): [2.99, 3.07, 3.16, 3.28],
            ('general', 'semipro'):     [3.05, 3.13, 3.22, 3.35],
            ('general', 'amateur'):     [3.12, 3.21, 3.31, 3.45],
            ('sub_18', 'general'):      [3.02, 3.10, 3.19, 3.31],
            ('sub_17', 'general'):      [3.07, 3.15, 3.24, 3.37],
            ('sub_16', 'general'):      [3.13, 3.21, 3.31, 3.44],
            ('sub_15', 'general'):      [3.20, 3.29, 3.40, 3.54],
            ('sub_14', 'general'):      [3.30, 3.40, 3.52, 3.67],
            ('general', 'general'):     [3.00, 3.09, 3.19, 3.31],
        }},
    },

    'sj': {
        'nombre': 'Salto sin contramovimiento (SJ)',
        'categoria': 'fisico', 'orden': 131, 'icono': 'trending-up',
        'descripcion': 'Fuerza explosiva pura, sin aprovechar el rebote elástico.',
        'protocolo': ('El jugador se queda quieto 3 segundos en media sentadilla '
                      '(90°) y salta sin bajar más. Manos en la cadera. Comparado '
                      'con el CMJ da el índice elástico: si el CMJ supera al SJ en '
                      'menos del 5 %, toca trabajar pliometría.'),
        'fuente': 'Bosco C, Luhtanen P, Komi PV (1983), Eur J Appl Physiol 50:273-282',
        'formula': 'Índice elástico = (CMJ − SJ) / SJ × 100',
        'campos': [_campo('height_cm', 'Altura', 'cm', 10, 75, 1, '38.0', MAYOR)],
        'baremos': {'height_cm': {
            ('general', 'elite'):       [42, 38, 34, 30],
            ('general', 'profesional'): [40, 36, 32, 28],
            ('general', 'amateur'):     [35, 31, 27, 23],
            ('sub_17', 'general'):      [37, 33, 29, 25],
            ('sub_15', 'general'):      [32, 28, 24, 21],
            ('general', 'general'):     [38, 34, 30, 26],
        }},
    },

    'abalakov': {
        'nombre': 'Salto Abalakov',
        'categoria': 'fisico', 'orden': 132, 'icono': 'trending-up',
        'descripcion': 'Salto máximo con ayuda de brazos: lo que se usa al rematar de cabeza.',
        'protocolo': ('Igual que el CMJ pero con los brazos libres y carrera de '
                      'cero pasos. Suele dar entre 4 y 8 cm más que el CMJ.'),
        'fuente': 'Abalakov (1938); baremos de Reilly, Bangsbo & Franks (2000)',
        'campos': [_campo('height_cm', 'Altura', 'cm', 15, 90, 1, '50.0', MAYOR)],
        'baremos': {'height_cm': {
            ('general', 'elite'):       [56, 51, 46, 40],
            ('general', 'profesional'): [53, 48, 43, 38],
            ('general', 'amateur'):     [46, 42, 37, 32],
            ('sub_17', 'general'):      [49, 44, 39, 34],
            ('sub_15', 'general'):      [42, 38, 33, 28],
            ('general', 'general'):     [51, 46, 41, 36],
        }},
    },

    'salto_horizontal': {
        'nombre': 'Salto horizontal a pies juntos',
        'categoria': 'fisico', 'orden': 133, 'icono': 'trending-up',
        'descripcion': 'Potencia horizontal. No hace falta más que una cinta métrica.',
        'protocolo': ('De pie tras la línea, pies juntos. Salta hacia adelante con '
                      'impulso de brazos y cae con los dos pies. Se mide de la '
                      'línea al talón más retrasado. Tres intentos, el mejor.'),
        'fuente': 'EUROFIT, Council of Europe (1993)',
        'campos': [_campo('distance_cm', 'Distancia', 'cm', 80, 320, 0, '215', MAYOR)],
        'baremos': {'distance_cm': {
            ('general', 'elite'):       [255, 240, 225, 205],
            ('general', 'profesional'): [245, 230, 215, 195],
            ('general', 'amateur'):     [230, 215, 200, 180],
            ('sub_18', 'general'):      [240, 225, 210, 190],
            ('sub_16', 'general'):      [225, 210, 195, 175],
            ('sub_14', 'general'):      [200, 185, 170, 152],
            ('sub_12', 'general'):      [175, 162, 148, 132],
            ('general', 'general'):     [240, 225, 210, 190],
        }},
    },

    # ─── Agilidad ──────────────────────────────────────────────────────────
    'illinois': {
        'nombre': 'Test de agilidad de Illinois',
        'categoria': 'fisico', 'orden': 140, 'icono': 'shuffle',
        'descripcion': 'Cambios de dirección a alta velocidad en circuito cerrado.',
        'protocolo': ('Circuito de 10 m de largo por 5 de ancho, con 4 conos en el '
                      'centro separados 3,3 m. Se sale tumbado boca abajo con las '
                      'manos a la altura de los hombros; a la señal se recorre el '
                      'circuito en zig-zag.'),
        'fuente': 'Getchell B (1979), Physical Fitness: A Way of Life, 2ª ed.',
        'campos': [_campo('time_seconds', 'Tiempo', 's', 12, 30, 2, '15.80', MENOR)],
        'baremos': {'time_seconds': {
            ('general', 'elite'):       [15.00, 15.60, 16.30, 17.20],
            ('general', 'profesional'): [15.20, 15.90, 16.60, 17.50],
            ('general', 'amateur'):     [15.90, 16.60, 17.40, 18.30],
            ('sub_17', 'general'):      [15.60, 16.30, 17.00, 17.90],
            ('sub_15', 'general'):      [16.30, 17.00, 17.80, 18.70],
            ('general', 'general'):     [15.20, 15.90, 16.70, 17.60],
        }},
    },

    'test_505': {
        'nombre': 'Test 505 (cambio de dirección)',
        'categoria': 'fisico', 'orden': 141, 'icono': 'corner-up-left',
        'descripcion': 'Frenar y volver a acelerar en 180°: el gesto del lateral.',
        'protocolo': ('Lanzamiento de 10 m, se cronometra desde los 5 m antes de la '
                      'línea de giro: el jugador pisa la línea, gira 180° y vuelve a '
                      'cruzar los 5 m. Se mide con cada pierna; una diferencia mayor '
                      'al 10 % entre lados es una asimetría a corregir.'),
        'fuente': 'Draper JA & Lancaster MG (1985), Aust J Sci Med Sport 17(1):15-18',
        'campos': [
            _campo('right', 'Giro pierna derecha', 's', 1.8, 4, 2, '2.35', MENOR),
            _campo('left', 'Giro pierna izquierda', 's', 1.8, 4, 2, '2.38', MENOR,
                   principal=False),
        ],
        'baremos': {c: {
            ('general', 'elite'):       [2.20, 2.30, 2.42, 2.56],
            ('general', 'profesional'): [2.25, 2.36, 2.48, 2.62],
            ('general', 'amateur'):     [2.36, 2.48, 2.60, 2.75],
            ('sub_17', 'general'):      [2.30, 2.41, 2.53, 2.68],
            ('general', 'general'):     [2.26, 2.37, 2.49, 2.63],
        } for c in ('right', 'left')},
    },

    't_test': {
        'nombre': 'T-Test',
        'categoria': 'fisico', 'orden': 142, 'icono': 'shuffle',
        'descripcion': 'Agilidad en cuatro direcciones: frente, lateral y espalda.',
        'protocolo': ('Cuatro conos en T: 10 m de frente y 5 m a cada lado. Se corre '
                      'de frente al cono central, desplazamiento lateral al izquierdo, '
                      'lateral hasta el derecho, vuelta al centro y de espaldas hasta '
                      'la salida. Los pies no se cruzan y hay que tocar cada cono.'),
        'fuente': 'Semenick D (1990), NSCA Journal 12(1):36-37',
        'campos': [_campo('time_seconds', 'Tiempo', 's', 7, 18, 2, '10.20', MENOR)],
        'baremos': {'time_seconds': {
            ('general', 'elite'):       [9.20, 9.70, 10.30, 11.00],
            ('general', 'profesional'): [9.50, 10.00, 10.60, 11.30],
            ('general', 'amateur'):     [10.10, 10.70, 11.40, 12.20],
            ('sub_17', 'general'):      [9.90, 10.50, 11.10, 11.90],
            ('sub_15', 'general'):      [10.50, 11.10, 11.80, 12.60],
            ('general', 'general'):     [9.50, 10.10, 10.70, 11.50],
        }},
    },

    # ─── Fuerza y composición ──────────────────────────────────────────────
    'abdominales_30s': {
        'nombre': 'Abdominales en 30 segundos',
        'categoria': 'fisico', 'orden': 150, 'icono': 'activity',
        'descripcion': 'Resistencia de la musculatura del tronco.',
        'protocolo': ('Tumbado, rodillas a 90°, manos en las sienes y pies sujetos. '
                      'Sube hasta tocar las rodillas con los codos y baja hasta '
                      'apoyar la espalda. Repeticiones completas en 30 s.'),
        'fuente': 'EUROFIT, Council of Europe (1993)',
        'campos': [_campo('reps', 'Repeticiones', '', 0, 60, 0, '28', MAYOR)],
        'baremos': {'reps': {
            ('general', 'general'):  [30, 26, 22, 18],
            ('sub_17', 'general'):   [29, 25, 21, 17],
            ('sub_15', 'general'):   [26, 22, 19, 15],
            ('sub_14', 'general'):   [23, 20, 17, 13],
        }},
    },

    'plancha': {
        'nombre': 'Plancha isométrica',
        'categoria': 'fisico', 'orden': 151, 'icono': 'minus',
        'descripcion': 'Estabilidad del núcleo, clave para prevenir lesiones.',
        'protocolo': ('Apoyo en antebrazos y puntas de los pies, cuerpo en línea '
                      'recta. Se cronometra hasta que la cadera cae o se levanta. '
                      'Se corta a los 4 minutos.'),
        'fuente': 'McGill SM (2007), Low Back Disorders, 2ª ed.',
        'campos': [_campo('time_seconds', 'Tiempo aguantado', 's', 0, 300, 0, '95', MAYOR)],
        'baremos': {'time_seconds': {
            ('general', 'general'):  [150, 110, 75, 45],
            ('sub_15', 'general'):   [120, 90, 60, 35],
        }},
    },

    'antropometria': {
        'nombre': 'Perfil antropométrico',
        'categoria': 'fisico', 'orden': 160, 'icono': 'user',
        'descripcion': 'Talla, peso y grasa corporal para seguir el crecimiento.',
        'protocolo': ('Talla descalzo con occipital, espalda y talones en la pared. '
                      'Peso en ropa ligera. El porcentaje de grasa con plicómetro '
                      '(Faulkner, 4 pliegues) o bioimpedancia; anota siempre con '
                      'cuál, porque no son intercambiables. En formación esto no '
                      'evalúa: sirve para vigilar el estirón.'),
        'fuente': 'Reilly, Bangsbo & Franks (2000); Faulkner JA (1968)',
        'formula': 'IMC = peso (kg) / talla (m)²',
        'campos': [
            _campo('height', 'Estatura', 'cm', 110, 215, 1, '176.0', MAYOR,
                   principal=False),
            _campo('weight', 'Peso', 'kg', 25, 130, 1, '70.5', MAYOR, principal=False),
            _campo('body_fat', 'Grasa corporal', '%', 3, 40, 1, '11.5', MENOR),
        ],
        'baremos': {'body_fat': {
            ('general', 'elite'):       [8.5, 10.5, 12.5, 15.0],
            ('general', 'profesional'): [9.0, 11.0, 13.0, 15.5],
            ('general', 'amateur'):     [10.0, 12.5, 15.0, 18.0],
            ('sub_17', 'general'):      [9.5, 11.5, 13.5, 16.0],
            ('sub_15', 'general'):      [10.5, 12.5, 15.0, 17.5],
            ('general', 'general'):     [9.5, 11.5, 13.5, 16.0],
        }},
    },

    # ─── Técnica ───────────────────────────────────────────────────────────
    'lspt': {
        'nombre': 'Loughborough Soccer Passing Test',
        'categoria': 'tecnico', 'orden': 170, 'icono': 'target',
        'descripcion': 'El test de pase con más respaldo científico que existe.',
        'protocolo': ('Cuadrado de 12 × 9,5 m con cuatro bancos de colores, cada uno '
                      'con una diana de 60 cm. 16 pases (4 a cada color) siguiendo el '
                      'color que canta el evaluador. Al tiempo bruto se le suman '
                      'penalizaciones: +5 s por fallar el banco, +3 s por dar fuera '
                      'de la diana, +3 s por salirse del área, +2 s por tocar de más '
                      'y −1 s por dar en la diana.'),
        'fuente': 'Ali A et al. (2007), J Sports Sci 25(13):1461-1470',
        'formula': 'Tiempo final = tiempo bruto + penalizaciones − bonificaciones',
        'campos': [
            _campo('final_time', 'Tiempo final', 's', 25, 140, 1, '52.0', MENOR),
            _campo('raw_time', 'Tiempo bruto', 's', 20, 130, 1, '45.0', MENOR,
                   principal=False),
            _campo('penalty', 'Penalización', 's', 0, 90, 0, '7', MENOR,
                   principal=False),
        ],
        'baremos': {'final_time': {
            ('general', 'elite'):       [44, 50, 57, 66],
            ('general', 'profesional'): [47, 53, 60, 70],
            ('general', 'amateur'):     [55, 62, 70, 82],
            ('sub_17', 'general'):      [52, 59, 67, 78],
            ('sub_15', 'general'):      [58, 66, 75, 87],
            ('general', 'general'):     [48, 55, 63, 73],
        }},
    },

    'juegos_malabares': {
        'nombre': 'Toques de balón (dominadas)',
        'categoria': 'tecnico', 'orden': 171, 'icono': 'circle',
        'descripcion': 'Sensibilidad y control del balón en el aire.',
        'protocolo': ('Toques seguidos sin que el balón caiga, alternando pie derecho, '
                      'pie izquierdo y muslo. No valen dos toques seguidos con la '
                      'misma superficie. Dos intentos, se anota el mejor.'),
        'fuente': 'Uso extendido en formación; sin baremo publicado con muestra amplia',
        'campos': [_campo('touches', 'Toques alternados', '', 0, 500, 0, '45', MAYOR)],
        'baremos': {'touches': {
            ('general', 'general'):  [80, 45, 22, 10],
            ('sub_15', 'general'):   [60, 35, 18, 8],
            ('sub_12', 'general'):   [40, 22, 12, 5],
        }},
    },

    'golpeo_largo': {
        'nombre': 'Golpeo de larga distancia',
        'categoria': 'tecnico', 'orden': 172, 'icono': 'send',
        'descripcion': 'Alcance y precisión en el cambio de orientación.',
        'protocolo': ('Cinco golpeos desde parado a un círculo de 5 m de radio situado '
                      'a 40 m. Se cuentan los que caen dentro y se anota la distancia '
                      'máxima alcanzada en un golpeo libre.'),
        'fuente': 'Valoración observacional del cuerpo técnico',
        'campos': [
            _campo('successful', 'Golpeos al círculo', '/5', 0, 5, 0, '3', MAYOR),
            _campo('max_distance', 'Distancia máxima', 'm', 15, 90, 0, '52', MAYOR,
                   principal=False),
        ],
        'baremos': {
            'successful': {('general', 'general'): [4, 3, 2, 1]},
            'max_distance': {
                ('general', 'profesional'): [65, 57, 50, 42],
                ('sub_17', 'general'):      [58, 51, 44, 37],
                ('sub_15', 'general'):      [50, 44, 38, 31],
                ('general', 'general'):     [60, 53, 46, 39],
            },
        },
    },

    # ─── Mental y táctica ──────────────────────────────────────────────────
    'perfil_tactico': {
        'nombre': 'Perfil Táctico (6 dimensiones)',
        'categoria': 'mental', 'orden': 180, 'icono': 'map',
        'descripcion': 'Lo que el entrenador ve en el partido, puesto en números.',
        'protocolo': ('Se rellena tras observar al jugador en dos o tres PARTIDOS, no '
                      'en un entrenamiento suelto. Cada dimensión de 1 a 10. Conviene '
                      'que lo hagan dos miembros del cuerpo técnico por separado: si '
                      'hay más de 2 puntos de diferencia, hablarlo antes de anotar.'),
        'fuente': 'Adaptado de Kannekens R et al. (2011), Scand J Med Sci Sports',
        'campos': [
            _nota('positioning', 'Posicionamiento sin balón'),
            _nota('decision', 'Toma de decisión', principal=False),
            _nota('reading', 'Lectura del juego', principal=False),
            _nota('pressing', 'Presión y basculación', principal=False),
            _nota('transitions', 'Transiciones', principal=False),
            _nota('teamwork', 'Juego colectivo', principal=False),
        ],
        'baremos': {c: {('general', 'general'): [9, 7, 6, 4]}
                    for c in ('positioning', 'decision', 'reading',
                              'pressing', 'transitions', 'teamwork')},
    },

    'reaccion': {
        'nombre': 'Tiempo de reacción',
        'categoria': 'mental', 'orden': 181, 'icono': 'zap',
        'descripcion': 'Velocidad de respuesta a un estímulo visual.',
        'protocolo': ('Prueba de la regla: el evaluador sujeta una regla de 30 cm en '
                      'vertical entre los dedos del jugador y la suelta sin avisar. Se '
                      'anota a cuántos centímetros la atrapa. Tres intentos, se '
                      'promedia.'),
        'fuente': 'Del Rossi G et al. (2014), J Athl Train 49(2):189-193',
        'campos': [_campo('drop_cm', 'Centímetros de caída', 'cm', 3, 30, 1, '14.0', MENOR)],
        'baremos': {'drop_cm': {('general', 'general'): [11.0, 14.0, 18.0, 23.0]}},
    },
}


# El catálogo que ve la app: primero las del MVP, luego las añadidas.
CATALOGO = {**_MVP, **_EXTRA}

# Qué pruebas venían de la app original. La pantalla las marca para que se
# distingan de las añadidas.
CLAVES_MVP = set(_MVP)


# ═══════════════════════════════════════════════════════════════════════════
#  CONSULTA
# ═══════════════════════════════════════════════════════════════════════════
#  Las tres familias son las del MVP y en su mismo orden. No se añadieron
#  familias nuevas: las pruebas extra caben en estas tres, y meter pestañas
#  que antes no existían cambiaría la pantalla sin necesidad.
CATEGORIAS = [
    ('fisico',  'Físicas',  '🏃', 'Resistencia, velocidad, potencia y agilidad'),
    ('tecnico', 'Técnicas', '⚽', 'Pase, control, conducción y remate'),
    ('mental',  'Mentales', '🧠', 'Observación psicológica y táctica'),
]

CATEGORIA_META = {c: {'etiqueta': e, 'emoji': em, 'descripcion': d}
                  for c, e, em, d in CATEGORIAS}


# ═══════════════════════════════════════════════════════════════════════════
#  QUÉ ATRIBUTO DE LA FICHA MUEVE CADA PRUEBA
# ═══════════════════════════════════════════════════════════════════════════
#  Una marca no se queda en una tabla aparte: sube o baja el atributo que le
#  toca en la ficha del jugador, como hace teamTestAnalysis.ts en la app
#  original. Es el principio del proyecto — lo que el entrenador mide cambia
#  las estadísticas reales del jugador.
#
#  Manda la familia de la prueba. Solo se listan aparte las que miden algo
#  distinto de lo que sugiere su familia; inventar pesos para las treinta y
#  una sería precisión fingida.
ATRIBUTO_DE_FAMILIA = {'fisico': 'fisico', 'tecnico': 'tecnica', 'mental': 'mental'}

PESOS_PROPIOS = {
    # Está entre las mentales porque se puntúa observando, pero lo que mide es
    # lectura de juego y posicionamiento.
    'perfil_tactico': {'tactico': 1.0},
    # Conducir entre conos es técnica, pero el cronómetro premia la agilidad.
    'conduccion_conos': {'tecnica': 0.7, 'fisico': 0.3},
}


def atributos_de(t):
    """{atributo: peso} que mueve una prueba. Los pesos suman 1.

    Acepta la prueba entera —no solo la clave— para que valga igual con las
    pruebas que se inventa el entrenador, que no están en el catálogo.
    """
    propios = PESOS_PROPIOS.get((t or {}).get('clave'))
    if propios:
        return dict(propios)
    familia = (t or {}).get('categoria') or 'fisico'
    return {ATRIBUTO_DE_FAMILIA.get(familia, 'fisico'): 1.0}


def test(clave):
    """Devuelve la prueba del catálogo, o None si la clave no existe."""
    t = CATALOGO.get(clave)
    if not t:
        return None
    return dict(t, clave=clave, _mvp=clave in CLAVES_MVP)


def tests_por_categoria(categoria=None):
    """Las pruebas ordenadas como en el MVP (por `orden`, no alfabéticamente)."""
    salida = []
    for clave, t in CATALOGO.items():
        if categoria and t['categoria'] != categoria:
            continue
        salida.append(dict(t, clave=clave, _mvp=clave in CLAVES_MVP))
    return sorted(salida, key=lambda t: (t['categoria'] != 'fisico',
                                         t['categoria'] != 'tecnico',
                                         t.get('orden', 999)))


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
            return {'cortes': tabla[par], 'edad': par[0], 'nivel': par[1],
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
        margen = max(abs(e - b), 1e-6)
        return int(min(100, 95 + 5 * min(1.0, (valor - e) / margen)))
    anterior = e
    for corte, base, techo in tramos[1:]:
        if valor >= corte:
            rango = max(anterior - corte, 1e-6)
            return int(round(base + (techo - base) * (valor - corte) / rango))
        anterior = corte
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
        partes.append(f'{etq} {signo} {corte:g}{(" " + unidad) if unidad else ""}')
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
