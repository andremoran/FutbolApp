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
            #  Minimo 10 y no 20: el baremo de sub-12 pone el corte flojo en
            #  17 cm, asi que un nino que saltaba menos de 20 no se podia ni
            #  registrar — el formulario le rechazaba la marca.
            _campo('height_cm', 'Altura', 'cm', 10, 80, 1, '42.5', MAYOR),
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


# ═══════════════════════════════════════════════════════════════════════════
#  BLOQUE C — LAS PRUEBAS AVALADAS DE LA BIBLIOTECA
# ═══════════════════════════════════════════════════════════════════════════
#  La biblioteca son 40 pruebas con protocolo y bibliografía publicados, las
#  mismas que la app nativa enseña en «Biblioteca de tests». Trece de ellas ya
#  estaban arriba midiendo exactamente lo mismo (Yo-Yo, CMJ, T-Test, LSPT...) y
#  NO se repiten aquí: se enriquecen en su sitio desde `tests_biblioteca.py`.
#  Duplicarlas partiría en dos el histórico del jugador.
#
#  Estas son las 27 restantes. Los baremos salen de `_baremos_40.py`, que parte
#  de los valores normativos que cada prueba publica y los proyecta a los once
#  contextos con la curva medida sobre las doce de la biblioteca que ya traían
#  baremo real. Los valores publicados se respetan tal cual en su contexto: si
#  la fuente dice que el sub-18 bueno son 20 m, en sub-18 salen 20 m.
# ═══════════════════════════════════════════════════════════════════════════

_BIBLIOTECA_TESTS = {

    'squat_1rm': {
        'nombre': '1RM Back Squat',
        'categoria': 'fisico',
        'orden': 250,
        'icono': 'trending-up',
        'fuente': 'Brzycki, M. (1993). JOPERD, 64(1), 88–90',
        'campos': [
            _campo('ratio', 'Ratio 1RM / peso corporal', '×', 0.4, 3.0, 2, '1.50', MAYOR),
            _campo('one_rm_kg', 'Carga máxima', 'kg', 20, 300, 1, '110.0', MAYOR, False),
            _campo('bw_kg', 'Peso corporal', 'kg', 25, 130, 1, '73.0', MAYOR, False),
        ],
        'baremos': {
            'ratio': {
                ('general', 'elite'):        [1.95, 1.8, 1.65, 1.5],
                ('general', 'profesional'):  [1.75, 1.6, 1.45, 1.3],
                ('general', 'semipro'):      [1.65, 1.5, 1.35, 1.2],
                ('general', 'amateur'):      [1.55, 1.4, 1.25, 1.1],
                ('sub_18', 'general'):       [1.55, 1.35, 1.15, 1.0],
                ('sub_17', 'general'):       [1.4, 1.2, 1.0, 0.85],
                ('sub_16', 'general'):       [1.3, 1.1, 0.92, 0.77],
                ('sub_15', 'general'):       [1.2, 1.0, 0.85, 0.7],
                ('sub_14', 'general'):       [1.14, 0.95, 0.8, 0.66],
                ('sub_12', 'general'):       [0.98, 0.82, 0.7, 0.57],
                ('general', 'general'):      [1.68, 1.53, 1.39, 1.25],
            },
        },
    },

    'ift_30_15': {
        'nombre': '30-15 Intermittent Fitness Test (30-15IFT)',
        'categoria': 'fisico',
        'orden': 260,
        'icono': 'activity',
        'fuente': 'Buchheit, M. (2008). The 30-15 Intermittent Fitness Test: accuracy '
        'for individualizing interval training. Journal of Strength and '
        'Conditioning Research, 22(2), 365–374',
        'campos': [
            _campo('vift_kmh', 'VIFT', 'km/h', 8, 26, 1, '18.5', MAYOR),
            _campo('vo2max', 'VO₂max estimado', 'ml/kg/min', 25, 80, 1, '55.0', MAYOR, False),
        ],
        'baremos': {
            'vift_kmh': {
                ('general', 'elite'):        [21.0, 20.0, 19.0, 18.0],
                ('general', 'profesional'):  [20.0, 19.0, 18.0, 17.0],
                ('general', 'semipro'):      [19.4, 18.4, 17.4, 16.4],
                ('general', 'amateur'):      [18.7, 17.7, 16.7, 15.7],
                ('sub_18', 'general'):       [19.0, 18.0, 17.0, 16.0],
                ('sub_17', 'general'):       [17.7, 16.8, 15.8, 14.9],
                ('sub_16', 'general'):       [16.8, 15.9, 15.0, 14.1],
                ('sub_15', 'general'):       [15.9, 15.1, 14.2, 13.4],
                ('sub_14', 'general'):       [15.5, 14.7, 13.9, 13.1],
                ('sub_12', 'general'):       [14.4, 13.6, 12.9, 12.1],
                ('general', 'general'):      [19.9, 18.9, 17.9, 16.9],
            },
            'vo2max': {
                ('general', 'elite'):        [62.0, 58.0, 54.0, 50.0],
                ('general', 'profesional'):  [58.4, 54.6, 50.8, 47.1],
                ('general', 'semipro'):      [56.4, 52.7, 49.1, 45.5],
                ('general', 'amateur'):      [53.9, 50.4, 47.0, 43.5],
                ('sub_18', 'general'):       [54.9, 51.3, 47.8, 44.3],
                ('sub_17', 'general'):       [51.1, 47.8, 44.5, 41.2],
                ('sub_16', 'general'):       [48.5, 45.3, 42.2, 39.1],
                ('sub_15', 'general'):       [45.9, 43.0, 40.0, 37.0],
                ('sub_14', 'general'):       [44.8, 41.9, 39.0, 36.1],
                ('sub_12', 'general'):       [41.6, 38.9, 36.2, 33.6],
                ('general', 'general'):      [58.0, 54.2, 50.5, 46.7],
            },
        },
    },

    'dinamometria': {
        'nombre': 'Dinamometría Manual',
        'categoria': 'fisico',
        'orden': 270,
        'icono': 'minimize-2',
        'fuente': 'Leyk, D. et al. (2007). European Journal of Applied Physiology, '
        '99(4), 415–421',
        'campos': [
            _campo('grip_dom_kg', 'Prensión mano dominante', 'kg', 10, 100, 1, '52.0', MAYOR),
            _campo('grip_nd_kg', 'Prensión mano no dominante', 'kg', 10, 100, 1, '49.0', MAYOR, False),
        ],
        'baremos': {
            'grip_dom_kg': {
                ('general', 'elite'):        [83.6, 74.6, 66.9, 59.1],
                ('general', 'profesional'):  [74.3, 66.3, 59.4, 52.6],
                ('general', 'semipro'):      [69.6, 62.1, 55.7, 49.3],
                ('general', 'amateur'):      [65.0, 58.0, 52.0, 46.0],
                ('sub_18', 'general'):       [61.4, 54.8, 49.1, 43.4],
                ('sub_17', 'general'):       [54.9, 49.0, 43.9, 38.9],
                ('sub_16', 'general'):       [49.8, 44.5, 39.9, 35.3],
                ('sub_15', 'general'):       [45.2, 40.3, 36.2, 32.0],
                ('sub_14', 'general'):       [42.8, 38.2, 34.2, 30.3],
                ('sub_12', 'general'):       [37.0, 33.1, 29.6, 26.2],
                ('general', 'general'):      [71.2, 63.5, 57.0, 50.4],
            },
            'grip_nd_kg': {
                ('general', 'elite'):        [78.4, 70.7, 63.0, 55.3],
                ('general', 'profesional'):  [69.7, 62.9, 56.0, 49.1],
                ('general', 'semipro'):      [65.4, 58.9, 52.5, 46.1],
                ('general', 'amateur'):      [61.0, 55.0, 49.0, 43.0],
                ('sub_18', 'general'):       [57.6, 51.9, 46.3, 40.6],
                ('sub_17', 'general'):       [51.5, 46.5, 41.4, 36.3],
                ('sub_16', 'general'):       [46.8, 42.2, 37.6, 33.0],
                ('sub_15', 'general'):       [42.4, 38.3, 34.1, 29.9],
                ('sub_14', 'general'):       [40.2, 36.2, 32.3, 28.3],
                ('sub_12', 'general'):       [34.8, 31.3, 27.9, 24.5],
                ('general', 'general'):      [66.8, 60.2, 53.7, 47.1],
            },
        },
    },

    'list_test': {
        'nombre': 'Loughborough Intermittent Shuttle Test (LIST)',
        'categoria': 'fisico',
        'orden': 280,
        'icono': 'clock',
        'fuente': 'Nicholas, C.W. et al. (1995). Journal of Sports Sciences, 13(6), '
        '474–481',
        'campos': [
            _campo('total_min', 'Minutos mantenidos', 'min', 0, 90, 0, '75', MAYOR),
            _campo('sprint_dec_pct', 'Descenso del sprint', '%', 0, 30, 1, '4.0', MENOR, False),
        ],
        'baremos': {
            'total_min': {
                ('general', 'elite'):        [90, 85, 75, 60],
                ('general', 'profesional'):  [80, 76, 67, 53],
                ('general', 'semipro'):      [75, 71, 62, 50],
                ('general', 'amateur'):      [70, 66, 58, 47],
                ('sub_18', 'general'):       [66, 62, 55, 44],
                ('sub_17', 'general'):       [59, 56, 49, 39],
                ('sub_16', 'general'):       [54, 51, 45, 36],
                ('sub_15', 'general'):       [49, 46, 41, 32],
                ('sub_14', 'general'):       [46, 44, 38, 31],
                ('sub_12', 'general'):       [40, 38, 33, 27],
                ('general', 'general'):      [77, 72, 64, 51],
            },
            'sprint_dec_pct': {
                ('general', 'elite'):        [1.9, 3.3, 4.7, 6.6],
                ('general', 'profesional'):  [2.0, 3.5, 5.0, 7.0],
                ('general', 'semipro'):      [2.1, 3.6, 5.2, 7.2],
                ('general', 'amateur'):      [2.2, 3.8, 5.4, 7.6],
                ('sub_18', 'general'):       [2.1, 3.7, 5.3, 7.4],
                ('sub_17', 'general'):       [2.3, 4.0, 5.7, 8.0],
                ('sub_16', 'general'):       [2.4, 4.2, 6.0, 8.4],
                ('sub_15', 'general'):       [2.5, 4.4, 6.4, 8.9],
                ('sub_14', 'general'):       [2.6, 4.6, 6.5, 9.1],
                ('sub_12', 'general'):       [2.8, 4.9, 7.0, 9.8],
                ('general', 'general'):      [2.0, 3.5, 5.0, 7.0],
            },
        },
    },

    'margaria_kalamen': {
        'nombre': 'Margaria-Kalamen (Escalera)',
        'categoria': 'fisico',
        'orden': 290,
        'icono': 'chevron-up',
        'fuente': 'Kalamen, J. (1968). Doctoral Dissertation, The Ohio State University',
        'campos': [
            _campo('power_wkg', 'Potencia relativa', 'W/kg', 5, 35, 1, '20.0', MAYOR),
            _campo('power_w', 'Potencia', 'W', 300, 2600, 0, '1600', MAYOR, False),
        ],
        'baremos': {
            'power_wkg': {
                ('general', 'elite'):        [23.4, 21.2, 19.1, 17.0],
                ('general', 'profesional'):  [22.0, 20.0, 18.0, 16.0],
                ('general', 'semipro'):      [21.2, 19.3, 17.4, 15.5],
                ('general', 'amateur'):      [20.3, 18.5, 16.6, 14.8],
                ('sub_18', 'general'):       [20.7, 18.8, 16.9, 15.0],
                ('sub_17', 'general'):       [19.3, 17.5, 15.8, 14.0],
                ('sub_16', 'general'):       [18.3, 16.6, 14.9, 13.3],
                ('sub_15', 'general'):       [17.3, 15.7, 14.2, 12.6],
                ('sub_14', 'general'):       [16.9, 15.4, 13.8, 12.3],
                ('sub_12', 'general'):       [15.7, 14.3, 12.8, 11.4],
                ('general', 'general'):      [21.9, 19.9, 17.9, 15.9],
            },
            'power_w': {
                ('general', 'elite'):        [2138, 1912, 1688, 1462],
                ('general', 'profesional'):  [1900, 1700, 1500, 1300],
                ('general', 'semipro'):      [1781, 1594, 1406, 1219],
                ('general', 'amateur'):      [1662, 1488, 1312, 1138],
                ('sub_18', 'general'):       [1570, 1404, 1239, 1074],
                ('sub_17', 'general'):       [1404, 1256, 1109, 961],
                ('sub_16', 'general'):       [1274, 1140, 1006, 872],
                ('sub_15', 'general'):       [1157, 1035, 913, 791],
                ('sub_14', 'general'):       [1094, 979, 864, 749],
                ('sub_12', 'general'):       [948, 848, 748, 648],
                ('general', 'general'):      [1821, 1629, 1437, 1246],
            },
        },
    },

    'rast': {
        'nombre': 'RAST (Running-based Anaerobic Sprint Test)',
        'categoria': 'fisico',
        'orden': 300,
        'icono': 'zap',
        'fuente': 'Zacharogiannis, E., Paradisis, G., & Tziortzis, S. (2004). Medicine '
        'and Science in Sports and Exercise, 36(5), S116',
        'campos': [
            _campo('pmax_w', 'Potencia máxima', 'W', 200, 1600, 0, '850', MAYOR),
            _campo('pmin_w', 'Potencia mínima', 'W', 100, 1200, 0, '600', MAYOR, False),
            _campo('fatigue_idx', 'Índice de fatiga', 'W/s', 0, 40, 1, '8.0', MENOR, False),
        ],
        'baremos': {
            'pmax_w': {
                ('general', 'elite'):        [1000, 900, 800, 700],
                ('general', 'profesional'):  [889, 800, 711, 622],
                ('general', 'semipro'):      [833, 750, 667, 583],
                ('general', 'amateur'):      [778, 700, 622, 544],
                ('sub_18', 'general'):       [734, 661, 587, 514],
                ('sub_17', 'general'):       [657, 591, 526, 460],
                ('sub_16', 'general'):       [596, 537, 477, 417],
                ('sub_15', 'general'):       [541, 487, 433, 379],
                ('sub_14', 'general'):       [512, 461, 410, 358],
                ('sub_12', 'general'):       [443, 399, 355, 310],
                ('general', 'general'):      [852, 767, 681, 596],
            },
            'pmin_w': {
                ('general', 'elite'):        [700, 620, 540, 460],
                ('general', 'profesional'):  [622, 551, 480, 409],
                ('general', 'semipro'):      [583, 517, 450, 383],
                ('general', 'amateur'):      [544, 482, 420, 358],
                ('sub_18', 'general'):       [514, 455, 397, 338],
                ('sub_17', 'general'):       [460, 407, 355, 302],
                ('sub_16', 'general'):       [417, 370, 322, 274],
                ('sub_15', 'general'):       [379, 335, 292, 249],
                ('sub_14', 'general'):       [358, 317, 276, 235],
                ('sub_12', 'general'):       [310, 275, 239, 204],
                ('general', 'general'):      [596, 528, 460, 392],
            },
            'fatigue_idx': {
                ('general', 'elite'):        [4.7, 6.6, 9.4, 12.2],
                ('general', 'profesional'):  [5.0, 7.0, 10.0, 13.0],
                ('general', 'semipro'):      [5.2, 7.2, 10.4, 13.5],
                ('general', 'amateur'):      [5.4, 7.6, 10.8, 14.1],
                ('sub_18', 'general'):       [5.3, 7.4, 10.6, 13.8],
                ('sub_17', 'general'):       [5.7, 8.0, 11.4, 14.8],
                ('sub_16', 'general'):       [6.0, 8.4, 12.0, 15.7],
                ('sub_15', 'general'):       [6.4, 8.9, 12.7, 16.5],
                ('sub_14', 'general'):       [6.5, 9.1, 13.0, 16.9],
                ('sub_12', 'general'):       [7.0, 9.8, 14.0, 18.2],
                ('general', 'general'):      [5.0, 7.0, 10.1, 13.1],
            },
        },
    },

    'abdominales_60s': {
        'nombre': 'Resistencia Abdominal (NSCA/ACSM)',
        'categoria': 'fisico',
        'orden': 310,
        'icono': 'octagon',
        'fuente': 'ACSM. (2022). ACSM\'s Guidelines for Exercise Testing and '
        'Prescription (11th ed.)',
        'campos': [
            _campo('reps', 'Repeticiones en 60 s', 'reps', 0, 100, 0, '45', MAYOR),
        ],
        'baremos': {
            'reps': {
                ('general', 'elite'):        [58, 52, 46, 39],
                ('general', 'profesional'):  [54, 49, 43, 37],
                ('general', 'semipro'):      [52, 47, 42, 36],
                ('general', 'amateur'):      [50, 45, 40, 34],
                ('sub_18', 'general'):       [51, 46, 41, 35],
                ('sub_17', 'general'):       [47, 43, 38, 32],
                ('sub_16', 'general'):       [45, 40, 36, 31],
                ('sub_15', 'general'):       [43, 38, 34, 29],
                ('sub_14', 'general'):       [42, 37, 33, 28],
                ('sub_12', 'general'):       [39, 35, 31, 26],
                ('general', 'general'):      [54, 48, 43, 37],
            },
        },
    },

    'y_balance': {
        'nombre': 'Y-Balance Test (YBT)',
        'categoria': 'fisico',
        'orden': 320,
        'icono': 'compass',
        'fuente': 'Plisky, P.J. et al. (2006). J. Orthopaedic & Sports Physical '
        'Therapy, 36(12), 911–919',
        'campos': [
            _campo('composite_pct', 'Score compuesto', '%', 50, 130, 1, '94.0', MAYOR),
            _campo('asym_ant_cm', 'Asimetría anterior', 'cm', 0, 15, 1, '2.0', MENOR, False),
        ],
        'baremos': {
            'composite_pct': {
                ('general', 'elite'):        [100, 94, 89, 84],
                ('general', 'profesional'):  [100, 94, 89, 84],
                ('general', 'semipro'):      [100, 94, 89, 84],
                ('general', 'amateur'):      [100, 94, 89, 84],
                ('sub_18', 'general'):       [100, 94, 89, 84],
                ('sub_17', 'general'):       [100, 94, 89, 84],
                ('sub_16', 'general'):       [100, 94, 89, 84],
                ('sub_15', 'general'):       [100, 94, 89, 84],
                ('sub_14', 'general'):       [100, 94, 89, 84],
                ('sub_12', 'general'):       [100, 94, 89, 84],
                ('general', 'general'):      [100, 94, 89, 84],
            },
            'asym_ant_cm': {
                ('general', 'elite'):        [1, 2, 3, 4],
                ('general', 'profesional'):  [1, 2, 3, 4],
                ('general', 'semipro'):      [1, 2, 3, 4],
                ('general', 'amateur'):      [1, 2, 3, 4],
                ('sub_18', 'general'):       [1, 2, 3, 4],
                ('sub_17', 'general'):       [1, 2, 3, 4],
                ('sub_16', 'general'):       [1, 2, 3, 4],
                ('sub_15', 'general'):       [1, 2, 3, 4],
                ('sub_14', 'general'):       [1, 2, 3, 4],
                ('sub_12', 'general'):       [1, 2, 3, 4],
                ('general', 'general'):      [1, 2, 3, 4],
            },
        },
    },

    'cabeceo_bangsbo': {
        'nombre': 'Cabeceo — Precisión y Distancia (Bangsbo)',
        'categoria': 'tecnico',
        'orden': 370,
        'icono': 'circle',
        'fuente': 'Bangsbo, J. (1994). Fitness Training in Football — A Scientific '
        'Approach. HO+Storm',
        'campos': [
            _campo('precision_score', 'Precisión', '/15', 0, 15, 0, '9', MAYOR),
            _campo('max_distance_m', 'Distancia máxima en salto', 'm', 2, 25, 1, '8.0', MAYOR, False),
        ],
        'baremos': {
            'precision_score': {
                ('general', 'elite'):        [12, 10, 8, 6],
                ('general', 'profesional'):  [12, 9, 7, 6],
                ('general', 'semipro'):      [12, 9, 7, 5],
                ('general', 'amateur'):      [12, 9, 7, 5],
                ('sub_18', 'general'):       [12, 9, 7, 5],
                ('sub_17', 'general'):       [12, 9, 6, 4],
                ('sub_16', 'general'):       [12, 8, 6, 4],
                ('sub_15', 'general'):       [11, 8, 5, 3],
                ('sub_14', 'general'):       [11, 8, 5, 3],
                ('sub_12', 'general'):       [11, 7, 4, 2],
                ('general', 'general'):      [12, 9, 7, 6],
            },
            'max_distance_m': {
                ('general', 'elite'):        [15.0, 10.9, 8.2, 5.4],
                ('general', 'profesional'):  [13.3, 9.7, 7.3, 4.8],
                ('general', 'semipro'):      [12.5, 9.1, 6.8, 4.5],
                ('general', 'amateur'):      [11.7, 8.5, 6.4, 4.2],
                ('sub_18', 'general'):       [11.0, 8.0, 6.0, 4.0],
                ('sub_17', 'general'):       [9.8, 7.2, 5.4, 3.6],
                ('sub_16', 'general'):       [8.9, 6.5, 4.9, 3.2],
                ('sub_15', 'general'):       [8.1, 5.9, 4.4, 2.9],
                ('sub_14', 'general'):       [7.7, 5.6, 4.2, 2.8],
                ('sub_12', 'general'):       [6.6, 4.8, 3.6, 2.4],
                ('general', 'general'):      [12.8, 9.3, 7.0, 4.6],
            },
        },
    },

    'conduccion_cambio_ritmo': {
        'nombre': 'Conducción con Cambio de Ritmo',
        'categoria': 'tecnico',
        'orden': 380,
        'icono': 'fast-forward',
        'fuente': 'Stølen, T. et al. (2005). Sports Medicine, 35(6), 501–536',
        'campos': [
            _campo('time_s', 'Tiempo total', 's', 4, 20, 2, '8.50', MENOR),
            _campo('balls_lost', 'Balones perdidos', 'balones', 0, 10, 0, '1', MENOR, False),
        ],
        'baremos': {
            'time_s': {
                ('general', 'elite'):        [7.0, 7.5, 8.3, 9.3],
                ('general', 'profesional'):  [7.39, 7.98, 8.83, 9.88],
                ('general', 'semipro'):      [7.62, 8.27, 9.15, 10.22],
                ('general', 'amateur'):      [7.94, 8.65, 9.57, 10.69],
                ('sub_18', 'general'):       [7.8, 8.5, 9.4, 10.5],
                ('sub_17', 'general'):       [8.37, 9.12, 10.09, 11.27],
                ('sub_16', 'general'):       [8.83, 9.63, 10.65, 11.89],
                ('sub_15', 'general'):       [9.32, 10.16, 11.23, 12.55],
                ('sub_14', 'general'):       [9.56, 10.41, 11.52, 12.87],
                ('sub_12', 'general'):       [10.29, 11.21, 12.4, 13.85],
                ('general', 'general'):      [7.43, 8.04, 8.89, 9.94],
            },
            'balls_lost': {
                ('general', 'elite'):        [0, 1, 2, 3],
                ('general', 'profesional'):  [0, 1, 2, 3],
                ('general', 'semipro'):      [0, 1, 2, 3],
                ('general', 'amateur'):      [0, 1, 2, 3],
                ('sub_18', 'general'):       [0, 1, 2, 3],
                ('sub_17', 'general'):       [0, 1, 2, 3],
                ('sub_16', 'general'):       [0, 1, 2, 3],
                ('sub_15', 'general'):       [0, 1, 2, 3],
                ('sub_14', 'general'):       [0, 1, 2, 3],
                ('sub_12', 'general'):       [0, 1, 2, 3],
                ('general', 'general'):      [0, 1, 2, 3],
            },
        },
    },

    'conduccion_vallas': {
        'nombre': 'Conducción con Vallas y Slalom',
        'categoria': 'tecnico',
        'orden': 390,
        'icono': 'grid',
        'fuente': 'Reilly, T., & Holmes, M. (1983). Physical Education Review, 6(1), '
        '64–71',
        'campos': [
            _campo('time_s', 'Tiempo total penalizado', 's', 6, 30, 2, '13.00', MENOR),
        ],
        'baremos': {
            'time_s': {
                ('general', 'elite'):        [8.47, 9.41, 10.54, 12.05],
                ('general', 'profesional'):  [9.0, 10.0, 11.2, 12.8],
                ('general', 'semipro'):      [10.34, 11.6, 12.96, 14.78],
                ('general', 'amateur'):      [11.71, 13.23, 14.76, 16.8],
                ('sub_18', 'general'):       [11.5, 13.0, 14.5, 16.5],
                ('sub_17', 'general'):       [12.34, 13.95, 15.56, 17.71],
                ('sub_16', 'general'):       [13.02, 14.72, 16.42, 18.69],
                ('sub_15', 'general'):       [13.74, 15.53, 17.33, 19.72],
                ('sub_14', 'general'):       [14.09, 15.93, 17.77, 20.22],
                ('sub_12', 'general'):       [15.17, 17.15, 19.13, 21.77],
                ('general', 'general'):      [9.24, 10.29, 11.52, 13.16],
            },
        },
    },

    'conduccion_circuito_30s': {
        'nombre': 'Conducción en Circuito Cerrado 30 s',
        'categoria': 'tecnico',
        'orden': 400,
        'icono': 'rotate-cw',
        'fuente': 'Impellizzeri, F.M. et al. (2008). Level of competition and '
        'soccer-specific fitness of under-17 players. Int. J. Sports '
        'Medicine, 29(7), 575–582',
        'campos': [
            _campo('laps', 'Vueltas en 30 s', 'vueltas', 0, 12, 1, '4.0', MAYOR),
            _campo('diff_direction', 'Diferencia entre sentidos', 'vueltas', 0, 5, 1, '0.5', MENOR, False),
        ],
        'baremos': {
            'laps': {
                ('general', 'elite'):        [6.0, 5.0, 4.0, 3.0],
                ('general', 'profesional'):  [5.5, 4.5, 3.5, 2.5],
                ('general', 'semipro'):      [5.2, 4.2, 3.2, 2.2],
                ('general', 'amateur'):      [4.9, 3.9, 2.9, 2.0],
                ('sub_18', 'general'):       [5.0, 4.0, 3.0, 2.0],
                ('sub_17', 'general'):       [4.7, 3.7, 2.8, 1.9],
                ('sub_16', 'general'):       [4.4, 3.5, 2.6, 1.8],
                ('sub_15', 'general'):       [4.2, 3.3, 2.5, 1.7],
                ('sub_14', 'general'):       [4.1, 3.3, 2.4, 1.6],
                ('sub_12', 'general'):       [3.8, 3.0, 2.3, 1.5],
                ('general', 'general'):      [5.4, 4.4, 3.4, 2.4],
            },
            'diff_direction': {
                ('general', 'elite'):        [0.2, 0.5, 1.0, 1.5],
                ('general', 'profesional'):  [0.2, 0.5, 1.0, 1.5],
                ('general', 'semipro'):      [0.2, 0.5, 1.0, 1.5],
                ('general', 'amateur'):      [0.2, 0.5, 1.0, 1.5],
                ('sub_18', 'general'):       [0.2, 0.5, 1.0, 1.5],
                ('sub_17', 'general'):       [0.2, 0.5, 1.0, 1.5],
                ('sub_16', 'general'):       [0.2, 0.5, 1.0, 1.5],
                ('sub_15', 'general'):       [0.2, 0.5, 1.0, 1.5],
                ('sub_14', 'general'):       [0.2, 0.5, 1.0, 1.5],
                ('sub_12', 'general'):       [0.2, 0.5, 1.0, 1.5],
                ('general', 'general'):      [0.2, 0.5, 1.0, 1.5],
            },
        },
    },

    'trapping_test': {
        'nombre': 'Control en Suelo — Trapping Test',
        'categoria': 'tecnico',
        'orden': 410,
        'icono': 'box',
        'fuente': 'Reilly, T., & Williams, A.M. (Eds.). (2003). Science and Soccer (2nd '
        'ed.). Routledge',
        'campos': [
            _campo('success_10', 'Controles exitosos', '/10', 0, 10, 0, '7', MAYOR),
        ],
        'baremos': {
            'success_10': {
                ('general', 'elite'):        [10, 9, 8, 6],
                ('general', 'profesional'):  [10, 9, 7, 5],
                ('general', 'semipro'):      [10, 8, 7, 5],
                ('general', 'amateur'):      [9, 8, 6, 5],
                ('sub_18', 'general'):       [9, 8, 6, 5],
                ('sub_17', 'general'):       [9, 7, 5, 4],
                ('sub_16', 'general'):       [9, 7, 5, 4],
                ('sub_15', 'general'):       [9, 7, 4, 3],
                ('sub_14', 'general'):       [9, 7, 4, 3],
                ('sub_12', 'general'):       [9, 6, 4, 3],
                ('general', 'general'):      [10, 9, 7, 5],
            },
        },
    },

    'dominio_balon_fifa': {
        'nombre': 'Dominio de Balón — 5 Superficies (FIFA)',
        'categoria': 'tecnico',
        'orden': 420,
        'icono': 'circle',
        'fuente': 'FIFA. (2014). Grassroots Football Manual — Technical Skill '
        'Assessment Protocols. Zurich: FIFA',
        'campos': [
            _campo('cycles', 'Ciclos completos en 60 s', 'ciclos', 0, 30, 0, '6', MAYOR),
            _campo('streak', 'Racha máxima de toques', 'toques', 0, 300, 0, '40', MAYOR, False),
        ],
        'baremos': {
            'cycles': {
                ('general', 'elite'):        [14, 10, 7, 5],
                ('general', 'profesional'):  [13, 9, 6, 4],
                ('general', 'semipro'):      [12, 8, 5, 4],
                ('general', 'amateur'):      [11, 7, 5, 3],
                ('sub_18', 'general'):       [11, 8, 5, 3],
                ('sub_17', 'general'):       [10, 6, 4, 3],
                ('sub_16', 'general'):       [9, 6, 3, 2],
                ('sub_15', 'general'):       [8, 5, 3, 2],
                ('sub_14', 'general'):       [8, 5, 3, 2],
                ('sub_12', 'general'):       [7, 5, 3, 2],
                ('general', 'general'):      [12, 9, 6, 4],
            },
            'streak': {
                ('general', 'elite'):        [100, 60, 40, 25],
                ('general', 'profesional'):  [89, 53, 36, 22],
                ('general', 'semipro'):      [83, 50, 33, 21],
                ('general', 'amateur'):      [78, 47, 31, 19],
                ('sub_18', 'general'):       [73, 44, 29, 18],
                ('sub_17', 'general'):       [66, 39, 26, 16],
                ('sub_16', 'general'):       [60, 36, 24, 15],
                ('sub_15', 'general'):       [54, 32, 22, 14],
                ('sub_14', 'general'):       [51, 31, 20, 13],
                ('sub_12', 'general'):       [44, 27, 18, 11],
                ('general', 'general'):      [85, 51, 34, 21],
            },
        },
    },

    'dribbling_fpf': {
        'nombre': 'Dribbling Speed Test (FPF)',
        'categoria': 'tecnico',
        'orden': 430,
        'icono': 'shuffle',
        'fuente': 'Federação Portuguesa de Futebol — FPF. (2017). Bateria de testes '
        'técnicos para futebol formativo. Lisboa: FPF',
        'campos': [
            _campo('time_s', 'Tiempo total', 's', 5, 25, 2, '9.20', MENOR),
            _campo('time_nd', 'Tiempo pierna no dominante', 's', 5, 25, 2, '9.80', MENOR, False),
        ],
        'baremos': {
            'time_s': {
                ('general', 'elite'):        [7.5, 8.0, 8.5, 9.4],
                ('general', 'profesional'):  [8.0, 8.5, 9.0, 9.8],
                ('general', 'semipro'):      [8.4, 8.8, 9.4, 10.2],
                ('general', 'amateur'):      [8.7, 9.2, 9.8, 10.8],
                ('sub_18', 'general'):       [8.5, 9.0, 9.7, 10.7],
                ('sub_17', 'general'):       [9.0, 9.7, 10.5, 11.5],
                ('sub_16', 'general'):       [9.49, 10.24, 10.99, 11.99],
                ('sub_15', 'general'):       [10.0, 10.8, 11.5, 12.5],
                ('sub_14', 'general'):       [10.25, 11.07, 11.79, 12.82],
                ('sub_12', 'general'):       [11.04, 11.92, 12.69, 13.8],
                ('general', 'general'):      [8.05, 8.56, 9.06, 9.87],
            },
            'time_nd': {
                ('general', 'elite'):        [7.97, 8.41, 9.03, 9.91],
                ('general', 'profesional'):  [8.46, 8.93, 9.59, 10.53],
                ('general', 'semipro'):      [8.76, 9.25, 9.93, 10.91],
                ('general', 'amateur'):      [9.16, 9.67, 10.38, 11.4],
                ('sub_18', 'general'):       [9.0, 9.5, 10.2, 11.2],
                ('sub_17', 'general'):       [9.66, 10.2, 10.95, 12.02],
                ('sub_16', 'general'):       [10.19, 10.76, 11.55, 12.68],
                ('sub_15', 'general'):       [10.75, 11.35, 12.19, 13.38],
                ('sub_14', 'general'):       [11.03, 11.64, 12.5, 13.72],
                ('sub_12', 'general'):       [11.87, 12.53, 13.46, 14.77],
                ('general', 'general'):      [8.52, 8.99, 9.66, 10.6],
            },
        },
    },

    'golpeo_porteria_ali': {
        'nombre': 'Golpeo a Portería (Ali — Loughborough)',
        'categoria': 'tecnico',
        'orden': 440,
        'icono': 'target',
        'fuente': 'Ali, A., Williams, C., Hulse, M. et al. (2007). Journal of Sports '
        'Sciences, 25(13), 1461–1470',
        'campos': [
            _campo('score', 'Puntuación', 'pts', 0, 30, 0, '18', MAYOR),
            _campo('velocity_kmh', 'Velocidad de disparo', 'km/h', 30, 140, 1, '85.0', MAYOR, False),
        ],
        'baremos': {
            'score': {
                ('general', 'elite'):        [28, 26, 22, 18],
                ('general', 'profesional'):  [25, 22, 18, 15],
                ('general', 'semipro'):      [23, 20, 17, 14],
                ('general', 'amateur'):      [22, 19, 16, 13],
                ('sub_18', 'general'):       [21, 18, 15, 12],
                ('sub_17', 'general'):       [18, 15, 12, 9],
                ('sub_16', 'general'):       [16, 13, 10, 7],
                ('sub_15', 'general'):       [15, 12, 9, 6],
                ('sub_14', 'general'):       [14, 11, 9, 6],
                ('sub_12', 'general'):       [12, 10, 7, 5],
                ('general', 'general'):      [24, 21, 17, 14],
            },
            'velocity_kmh': {
                ('general', 'elite'):        [110.0, 100.0, 92.0, 84.0],
                ('general', 'profesional'):  [103.5, 94.1, 86.6, 79.1],
                ('general', 'semipro'):      [100.0, 90.9, 83.6, 76.4],
                ('general', 'amateur'):      [95.7, 87.0, 80.0, 73.0],
                ('sub_18', 'general'):       [97.4, 88.5, 81.4, 74.4],
                ('sub_17', 'general'):       [90.7, 82.5, 75.9, 69.3],
                ('sub_16', 'general'):       [86.0, 78.2, 71.9, 65.7],
                ('sub_15', 'general'):       [81.5, 74.1, 68.1, 62.2],
                ('sub_14', 'general'):       [79.5, 72.2, 66.5, 60.7],
                ('sub_12', 'general'):       [73.8, 67.1, 61.7, 56.4],
                ('general', 'general'):      [102.8, 93.5, 86.0, 78.5],
            },
        },
    },

    'juego_aereo': {
        'nombre': 'Juego Aéreo — Duelos de Cabeza',
        'categoria': 'tecnico',
        'orden': 450,
        'icono': 'arrow-up',
        'fuente': 'Bangsbo, J. (1994). Fitness Training in Football. HO+Storm',
        'campos': [
            _campo('wins_opp', 'Duelos ganados con oponente', '/5', 0, 5, 0, '3', MAYOR),
            _campo('wins_no_opp', 'Duelos ganados sin oponente', '/5', 0, 5, 0, '4', MAYOR, False),
        ],
        'baremos': {
            'wins_opp': {
                ('general', 'elite'):        [5, 4, 3, 2],
                ('general', 'profesional'):  [5, 4, 3, 2],
                ('general', 'semipro'):      [4, 3, 2, 1],
                ('general', 'amateur'):      [4, 3, 2, 1],
                ('sub_18', 'general'):       [4, 3, 2, 1],
                ('sub_17', 'general'):       [4, 3, 2, 1],
                ('sub_16', 'general'):       [4, 3, 2, 0],
                ('sub_15', 'general'):       [4, 3, 1, 0],
                ('sub_14', 'general'):       [4, 3, 1, 0],
                ('sub_12', 'general'):       [4, 2, 1, 0],
                ('general', 'general'):      [4, 3, 2, 1],
            },
            'wins_no_opp': {
                ('general', 'elite'):        [5, 4, 3, 2],
                ('general', 'profesional'):  [5, 4, 3, 2],
                ('general', 'semipro'):      [5, 4, 3, 2],
                ('general', 'amateur'):      [5, 4, 3, 2],
                ('sub_18', 'general'):       [5, 4, 3, 2],
                ('sub_17', 'general'):       [5, 4, 3, 2],
                ('sub_16', 'general'):       [5, 4, 3, 2],
                ('sub_15', 'general'):       [5, 4, 3, 1],
                ('sub_14', 'general'):       [5, 4, 3, 1],
                ('sub_12', 'general'):       [5, 4, 2, 1],
                ('general', 'general'):      [5, 4, 3, 2],
            },
        },
    },

    'pared_primer_toque': {
        'nombre': 'Pared — Pases de Primer Toque',
        'categoria': 'tecnico',
        'orden': 460,
        'icono': 'repeat',
        'fuente': 'Grehaigne, J.F., Bouthier, D., & David, B. (1997). Dynamic-system '
        'analysis of opponent relationships in collective actions in soccer. '
        'Journal of Sports Sciences, 15(2), 137–149',
        'campos': [
            _campo('hits_30s', 'Toques precisos en 30 s', 'toques', 0, 60, 0, '22', MAYOR),
        ],
        'baremos': {
            'hits_30s': {
                ('general', 'elite'):        [42, 36, 30, 23],
                ('general', 'profesional'):  [40, 34, 28, 22],
                ('general', 'semipro'):      [31, 25, 20, 15],
                ('general', 'amateur'):      [26, 20, 15, 11],
                ('sub_18', 'general'):       [26, 20, 15, 11],
                ('sub_17', 'general'):       [24, 19, 14, 10],
                ('sub_16', 'general'):       [23, 18, 13, 10],
                ('sub_15', 'general'):       [22, 17, 13, 9],
                ('sub_14', 'general'):       [21, 16, 12, 9],
                ('sub_12', 'general'):       [20, 15, 11, 8],
                ('general', 'general'):      [38, 32, 26, 20],
            },
        },
    },

    'pase_largo_precision': {
        'nombre': 'Pase Largo — Precisión y Distancia',
        'categoria': 'tecnico',
        'orden': 470,
        'icono': 'send',
        'fuente': 'Haaland, E., & Hoff, J. (2003). Non-dominant leg training improves '
        'the bilateral motor performance of soccer players. Scandinavian '
        'Journal of Medicine & Science in Sports, 13(3), 179–184',
        'campos': [
            _campo('score', 'Puntuación', '/27', 0, 27, 0, '16', MAYOR),
            _campo('asym', 'Asimetría entre piernas', 'pts', 0, 27, 0, '3', MENOR, False),
        ],
        'baremos': {
            'score': {
                ('general', 'elite'):        [23, 18, 15, 11],
                ('general', 'profesional'):  [23, 17, 14, 10],
                ('general', 'semipro'):      [22, 17, 13, 10],
                ('general', 'amateur'):      [22, 17, 13, 9],
                ('sub_18', 'general'):       [22, 17, 13, 9],
                ('sub_17', 'general'):       [22, 16, 12, 8],
                ('sub_16', 'general'):       [22, 15, 11, 7],
                ('sub_15', 'general'):       [21, 15, 10, 6],
                ('sub_14', 'general'):       [21, 14, 10, 5],
                ('sub_12', 'general'):       [21, 13, 9, 4],
                ('general', 'general'):      [23, 17, 14, 10],
            },
            'asym': {
                ('general', 'elite'):        [1, 2, 3, 5],
                ('general', 'profesional'):  [1, 2, 3, 5],
                ('general', 'semipro'):      [1, 2, 3, 5],
                ('general', 'amateur'):      [1, 2, 3, 5],
                ('sub_18', 'general'):       [1, 2, 3, 5],
                ('sub_17', 'general'):       [1, 2, 3, 5],
                ('sub_16', 'general'):       [1, 2, 3, 5],
                ('sub_15', 'general'):       [1, 2, 3, 5],
                ('sub_14', 'general'):       [1, 2, 3, 5],
                ('sub_12', 'general'):       [1, 2, 3, 5],
                ('general', 'general'):      [1, 2, 3, 5],
            },
        },
    },

    'penalti_test': {
        'nombre': 'Penalti — Velocidad, Precisión y Presión',
        'categoria': 'tecnico',
        'orden': 480,
        'icono': 'target',
        'fuente': 'Wilson, M.R. et al. (2009). Anxiety, attentional control, and '
        'performance impairment in penalty kicks. J. Sport and Exercise '
        'Psychology, 31(6), 761–775',
        'campos': [
            _campo('score', 'Puntuación', '/30', 0, 30, 0, '20', MAYOR),
        ],
        'baremos': {
            'score': {
                ('general', 'elite'):        [28, 26, 23, 20],
                ('general', 'profesional'):  [26, 23, 20, 17],
                ('general', 'semipro'):      [25, 22, 19, 16],
                ('general', 'amateur'):      [23, 20, 17, 14],
                ('sub_18', 'general'):       [22, 19, 16, 13],
                ('sub_17', 'general'):       [20, 17, 14, 11],
                ('sub_16', 'general'):       [18, 15, 12, 9],
                ('sub_15', 'general'):       [17, 14, 11, 8],
                ('sub_14', 'general'):       [16, 13, 10, 8],
                ('sub_12', 'general'):       [14, 11, 9, 7],
                ('general', 'general'):      [25, 22, 19, 16],
            },
        },
    },

    'recepcion_pivot': {
        'nombre': 'Recepción en Movimiento — Pivot',
        'categoria': 'tecnico',
        'orden': 490,
        'icono': 'rotate-ccw',
        'fuente': 'Dellal, A. et al. (2011). Comparison of technical performances of '
        'players in the top five European professional soccer league '
        'tournaments. Journal of Sports Medicine and Physical Fitness, 51(4), '
        '690–700',
        'campos': [
            _campo('correct', 'Controles orientados', '/10', 0, 10, 0, '7', MAYOR),
            _campo('orientation_s', 'Tiempo de orientación', 's', 0.3, 6, 2, '1.50', MENOR, False),
        ],
        'baremos': {
            'correct': {
                ('general', 'elite'):        [9, 8, 6, 5],
                ('general', 'profesional'):  [9, 7, 6, 5],
                ('general', 'semipro'):      [9, 7, 5, 4],
                ('general', 'amateur'):      [9, 7, 5, 4],
                ('sub_18', 'general'):       [9, 7, 5, 4],
                ('sub_17', 'general'):       [9, 7, 5, 4],
                ('sub_16', 'general'):       [9, 7, 5, 4],
                ('sub_15', 'general'):       [9, 7, 4, 3],
                ('sub_14', 'general'):       [9, 7, 4, 3],
                ('sub_12', 'general'):       [9, 6, 4, 3],
                ('general', 'general'):      [9, 7, 6, 5],
            },
            'orientation_s': {
                ('general', 'elite'):        [0.99, 1.24, 1.57, 1.98],
                ('general', 'profesional'):  [1.05, 1.31, 1.66, 2.1],
                ('general', 'semipro'):      [1.09, 1.36, 1.72, 2.18],
                ('general', 'amateur'):      [1.14, 1.42, 1.8, 2.28],
                ('sub_18', 'general'):       [1.12, 1.4, 1.77, 2.24],
                ('sub_17', 'general'):       [1.2, 1.5, 1.9, 2.4],
                ('sub_16', 'general'):       [1.27, 1.58, 2.0, 2.53],
                ('sub_15', 'general'):       [1.34, 1.67, 2.12, 2.67],
                ('sub_14', 'general'):       [1.37, 1.71, 2.17, 2.74],
                ('sub_12', 'general'):       [1.47, 1.84, 2.34, 2.95],
                ('general', 'general'):      [1.06, 1.32, 1.68, 2.12],
            },
        },
    },

    'recepcion_orientada': {
        'nombre': 'Recepción y Control Orientado',
        'categoria': 'tecnico',
        'orden': 500,
        'icono': 'corner-down-right',
        'fuente': 'Castagna, C. et al. (2006). J. Strength and Conditioning Research, '
        '20(2), 320–325',
        'campos': [
            _campo('success', 'Controles exitosos', '/10', 0, 10, 0, '7', MAYOR),
            _campo('reaction_s', 'Tiempo de reacción', 's', 0.3, 5, 2, '1.10', MENOR, False),
        ],
        'baremos': {
            'success': {
                ('general', 'elite'):        [9, 8, 7, 6],
                ('general', 'profesional'):  [9, 8, 6, 5],
                ('general', 'semipro'):      [9, 8, 6, 5],
                ('general', 'amateur'):      [9, 8, 6, 5],
                ('sub_18', 'general'):       [9, 8, 6, 5],
                ('sub_17', 'general'):       [9, 8, 6, 5],
                ('sub_16', 'general'):       [9, 8, 6, 5],
                ('sub_15', 'general'):       [9, 8, 6, 4],
                ('sub_14', 'general'):       [9, 8, 5, 4],
                ('sub_12', 'general'):       [9, 8, 5, 4],
                ('general', 'general'):      [9, 8, 6, 5],
            },
            'reaction_s': {
                ('general', 'elite'):        [0.66, 0.91, 1.15, 1.48],
                ('general', 'profesional'):  [0.7, 0.96, 1.23, 1.58],
                ('general', 'semipro'):      [0.73, 1.0, 1.27, 1.63],
                ('general', 'amateur'):      [0.76, 1.04, 1.33, 1.71],
                ('sub_18', 'general'):       [0.75, 1.02, 1.3, 1.68],
                ('sub_17', 'general'):       [0.8, 1.1, 1.4, 1.8],
                ('sub_16', 'general'):       [0.84, 1.16, 1.48, 1.9],
                ('sub_15', 'general'):       [0.89, 1.22, 1.56, 2.0],
                ('sub_14', 'general'):       [0.91, 1.26, 1.6, 2.05],
                ('sub_12', 'general'):       [0.98, 1.35, 1.72, 2.21],
                ('general', 'general'):      [0.71, 0.97, 1.24, 1.59],
            },
        },
    },

    'regate_1vs0': {
        'nombre': 'Regate 1vs0 con Finta Obligatoria',
        'categoria': 'tecnico',
        'orden': 510,
        'icono': 'corner-up-right',
        'fuente': 'Rampinini, E. et al. (2009). J. Science and Medicine in Sport, '
        '12(1), 227–233',
        'campos': [
            _campo('time_s', 'Tiempo penalizado', 's', 5, 25, 2, '10.00', MENOR),
            _campo('finta_quality', 'Calidad de la finta', '1-3', 1, 3, 0, '2', MAYOR, False),
        ],
        'baremos': {
            'time_s': {
                ('general', 'elite'):        [7.79, 8.85, 10.0, 11.51],
                ('general', 'profesional'):  [8.28, 9.4, 10.63, 12.23],
                ('general', 'semipro'):      [8.57, 9.74, 11.0, 12.66],
                ('general', 'amateur'):      [8.96, 10.18, 11.5, 13.23],
                ('sub_18', 'general'):       [8.8, 10.0, 11.3, 13.0],
                ('sub_17', 'general'):       [9.44, 10.73, 12.13, 13.95],
                ('sub_16', 'general'):       [9.97, 11.32, 12.8, 14.72],
                ('sub_15', 'general'):       [10.52, 11.95, 13.5, 15.53],
                ('sub_14', 'general'):       [10.78, 12.25, 13.85, 15.93],
                ('sub_12', 'general'):       [11.61, 13.19, 14.91, 17.15],
                ('general', 'general'):      [8.33, 9.47, 10.7, 12.31],
            },
        },
    },

    'saque_banda': {
        'nombre': 'Saque de Banda — Distancia y Precisión',
        'categoria': 'tecnico',
        'orden': 520,
        'icono': 'arrow-right',
        'fuente': 'Kollath, E., & Quade, K. (1993). Measurement of sprinting speed of '
        'professional and amateur soccer players. In Science and Football II. '
        'E&FN Spon',
        'campos': [
            _campo('max_distance_m', 'Distancia máxima', 'm', 5, 50, 1, '22.0', MAYOR),
            _campo('accuracy_pct', 'Precisión zona media', '%', 0, 100, 0, '80', MAYOR, False),
        ],
        'baremos': {
            'max_distance_m': {
                ('general', 'elite'):        [38.2, 33.8, 28.1, 22.5],
                ('general', 'profesional'):  [34.0, 30.0, 25.0, 20.0],
                ('general', 'semipro'):      [31.1, 26.2, 21.5, 16.8],
                ('general', 'amateur'):      [28.2, 22.6, 18.3, 14.0],
                ('sub_18', 'general'):       [26.0, 20.0, 16.0, 12.0],
                ('sub_17', 'general'):       [23.3, 17.9, 14.3, 10.7],
                ('sub_16', 'general'):       [21.1, 16.2, 13.0, 9.7],
                ('sub_15', 'general'):       [19.2, 14.7, 11.8, 8.8],
                ('sub_14', 'general'):       [18.1, 13.9, 11.2, 8.4],
                ('sub_12', 'general'):       [15.7, 12.1, 9.7, 7.2],
                ('general', 'general'):      [32.0, 27.4, 22.6, 17.8],
            },
            'accuracy_pct': {
                ('general', 'elite'):        [95, 81, 67, 53],
                ('general', 'profesional'):  [95, 80, 65, 50],
                ('general', 'semipro'):      [95, 79, 64, 48],
                ('general', 'amateur'):      [95, 78, 62, 46],
                ('sub_18', 'general'):       [95, 79, 63, 47],
                ('sub_17', 'general'):       [94, 77, 60, 43],
                ('sub_16', 'general'):       [94, 76, 58, 40],
                ('sub_15', 'general'):       [94, 75, 56, 36],
                ('sub_14', 'general'):       [93, 74, 54, 35],
                ('sub_12', 'general'):       [93, 72, 51, 30],
                ('general', 'general'):      [95, 80, 65, 50],
            },
        },
    },

    'tiro_potencia_radar': {
        'nombre': 'Tiro con Potencia (Radar)',
        'categoria': 'tecnico',
        'orden': 530,
        'icono': 'zap',
        'fuente': 'Levanon, J., & Dapena, J. (1998). Comparison of the kinematics of '
        'the full-instep and pass kicks in soccer. Medicine & Science in '
        'Sports & Exercise, 30(6), 917–927',
        'campos': [
            _campo('vmax_kmh', 'Velocidad máxima', 'km/h', 30, 150, 1, '85.0', MAYOR),
            _campo('vmean_kmh', 'Velocidad media', 'km/h', 25, 140, 1, '78.0', MAYOR, False),
            _campo('diff_legs', 'Diferencial entre piernas', 'km/h', 0, 60, 1, '15.0', MENOR, False),
        ],
        'baremos': {
            'vmax_kmh': {
                ('general', 'elite'):        [120.0, 105.0, 95.0, 88.0],
                ('general', 'profesional'):  [102.9, 90.6, 81.6, 73.9],
                ('general', 'semipro'):      [94.2, 83.2, 74.8, 66.9],
                ('general', 'amateur'):      [86.4, 76.6, 68.8, 60.9],
                ('sub_18', 'general'):       [88.0, 78.0, 70.0, 62.0],
                ('sub_17', 'general'):       [82.0, 72.7, 65.2, 57.8],
                ('sub_16', 'general'):       [77.7, 68.9, 61.8, 54.7],
                ('sub_15', 'general'):       [73.6, 65.3, 58.6, 51.9],
                ('sub_14', 'general'):       [71.8, 63.7, 57.1, 50.6],
                ('sub_12', 'general'):       [66.7, 59.1, 53.1, 47.0],
                ('general', 'general'):      [101.1, 89.1, 80.3, 72.5],
            },
            'vmean_kmh': {
                ('general', 'elite'):        [105.0, 95.0, 85.0, 78.0],
                ('general', 'profesional'):  [98.8, 89.4, 80.0, 73.4],
                ('general', 'semipro'):      [95.5, 86.4, 77.3, 70.9],
                ('general', 'amateur'):      [91.3, 82.6, 73.9, 67.8],
                ('sub_18', 'general'):       [92.9, 84.1, 75.2, 69.0],
                ('sub_17', 'general'):       [86.6, 78.4, 70.1, 64.3],
                ('sub_16', 'general'):       [82.1, 74.3, 66.4, 61.0],
                ('sub_15', 'general'):       [77.8, 70.4, 63.0, 57.8],
                ('sub_14', 'general'):       [75.9, 68.6, 61.4, 56.4],
                ('sub_12', 'general'):       [70.5, 63.7, 57.0, 52.3],
                ('general', 'general'):      [98.2, 88.8, 79.5, 72.9],
            },
            'diff_legs': {
                ('general', 'elite'):        [8, 14, 20, 26],
                ('general', 'profesional'):  [8, 14, 20, 26],
                ('general', 'semipro'):      [8, 14, 20, 26],
                ('general', 'amateur'):      [8, 14, 20, 26],
                ('sub_18', 'general'):       [8, 14, 20, 26],
                ('sub_17', 'general'):       [8, 14, 20, 26],
                ('sub_16', 'general'):       [8, 14, 20, 26],
                ('sub_15', 'general'):       [8, 14, 20, 26],
                ('sub_14', 'general'):       [8, 14, 20, 26],
                ('sub_12', 'general'):       [8, 14, 20, 26],
                ('general', 'general'):      [8, 14, 20, 26],
            },
        },
    },

    'tecnica_bajo_fatiga': {
        'nombre': 'Técnica Bajo Fatiga (FTT)',
        'categoria': 'tecnico',
        'orden': 540,
        'icono': 'battery-low',
        'fuente': 'Rampinini, E., Impellizzeri, F.M., Castagna, C. et al. (2008). '
        'Technical performance during soccer matches of the Italian Serie A '
        'league. J. Science and Medicine in Sport, 12(1), 179–184',
        'campos': [
            _campo('decay_pct', 'Deterioro técnico', '%', 0, 80, 1, '12.0', MENOR),
            _campo('score_pre', 'Score técnico pre-fatiga', 'pts', 0, 100, 1, '80.0', MAYOR, False),
            _campo('score_post', 'Score técnico post-fatiga', 'pts', 0, 100, 1, '70.0', MAYOR, False),
        ],
        'baremos': {
            'decay_pct': {
                ('general', 'elite'):        [7, 12, 20, 26],
                ('general', 'profesional'):  [7, 12, 20, 26],
                ('general', 'semipro'):      [7, 12, 20, 26],
                ('general', 'amateur'):      [7, 12, 20, 26],
                ('sub_18', 'general'):       [7, 12, 20, 26],
                ('sub_17', 'general'):       [7, 12, 20, 26],
                ('sub_16', 'general'):       [7, 12, 20, 26],
                ('sub_15', 'general'):       [7, 12, 20, 26],
                ('sub_14', 'general'):       [7, 12, 20, 26],
                ('sub_12', 'general'):       [7, 12, 20, 26],
                ('general', 'general'):      [7, 12, 20, 26],
            },
        },
    },

    'conduccion_recta': {
        'nombre': 'Velocidad de Conducción Línea Recta',
        'categoria': 'tecnico',
        'orden': 550,
        'icono': 'play',
        'fuente': 'Reilly, T., & Holmes, M. (1983). Physical Education Review, 6(1), '
        '64–71',
        'campos': [
            _campo('dribble_30m', 'Conducción 30 m', 's', 3, 15, 2, '5.40', MENOR),
            _campo('diff_sprint', 'Diferencial vs sprint libre', 's', 0, 5, 2, '0.50', MENOR, False),
        ],
        'baremos': {
            'dribble_30m': {
                ('general', 'elite'):        [5.0, 5.2, 5.6, 6.2],
                ('general', 'profesional'):  [5.31, 5.52, 5.95, 6.59],
                ('general', 'semipro'):      [5.5, 5.72, 6.16, 6.82],
                ('general', 'amateur'):      [5.75, 5.98, 6.44, 7.13],
                ('sub_18', 'general'):       [5.65, 5.87, 6.33, 7.0],
                ('sub_17', 'general'):       [6.06, 6.3, 6.79, 7.52],
                ('sub_16', 'general'):       [6.4, 6.65, 7.16, 7.93],
                ('sub_15', 'general'):       [6.75, 7.02, 7.56, 8.37],
                ('sub_14', 'general'):       [6.92, 7.2, 7.75, 8.58],
                ('sub_12', 'general'):       [7.45, 7.75, 8.35, 9.24],
                ('general', 'general'):      [5.35, 5.56, 5.99, 6.63],
            },
            'diff_sprint': {
                ('general', 'elite'):        [0.3, 0.5, 0.8, 1.1],
                ('general', 'profesional'):  [0.3, 0.5, 0.8, 1.1],
                ('general', 'semipro'):      [0.3, 0.5, 0.8, 1.1],
                ('general', 'amateur'):      [0.3, 0.5, 0.8, 1.1],
                ('sub_18', 'general'):       [0.3, 0.5, 0.8, 1.1],
                ('sub_17', 'general'):       [0.3, 0.5, 0.8, 1.1],
                ('sub_16', 'general'):       [0.3, 0.5, 0.8, 1.1],
                ('sub_15', 'general'):       [0.3, 0.5, 0.8, 1.1],
                ('sub_14', 'general'):       [0.3, 0.5, 0.8, 1.1],
                ('sub_12', 'general'):       [0.3, 0.5, 0.8, 1.1],
                ('general', 'general'):      [0.3, 0.5, 0.8, 1.1],
            },
        },
    }
}


# El catálogo que ve la app: primero las del MVP, luego las añadidas, y al
# final las avaladas de la biblioteca.
CATALOGO = {**_MVP, **_EXTRA, **_BIBLIOTECA_TESTS}

# Qué pruebas venían de la app original. La pantalla las marca para que se
# distingan de las añadidas.
CLAVES_MVP = set(_MVP)

# ─── La ficha larga de las avaladas ─────────────────────────────────────────
#  Objetivo, material, protocolo detallado, variables, valores normativos y
#  bibliografía de las 40. Vive aparte porque son 38 KB de texto y aquí
#  taparían los baremos.
#
#  Se fusiona con `setdefault` A PROPÓSITO: las trece que venían del MVP
#  conservan su descripción y su protocolo tal cual. El entrenador ya sabe cómo
#  se toma cada una y cambiarle el texto le obliga a releerlo todo.
from . import tests_biblioteca  # noqa: E402

for _clave, _ficha in tests_biblioteca.BIBLIOTECA.items():
    _t = CATALOGO.get(_clave)
    if not _t:
        continue
    for _k, _v in _ficha.items():
        _t.setdefault(_k, _v)
    _t['avalado'] = True

# Las que tienen protocolo y bibliografía publicados. La biblioteca las muestra
# aparte y la pantalla les pone la insignia.
CLAVES_AVALADAS = set(tests_biblioteca.BIBLIOTECA)

# ─── La ficha larga de las 18 restantes ─────────────────────────────────────
#  El Cooper, la plancha, las dominadas, los perfiles de observación… tenían
#  una línea de protocolo y nada más: la ficha salía vacía y quien no conocía
#  la prueba no tenía de dónde agarrarse.
#
#  Se fusiona igual que la biblioteca, con setdefault, pero SIN marcarlas como
#  avaladas: el texto lo escribimos nosotros a partir del protocolo estándar y
#  la insignia se queda para las que tienen protocolo publicado.
from . import tests_fichas_propias  # noqa: E402

for _clave, _ficha in tests_fichas_propias.FICHAS_PROPIAS.items():
    _t = CATALOGO.get(_clave)
    if not _t:
        continue
    for _k, _v in _ficha.items():
        _t.setdefault(_k, _v)


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
    # Las de conducción de la biblioteca son el mismo caso: se puntúan con el
    # cronómetro, así que reparten igual que la de conos. Dejarlas en técnica
    # pura haría que dos pruebas casi iguales movieran atributos distintos.
    'dribbling_fpf': {'tecnica': 0.7, 'fisico': 0.3},
    'conduccion_vallas': {'tecnica': 0.7, 'fisico': 0.3},
    'conduccion_cambio_ritmo': {'tecnica': 0.7, 'fisico': 0.3},
    'conduccion_circuito_30s': {'tecnica': 0.7, 'fisico': 0.3},
    'regate_1vs0': {'tecnica': 0.7, 'fisico': 0.3},
    # Esta es directamente un sprint con balón: manda lo físico.
    'conduccion_recta': {'tecnica': 0.5, 'fisico': 0.5},
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


# ═══════════════════════════════════════════════════════════════════════════
#  LA TABLA DE RANGOS DE LA FICHA
# ═══════════════════════════════════════════════════════════════════════════
#  Los once contextos en el orden en que se leen: primero el adulto de mejor a
#  peor nivel y luego las categorías de mayor a menor edad. Cada uno lleva dos
#  etiquetas porque así lo enseña la app —«Juvenil inicial» arriba y «Sub-15»
#  debajo—: el entrenador piensa en categorías, pero el baremo compara contra
#  un nivel competitivo y conviene que vea los dos.
CONTEXTOS_BAREMO = [
    (('general', 'elite'),       'Élite',            'Adulto'),
    (('general', 'profesional'), 'Profesional',      'Adulto'),
    (('general', 'semipro'),     'Semiprofesional',  'Adulto'),
    (('general', 'amateur'),     'Amateur',          'Adulto'),
    (('sub_18', 'general'),      'Juvenil avanzado', 'Sub-18'),
    (('sub_17', 'general'),      'Juvenil',          'Sub-17'),
    (('sub_16', 'general'),      'Juvenil',          'Sub-16'),
    (('sub_15', 'general'),      'Juvenil inicial',  'Sub-15'),
    (('sub_14', 'general'),      'Formativo',        'Sub-14'),
    (('sub_12', 'general'),      'Escuela',          'Sub-12'),
    (('general', 'general'),     'General',          'Sin contexto'),
]


def tabla_baremos(clave_test, campo, categoria_edad='general', nivel='general'):
    """Las filas de «Rangos esperados por nivel» para la ficha de una prueba.

    Solo devuelve los contextos que esa prueba tiene definidos: si una solo
    trae el de respaldo, se enseña una fila y no diez vacías.

    La fila que le toca al equipo va marcada con `actual`. Se resuelve con el
    mismo `baremo_para` que usa la puntuación —y no comparando claves a
    ojo— para que lo resaltado sea exactamente contra lo que se va a medir,
    incluida la caída hacia atrás cuando el contexto exacto no existe.
    """
    tabla = (CATALOGO.get(clave_test) or {}).get('baremos', {}).get(campo)
    if not tabla:
        return []
    usado = baremo_para(clave_test, campo, categoria_edad, nivel)
    par_usado = (usado['edad'], usado['nivel']) if usado else None
    filas = []
    for par, et_nivel, et_edad in CONTEXTOS_BAREMO:
        cortes = tabla.get(par)
        if not cortes:
            continue
        filas.append({'nivel': et_nivel, 'edad': et_edad, 'cortes': cortes,
                      'actual': par == par_usado})
    return filas


def campos_con_baremo(t):
    """Los campos de una prueba que se pueden puntuar, el principal primero."""
    baremos = (t or {}).get('baremos') or {}
    return [c for c in (t.get('campos') or []) if c['clave'] in baremos]


def categoria_por_edad(anio_nacimiento, hoy=None, fecha_nacimiento=None):
    """La categoría con la que se compara un jugador.

    Acepta la FECHA completa —y entonces la edad es exacta, con el cumpleaños
    descontado— o solo el año, que es lo único que se guardaba antes. Con el
    año a secas un chico nacido en diciembre figura un año mayor de lo que es
    desde el 1 de enero, y eso lo mueve de categoría entera.
    """
    from datetime import date
    hoy = hoy or date.today()

    f = None
    if fecha_nacimiento:
        try:
            from datetime import datetime
            f = datetime.fromisoformat(str(fecha_nacimiento)[:19]).date()
        except (TypeError, ValueError):
            try:
                from datetime import datetime
                f = datetime.strptime(str(fecha_nacimiento)[:10], '%Y-%m-%d').date()
            except (TypeError, ValueError):
                f = None
    if f:
        edad = max(0, hoy.year - f.year - ((hoy.month, hoy.day) < (f.month, f.day)))
    else:
        if not anio_nacimiento:
            return 'general'
        try:
            edad = hoy.year - int(anio_nacimiento)
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
