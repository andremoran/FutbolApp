# -*- coding: utf-8 -*-
"""Fase 2 — genera el bloque C del catálogo: las 40 pruebas de la biblioteca.

De las 40, trece ya estaban en el catálogo web midiendo exactamente lo mismo
(Yo-Yo, CMJ, T-Test, LSPT...). Esas NO se duplican: se enriquecen en su sitio
con el texto largo de la biblioteca (objetivo, material, protocolo detallado,
variables, normativa y bibliografía) y se marcan como avaladas. Sus campos y
sus baremos no se tocan — quien ya cargó marcas con ellas las sigue leyendo
igual.

Las 27 restantes se añaden nuevas. El problema de esas 27 es que la biblioteca
trae el valor normativo como texto suelto («Bueno sub-18: < 13 s. Referencia
profesional: < 10 s») y el catálogo necesita cuatro umbrales en once contextos.
Inventar 27 × campos × 11 × 4 números sería precisión fingida, así que:

  1. De cada prueba se toman los puntos normativos que la biblioteca SÍ publica,
     cada uno con el contexto al que pertenece.
  2. Cada punto se retroproyecta al contexto de referencia dividiéndolo por el
     factor de la curva medida en `_curva_biblioteca.py`.
  3. Si hay varios puntos se promedian en media geométrica — así se usan todos
     los datos publicados en vez de descartar los que no encajan.
  4. Ese valor de referencia se vuelve a proyectar a los once contextos.

Cuatro de las 27 (1RM, Dribbling FPF, Golpeo de Ali y Penalti) ya tienen baremo
real en `test_reference_ranges` para su campo principal. Ahí no se genera nada:
se copian los siete contextos publicados y solo se derivan los cuatro que el
eje web tiene de más.
"""
import io
import json
import math

# ═══════════════════════════════════════════════════════════════════════════
#  LA CURVA
# ═══════════════════════════════════════════════════════════════════════════
#  Medida en `_curva_biblioteca.py` sobre los 12 baremos reales de la propia
#  biblioteca. Referencia = profesional adulto.
CURVA = {
    'menor_mejor|juvenil_inicial': 1.2706, 'menor_mejor|juvenil': 1.1412,
    'menor_mejor|juvenil_avanzado': 1.0633, 'menor_mejor|amateur': 1.0824,
    'menor_mejor|semipro': 1.0353, 'menor_mejor|profesional': 1.0,
    'menor_mejor|elite': 0.9412,
    'mayor_mejor|juvenil_inicial': 0.6087, 'mayor_mejor|juvenil': 0.7391,
    'mayor_mejor|juvenil_avanzado': 0.8261, 'mayor_mejor|amateur': 0.8750,
    'mayor_mejor|semipro': 0.9375, 'mayor_mejor|profesional': 1.0,
    'mayor_mejor|elite': 1.1250,
}

#  La curva de la Fase 1, medida sobre las 31 del catálogo web. Aquí solo se
#  usa para lo que la biblioteca no cubre: las categorías por debajo de sub-15
#  y el contexto de respaldo ('general', 'general').
FASE1 = {
    'menor_mejor|sub_15': 1.0731, 'menor_mejor|sub_14': 1.1003,
    'menor_mejor|sub_12': 1.1846, 'menor_mejor|profesional': 0.9933,
    'mayor_mejor|sub_15': 0.8248, 'mayor_mejor|sub_14': 0.7804,
    'mayor_mejor|sub_12': 0.6758, 'mayor_mejor|profesional': 1.0435,
}

MAYOR, MENOR = 'mayor_mejor', 'menor_mejor'


def factores_web(d):
    """Factor de cada uno de los 11 contextos del catálogo web, sobre la
    referencia (profesional adulto)."""
    ji = CURVA[f'{d}|juvenil_inicial']
    return {
        ('general', 'elite'):       CURVA[f'{d}|elite'],
        ('general', 'profesional'): CURVA[f'{d}|profesional'],
        ('general', 'semipro'):     CURVA[f'{d}|semipro'],
        ('general', 'amateur'):     CURVA[f'{d}|amateur'],
        # El eje de la biblioteca empareja sub-19 con «juvenil avanzado» y
        # sub-17 con «juvenil»; el web llega hasta sub-18.
        ('sub_18', 'general'):      CURVA[f'{d}|juvenil_avanzado'],
        ('sub_17', 'general'):      CURVA[f'{d}|juvenil'],
        # Sub-16 cae justo entre dos contextos con dato real: se interpola.
        ('sub_16', 'general'):      math.sqrt(CURVA[f'{d}|juvenil'] * ji),
        ('sub_15', 'general'):      ji,
        # Por debajo de sub-15 la biblioteca no llega. Se extiende con la
        # proporción que la Fase 1 midió entre esas categorías y sub-15.
        ('sub_14', 'general'):      ji * (FASE1[f'{d}|sub_14'] / FASE1[f'{d}|sub_15']),
        ('sub_12', 'general'):      ji * (FASE1[f'{d}|sub_12'] / FASE1[f'{d}|sub_15']),
        # El respaldo queda un poco por debajo del profesional, como en las 31.
        ('general', 'general'):     1.0 / FASE1[f'{d}|profesional'],
    }


ORDEN_CONTEXTOS = [
    ('general', 'elite'), ('general', 'profesional'), ('general', 'semipro'),
    ('general', 'amateur'), ('sub_18', 'general'), ('sub_17', 'general'),
    ('sub_16', 'general'), ('sub_15', 'general'), ('sub_14', 'general'),
    ('sub_12', 'general'), ('general', 'general'),
]

# ═══════════════════════════════════════════════════════════════════════════
#  CÓMO ESCALA CADA TIPO DE MAGNITUD
# ═══════════════════════════════════════════════════════════════════════════
#  No todo lo que se mide escala igual con la edad, y usar una sola curva para
#  todo fue el primer error de este script: salían sub-15 con 12,6 km/h de VIFT
#  (lo real son 15-16) y marcadores sobre 10 con los cuatro umbrales repetidos.
#
#  La curva `mayor_mejor` está medida sobre distancias, alturas de salto y
#  cargas — magnitudes que dependen del tamaño del cuerpo y por eso caen un 40%
#  del profesional al sub-15. Una velocidad no hace eso.
#
#    EXTENSIVA  Crece con el cuerpo: metros, centímetros, vatios, kilos,
#               segundos. Usa la curva de su propia dirección.
#    RITMO      Velocidades y magnitudes por unidad de tiempo o por kilo:
#               km/h, W/kg, ml/kg/min, reps/60 s, vueltas/30 s. Una velocidad
#               es distancia partida por tiempo, así que escala como el
#               INVERSO de la curva de tiempos — bastante más suave.
#    DEFICIT    Marcadores acotados: /5, /10, /15, /27, %. Aquí no escala el
#               acierto sino el FALLO: «el élite falla 1 de 10 y el sub-15
#               falla 4». Escalar el acierto lo empuja contra el techo y
#               repite umbrales; escalar el fallo nunca se pasa del máximo.
#    PLANA      Índices que ya vienen normalizados: asimetrías entre piernas,
#               % de deterioro, diferenciales contra la propia marca. No
#               mejoran con la edad y meterles curva sería exigirle al adulto
#               más simetría que al niño sin ningún motivo.
EXTENSIVA, RITMO, DEFICIT, PLANA = 'extensiva', 'ritmo', 'deficit', 'plana'

#  Los 7 contextos de la biblioteca, traducidos al eje del web.
MAPA_REAL = {
    'elite': ('general', 'elite'), 'profesional': ('general', 'profesional'),
    'semipro': ('general', 'semipro'), 'amateur': ('general', 'amateur'),
    'juvenil_avanzado': ('sub_18', 'general'), 'juvenil': ('sub_17', 'general'),
    'juvenil_inicial': ('sub_15', 'general'),
}


# ═══════════════════════════════════════════════════════════════════════════
#  LAS 13 QUE YA ESTABAN
# ═══════════════════════════════════════════════════════════════════════════
#  clave del catálogo web → nombre de la plantilla en la biblioteca.
#  Miden lo mismo con el mismo protocolo, así que se enriquecen en su sitio en
#  vez de crear una segunda entrada que dividiría el histórico del jugador.
DUPLICADOS = {
    'yoyo_ir1':         'Yo-Yo Intermittent Recovery Test (IR1/IR2)',
    'course_navette':   'Course Navette 20 m (Léger Beep Test)',
    'sprint_30m':       'Sprint 10 m, 20 m y 30 m',
    'cmj':              'Countermovement Jump (CMJ)',
    'sj':               'Squat Jump (SJ)',
    'rsa':              'RSA Test (Repeated Sprint Ability)',
    't_test':           'T-Test de Agilidad',
    'illinois':         'Illinois Agility Test',
    'salto_horizontal': 'Salto Horizontal (Broad Jump)',
    'sit_and_reach':    'Sit and Reach (Wells & Dillon)',
    'vo2max':           'VO₂max Directo (Ergometría)',
    'test_505':         '505 COD Test',
    'lspt':             'Loughborough Soccer Passing Test (LSPT)',
}


# ═══════════════════════════════════════════════════════════════════════════
#  LAS 27 NUEVAS
# ═══════════════════════════════════════════════════════════════════════════
#  campos: (clave, etiqueta, unidad, mín, máx, decimales, ejemplo, dirección,
#           principal)
#  anclas: campo → (dirección, escala, [(nivel_biblioteca, [e, b, p, d]), ...])
#          escala=False deja el mismo baremo en los once contextos. Es lo
#          correcto en los índices que ya vienen normalizados —una asimetría
#          entre piernas o un % de deterioro no mejoran con la edad— y meterles
#          la curva los volvería más exigentes con el adulto sin motivo.
#  reales: campos cuyo baremo se copia de `test_reference_ranges`.

NUEVAS = {

    # ─── FÍSICAS ────────────────────────────────────────────────────────────
    'ift_30_15': {
        'plantilla': '30-15 Intermittent Fitness Test (30-15IFT)',
        'campos': [
            ('vift_kmh', 'VIFT', 'km/h', 8, 26, 1, '18.5', MAYOR, True),
            ('vo2max', 'VO₂max estimado', 'ml/kg/min', 25, 80, 1, '55.0', MAYOR, False),
        ],
        'anclas': {
            # «Élite adulto masculino: VIFT 19–21 km/h. Sub-18 bueno: 17–19 km/h»
            'vift_kmh': (MAYOR, RITMO, [('elite', [21, 20, 19, 18]),
                                       ('juvenil_avanzado', [19, 18, 17, 16])]),
            'vo2max': (MAYOR, RITMO, [('elite', [62, 58, 54, 50])]),
        },
    },

    'y_balance': {
        'plantilla': 'Y-Balance Test (YBT)',
        'campos': [
            ('composite_pct', 'Score compuesto', '%', 50, 130, 1, '94.0', MAYOR, True),
            ('asym_ant_cm', 'Asimetría anterior', 'cm', 0, 15, 1, '2.0', MENOR, False),
        ],
        'anclas': {
            # El alcance ya viene dividido por la longitud de la pierna, que es
            # justo lo que cambia con la edad. Por eso no escala.
            'composite_pct': (MAYOR, PLANA, [('profesional', [100, 94, 89, 84])]),
            'asym_ant_cm': (MENOR, PLANA, [('profesional', [1, 2, 3, 4])]),
        },
    },

    'rast': {
        'plantilla': 'RAST (Running-based Anaerobic Sprint Test)',
        'campos': [
            ('pmax_w', 'Potencia máxima', 'W', 200, 1600, 0, '850', MAYOR, True),
            ('pmin_w', 'Potencia mínima', 'W', 100, 1200, 0, '600', MAYOR, False),
            ('fatigue_idx', 'Índice de fatiga', 'W/s', 0, 40, 1, '8.0', MENOR, False),
        ],
        'anclas': {
            # «Potencia máxima élite: > 900 W. IF aceptable: < 10 W/s»
            'pmax_w': (MAYOR, EXTENSIVA, [('elite', [1000, 900, 800, 700])]),
            'pmin_w': (MAYOR, EXTENSIVA, [('elite', [700, 620, 540, 460])]),
            'fatigue_idx': (MENOR, EXTENSIVA, [('profesional', [5, 7, 10, 13])]),
        },
    },

    'dinamometria': {
        'plantilla': 'Dinamometría Manual',
        'campos': [
            ('grip_dom_kg', 'Prensión mano dominante', 'kg', 10, 100, 1, '52.0', MAYOR, True),
            ('grip_nd_kg', 'Prensión mano no dominante', 'kg', 10, 100, 1, '49.0', MAYOR, False),
        ],
        'anclas': {
            # «Adulto masculino deportista: 50–65 kg»
            'grip_dom_kg': (MAYOR, EXTENSIVA, [('amateur', [65, 58, 52, 46])]),
            'grip_nd_kg': (MAYOR, EXTENSIVA, [('amateur', [61, 55, 49, 43])]),
        },
    },

    'squat_1rm': {
        'plantilla': '1RM Back Squat',
        'campos': [
            ('ratio', 'Ratio 1RM / peso corporal', '×', 0.4, 3.0, 2, '1.50', MAYOR, True),
            ('one_rm_kg', 'Carga máxima', 'kg', 20, 300, 1, '110.0', MAYOR, False),
            ('bw_kg', 'Peso corporal', 'kg', 25, 130, 1, '73.0', MAYOR, False),
        ],
        # El ratio ya trae baremo publicado. La carga en kg no se puntúa sola:
        # sin el peso corporal al lado no dice nada.
        'reales': ['ratio'],
        'anclas': {},
    },

    'abdominales_60s': {
        'plantilla': 'Resistencia Abdominal (NSCA/ACSM)',
        'campos': [
            ('reps', 'Repeticiones en 60 s', 'reps', 0, 100, 0, '45', MAYOR, True),
        ],
        'anclas': {
            # «Bueno (20–29 años masculino): 44–49 reps. Excelente: ≥ 50»
            'reps': (MAYOR, RITMO, [('amateur', [50, 45, 40, 34])]),
        },
    },

    'margaria_kalamen': {
        'plantilla': 'Margaria-Kalamen (Escalera)',
        'campos': [
            ('power_wkg', 'Potencia relativa', 'W/kg', 5, 35, 1, '20.0', MAYOR, True),
            ('power_w', 'Potencia', 'W', 300, 2600, 0, '1600', MAYOR, False),
        ],
        'anclas': {
            # «Futbolistas buenos: 1500–1800 W. Élite: > 1800 W. Relativo: > 22 W/kg»
            'power_wkg': (MAYOR, RITMO, [('profesional', [22, 20, 18, 16])]),
            'power_w': (MAYOR, EXTENSIVA, [('profesional', [1900, 1700, 1500, 1300])]),
        },
    },

    'list_test': {
        'plantilla': 'Loughborough Intermittent Shuttle Test (LIST)',
        'campos': [
            ('total_min', 'Minutos mantenidos', 'min', 0, 90, 0, '75', MAYOR, True),
            ('sprint_dec_pct', 'Descenso del sprint', '%', 0, 30, 1, '4.0', MENOR, False),
        ],
        'anclas': {
            # «Élite completa (90 min) sin fallos. Descenso > 5% = fatiga»
            'total_min': (MAYOR, EXTENSIVA, [('elite', [90, 85, 75, 60])]),
            'sprint_dec_pct': (MENOR, EXTENSIVA, [('profesional', [2, 3.5, 5, 7])]),
        },
    },

    # ─── TÉCNICAS ───────────────────────────────────────────────────────────
    'dribbling_fpf': {
        'plantilla': 'Dribbling Speed Test (FPF)',
        'campos': [
            ('time_s', 'Tiempo total', 's', 5, 25, 2, '9.20', MENOR, True),
            ('time_nd', 'Tiempo pierna no dominante', 's', 5, 25, 2, '9.80', MENOR, False),
        ],
        'reales': ['time_s'],
        'anclas': {
            'time_nd': (MENOR, EXTENSIVA, [('juvenil_avanzado', [9.0, 9.5, 10.2, 11.2])]),
        },
    },

    'golpeo_porteria_ali': {
        'plantilla': 'Golpeo a Portería (Ali — Loughborough)',
        'campos': [
            ('score', 'Puntuación', 'pts', 0, 30, 0, '18', MAYOR, True),
            ('velocity_kmh', 'Velocidad de disparo', 'km/h', 30, 140, 1, '85.0', MAYOR, False),
        ],
        'reales': ['score'],
        'anclas': {
            # «Velocidad élite adulto: 90–110 km/h»
            'velocity_kmh': (MAYOR, RITMO, [('elite', [110, 100, 92, 84])]),
        },
    },

    'conduccion_vallas': {
        'plantilla': 'Conducción con Vallas y Slalom',
        'campos': [
            ('time_s', 'Tiempo total penalizado', 's', 6, 30, 2, '13.00', MENOR, True),
        ],
        'anclas': {
            # «Bueno sub-18: < 13 s. Referencia profesional: < 10 s»
            'time_s': (MENOR, EXTENSIVA, [('juvenil_avanzado', [11.5, 13.0, 14.5, 16.5]),
                                     ('profesional', [9.0, 10.0, 11.2, 12.8])]),
        },
    },

    'dominio_balon_fifa': {
        'plantilla': 'Dominio de Balón — 5 Superficies (FIFA)',
        'campos': [
            ('cycles', 'Ciclos completos en 60 s', 'ciclos', 0, 30, 0, '6', MAYOR, True),
            ('streak', 'Racha máxima de toques', 'toques', 0, 300, 0, '40', MAYOR, False),
        ],
        'anclas': {
            # «Bueno sub-16: ≥ 5 ciclos. Avanzado: ≥ 10. Élite: > 60 toques»
            'cycles': (MAYOR, RITMO, [('juvenil_inicial', [8, 5, 3, 2]),
                                     ('elite', [14, 10, 7, 5])]),
            'streak': (MAYOR, EXTENSIVA, [('elite', [100, 60, 40, 25])]),
        },
    },

    'recepcion_orientada': {
        'plantilla': 'Recepción y Control Orientado',
        'campos': [
            ('success', 'Controles exitosos', '/10', 0, 10, 0, '7', MAYOR, True),
            ('reaction_s', 'Tiempo de reacción', 's', 0.3, 5, 2, '1.10', MENOR, False),
        ],
        'anclas': {
            # «Excelente: ≥ 8/10. Bueno: 6–7/10. Deficiente: < 5/10»
            'success': (MAYOR, DEFICIT, [('juvenil', [9, 8, 6, 5])]),
            'reaction_s': (MENOR, EXTENSIVA, [('juvenil', [0.8, 1.1, 1.4, 1.8])]),
        },
    },

    'regate_1vs0': {
        'plantilla': 'Regate 1vs0 con Finta Obligatoria',
        'campos': [
            ('time_s', 'Tiempo penalizado', 's', 5, 25, 2, '10.00', MENOR, True),
            ('finta_quality', 'Calidad de la finta', '1-3', 1, 3, 0, '2', MAYOR, False),
        ],
        'anclas': {
            # «Bueno sub-18: < 10 s sin penalización»
            'time_s': (MENOR, EXTENSIVA, [('juvenil_avanzado', [8.8, 10.0, 11.3, 13.0])]),
            # La calidad de la finta es un juicio del entrenador en tres
            # escalones: no da para cuatro umbrales sin repetirlos.
        },
    },

    'cabeceo_bangsbo': {
        'plantilla': 'Cabeceo — Precisión y Distancia (Bangsbo)',
        'campos': [
            ('precision_score', 'Precisión', '/15', 0, 15, 0, '9', MAYOR, True),
            ('max_distance_m', 'Distancia máxima en salto', 'm', 2, 25, 1, '8.0', MAYOR, False),
        ],
        'anclas': {
            # «Bueno sub-18: ≥ 9/15 en precisión. Distancia en salto: > 8 m»
            'precision_score': (MAYOR, DEFICIT, [('juvenil_avanzado', [12, 9, 7, 5])]),
            'max_distance_m': (MAYOR, EXTENSIVA, [('juvenil_avanzado', [11, 8, 6, 4])]),
        },
    },

    'saque_banda': {
        'plantilla': 'Saque de Banda — Distancia y Precisión',
        'campos': [
            ('max_distance_m', 'Distancia máxima', 'm', 5, 50, 1, '22.0', MAYOR, True),
            ('accuracy_pct', 'Precisión zona media', '%', 0, 100, 0, '80', MAYOR, False),
        ],
        'anclas': {
            # «Profesional adulto: > 30 m. Bueno sub-18: > 20 m»
            'max_distance_m': (MAYOR, EXTENSIVA, [('juvenil_avanzado', [26, 20, 16, 12]),
                                             ('profesional', [34, 30, 25, 20])]),
            # «Precisión zona media: ≥ 4/5» = 80%
            'accuracy_pct': (MAYOR, DEFICIT, [('profesional', [95, 80, 65, 50])]),
        },
    },

    'conduccion_recta': {
        'plantilla': 'Velocidad de Conducción Línea Recta',
        'campos': [
            ('dribble_30m', 'Conducción 30 m', 's', 3, 15, 2, '5.40', MENOR, True),
            ('diff_sprint', 'Diferencial vs sprint libre', 's', 0, 5, 2, '0.50', MENOR, False),
        ],
        'anclas': {
            # «Élite adulto: conducción < 5,2 s. Diferencial aceptable: < 0,5 s»
            'dribble_30m': (MENOR, EXTENSIVA, [('elite', [5.0, 5.2, 5.6, 6.2])]),
            # El diferencial ya es la resta contra el propio sprint del jugador:
            # viene normalizado y no escala.
            'diff_sprint': (MENOR, PLANA, [('profesional', [0.3, 0.5, 0.8, 1.1])]),
        },
    },

    'pase_largo_precision': {
        'plantilla': 'Pase Largo — Precisión y Distancia',
        'campos': [
            ('score', 'Puntuación', '/27', 0, 27, 0, '16', MAYOR, True),
            ('asym', 'Asimetría entre piernas', 'pts', 0, 27, 0, '3', MENOR, False),
        ],
        'anclas': {
            # «Bueno: ≥ 16/27. Excelente: ≥ 22/27»
            'score': (MAYOR, DEFICIT, [('juvenil', [22, 16, 12, 8])]),
            # «Diferencia entre piernas ≤ 3 pts = equilibrio aceptable»
            'asym': (MENOR, PLANA, [('profesional', [1, 2, 3, 5])]),
        },
    },

    'penalti_test': {
        'plantilla': 'Penalti — Velocidad, Precisión y Presión',
        'campos': [
            ('score', 'Puntuación', '/30', 0, 30, 0, '20', MAYOR, True),
        ],
        'reales': ['score'],
        'anclas': {},
    },

    'pared_primer_toque': {
        'plantilla': 'Pared — Pases de Primer Toque',
        'campos': [
            ('hits_30s', 'Toques precisos en 30 s', 'toques', 0, 60, 0, '22', MAYOR, True),
        ],
        'anclas': {
            # «Bueno sub-18: ≥ 20. Élite: ≥ 28. Profesional: ≥ 34». La fuente se
            # contradice al poner al profesional por encima del élite; con los
            # dos puntos promediados el orden se recompone solo.
            'hits_30s': (MAYOR, RITMO, [('juvenil_avanzado', [26, 20, 15, 11]),
                                       ('profesional', [40, 34, 28, 22])]),
        },
    },

    'conduccion_circuito_30s': {
        'plantilla': 'Conducción en Circuito Cerrado 30 s',
        'campos': [
            ('laps', 'Vueltas en 30 s', 'vueltas', 0, 12, 1, '4.0', MAYOR, True),
            ('diff_direction', 'Diferencia entre sentidos', 'vueltas', 0, 5, 1, '0.5', MENOR, False),
        ],
        'anclas': {
            # «Bueno sub-18: ≥ 4 vueltas. Élite: ≥ 5»
            'laps': (MAYOR, RITMO, [('juvenil_avanzado', [5, 4, 3, 2]),
                                   ('elite', [6, 5, 4, 3])]),
            'diff_direction': (MENOR, PLANA, [('profesional', [0.2, 0.5, 1.0, 1.5])]),
        },
    },

    'recepcion_pivot': {
        'plantilla': 'Recepción en Movimiento — Pivot',
        'campos': [
            ('correct', 'Controles orientados', '/10', 0, 10, 0, '7', MAYOR, True),
            ('orientation_s', 'Tiempo de orientación', 's', 0.3, 6, 2, '1.50', MENOR, False),
        ],
        'anclas': {
            # «Bueno: ≥ 7/10. Excelente: ≥ 9/10. Tiempo óptimo: < 1,5 s»
            'correct': (MAYOR, DEFICIT, [('juvenil', [9, 7, 5, 4])]),
            'orientation_s': (MENOR, EXTENSIVA, [('juvenil', [1.2, 1.5, 1.9, 2.4])]),
        },
    },

    'tiro_potencia_radar': {
        'plantilla': 'Tiro con Potencia (Radar)',
        'campos': [
            ('vmax_kmh', 'Velocidad máxima', 'km/h', 30, 150, 1, '85.0', MAYOR, True),
            ('vmean_kmh', 'Velocidad media', 'km/h', 25, 140, 1, '78.0', MAYOR, False),
            ('diff_legs', 'Diferencial entre piernas', 'km/h', 0, 60, 1, '15.0', MENOR, False),
        ],
        'anclas': {
            # «Élite profesional adulto: 90–120. Sub-18 bueno: 70–85»
            'vmax_kmh': (MAYOR, RITMO, [('elite', [120, 105, 95, 88]),
                                       ('juvenil_avanzado', [88, 78, 70, 62])]),
            'vmean_kmh': (MAYOR, RITMO, [('elite', [105, 95, 85, 78])]),
            'diff_legs': (MENOR, PLANA, [('profesional', [8, 14, 20, 26])]),
        },
    },

    'juego_aereo': {
        'plantilla': 'Juego Aéreo — Duelos de Cabeza',
        'campos': [
            ('wins_opp', 'Duelos ganados con oponente', '/5', 0, 5, 0, '3', MAYOR, True),
            ('wins_no_opp', 'Duelos ganados sin oponente', '/5', 0, 5, 0, '4', MAYOR, False),
        ],
        'anclas': {
            # «Bueno sub-18: ≥ 3/5 con oponente. Élite: ≥ 4/5»
            'wins_opp': (MAYOR, DEFICIT, [('juvenil_avanzado', [4, 3, 2, 1]),
                                       ('elite', [5, 4, 3, 2])]),
            'wins_no_opp': (MAYOR, DEFICIT, [('juvenil_avanzado', [5, 4, 3, 2])]),
        },
    },

    'trapping_test': {
        'plantilla': 'Control en Suelo — Trapping Test',
        'campos': [
            ('success_10', 'Controles exitosos', '/10', 0, 10, 0, '7', MAYOR, True),
        ],
        'anclas': {
            # «Bueno sub-16: ≥ 7/10. Élite sub-20: ≥ 9/10»
            'success_10': (MAYOR, DEFICIT, [('juvenil', [9, 7, 5, 4]),
                                         ('elite', [10, 9, 8, 6])]),
        },
    },

    'conduccion_cambio_ritmo': {
        'plantilla': 'Conducción con Cambio de Ritmo',
        'campos': [
            ('time_s', 'Tiempo total', 's', 4, 20, 2, '8.50', MENOR, True),
            ('balls_lost', 'Balones perdidos', 'balones', 0, 10, 0, '1', MENOR, False),
        ],
        'anclas': {
            # «Bueno sub-18: < 8,5 s sin perder el balón. Élite: < 7,5 s»
            'time_s': (MENOR, EXTENSIVA, [('juvenil_avanzado', [7.8, 8.5, 9.4, 10.5]),
                                     ('elite', [7.0, 7.5, 8.3, 9.3])]),
            'balls_lost': (MENOR, PLANA, [('profesional', [0, 1, 2, 3])]),
        },
    },

    'tecnica_bajo_fatiga': {
        'plantilla': 'Técnica Bajo Fatiga (FTT)',
        'campos': [
            ('decay_pct', 'Deterioro técnico', '%', 0, 80, 1, '12.0', MENOR, True),
            ('score_pre', 'Score técnico pre-fatiga', 'pts', 0, 100, 1, '80.0', MAYOR, False),
            ('score_post', 'Score técnico post-fatiga', 'pts', 0, 100, 1, '70.0', MAYOR, False),
        ],
        'anclas': {
            # «Élite: deterioro < 10%. Aceptable: < 20%. Preocupante: > 25%».
            # Es la caída del jugador contra su propia marca en fresco, así que
            # ya viene normalizada: no escala.
            'decay_pct': (MENOR, PLANA, [('profesional', [7, 12, 20, 26])]),
            # Los scores pre y post no tienen escala absoluta publicada: solo
            # valen para calcular el deterioro.
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  GENERACIÓN
# ═══════════════════════════════════════════════════════════════════════════

def redondear(v, decimales, minimo, maximo):
    v = max(minimo, min(maximo, v))
    return round(v, decimales) if decimales else int(round(v))


def separar(cortes, direccion, decimales, minimo, maximo):
    """Cuatro bandas siempre distintas.

    En un marcador sobre 10 con cuatro umbrales, el redondeo junta dos escalones
    de vez en cuando y sale algo como [9, 8, 6, 6]: el jugador que saca 6 cae a
    la vez en «promedio» y en «a mejorar», y la banda de abajo desaparece de la
    tabla. Se separa el umbral repetido por el paso mínimo que admite el campo.
    """
    paso = 10 ** -decimales if decimales else 1
    out = list(cortes)
    for i in range(1, 4):
        if direccion == MAYOR and out[i] >= out[i - 1]:
            out[i] = round(out[i - 1] - paso, decimales or None)
        elif direccion == MENOR and out[i] <= out[i - 1]:
            out[i] = round(out[i - 1] + paso, decimales or None)
    return [redondear(v, decimales, minimo, maximo) for v in out]


NIVELES_BIB = ('juvenil_inicial', 'juvenil', 'juvenil_avanzado', 'amateur',
               'semipro', 'profesional', 'elite')


def _interpolar(f_objetivo, anclas):
    """El valor que le toca a un contexto de factor `f_objetivo`.

    `anclas` son los puntos publicados como (factor, valor), y esta función
    pasa EXACTAMENTE por todos ellos. Entre dos anclas interpola en escala
    logarítmica —lo que se compara son proporciones, no diferencias— y fuera
    del rango extiende con la de su extremo.

    Interpolar es lo que arregla el cruce que salía antes. Con la media
    geométrica de todas las anclas, el Tiro con Potencia daba un sub-17 (90,1
    km/h) más exigente que el sub-18 (88), porque el sub-18 respetaba su valor
    publicado y el sub-17 se derivaba de un promedio que no pasaba por él. Una
    función monótona del factor no puede cruzarse consigo misma.
    """
    if len(anclas) == 1:
        f0, v0 = anclas[0]
        return v0 * f_objetivo / f0

    orden = sorted(anclas)
    if f_objetivo <= orden[0][0]:
        f0, v0 = orden[0]
        return v0 * f_objetivo / f0
    if f_objetivo >= orden[-1][0]:
        f1, v1 = orden[-1]
        return v1 * f_objetivo / f1

    for (f0, v0), (f1, v1) in zip(orden, orden[1:]):
        if f0 <= f_objetivo <= f1:
            t = (math.log(f_objetivo) - math.log(f0)) / (math.log(f1) - math.log(f0))
            if v0 > 0 and v1 > 0:
                return v0 * (v1 / v0) ** t
            # Un déficit puede valer 0 y el Sit and Reach baja de cero.
            return v0 + (v1 - v0) * t
    return orden[-1][1] * f_objetivo / orden[-1][0]


def generar(direccion, escala, puntos, decimales, minimo, maximo):
    """Los once contextos a partir de los puntos normativos publicados.

    Los puntos publicados se respetan TAL CUAL en su propio contexto: si la
    fuente dice que el sub-18 bueno son 20 m, en sub-18 salen 20 m. El resto se
    interpola entre ellos, así que la progresión no puede cruzarse.
    """
    if escala == PLANA:
        cortes = [redondear(v, decimales, minimo, maximo) for v in puntos[0][1]]
        return {ctx: list(cortes) for ctx in ORDEN_CONTEXTOS}

    #  Qué curva toca según el tipo de magnitud (ver el bloque de arriba).
    if escala == RITMO:
        fw = {ctx: 1.0 / f for ctx, f in factores_web(MENOR).items()}
        fp = {n: 1.0 / CURVA[f'{MENOR}|{n}'] for n in NIVELES_BIB}
    elif escala == DEFICIT:
        fw = factores_web(MENOR)
        fp = {n: CURVA[f'{MENOR}|{n}'] for n in NIVELES_BIB}
    else:
        fw = factores_web(direccion)
        fp = {n: CURVA[f'{direccion}|{n}'] for n in NIVELES_BIB}

    #  Un juego de anclas (factor, valor) por umbral. En DEFICIT lo que se
    #  interpola es el fallo, no el acierto.
    anclas = []
    for i in range(4):
        if escala == DEFICIT:
            anclas.append([(fp[n], maximo - v[i]) for n, v in puntos])
        else:
            anclas.append([(fp[n], v[i]) for n, v in puntos])

    salida = {}
    for ctx in ORDEN_CONTEXTOS:
        crudo = []
        for i in range(4):
            v = _interpolar(fw[ctx], anclas[i])
            crudo.append(maximo - v if escala == DEFICIT else v)
        salida[ctx] = separar([redondear(v, decimales, minimo, maximo) for v in crudo],
                              direccion, decimales, minimo, maximo)
    return salida


def desde_reales(filas, decimales, minimo, maximo, direccion):
    """Copia los 7 contextos publicados y deriva los 4 que el eje web añade."""
    salida = {}
    for nivel, ctx in MAPA_REAL.items():
        if nivel in filas:
            salida[ctx] = [redondear(v, decimales, minimo, maximo) for v in filas[nivel]]

    fw = factores_web(direccion)
    ji = CURVA[f'{direccion}|juvenil_inicial']
    base_ji = filas.get('juvenil_inicial')
    base_pro = filas.get('profesional')

    #  Sub-16 se interpola entre los dos contextos reales que lo rodean.
    if 'juvenil_inicial' in filas and 'juvenil' in filas:
        salida[('sub_16', 'general')] = [
            redondear(math.sqrt(a * b) if a > 0 and b > 0 else (a + b) / 2,
                      decimales, minimo, maximo)
            for a, b in zip(filas['juvenil_inicial'], filas['juvenil'])]

    #  Sub-14 y sub-12 se extienden desde el sub-15 real, no desde la
    #  referencia: así arrancan del dato publicado más cercano.
    for ctx in (('sub_14', 'general'), ('sub_12', 'general')):
        if base_ji:
            salida[ctx] = [redondear(v * fw[ctx] / ji, decimales, minimo, maximo)
                           for v in base_ji]

    if base_pro:
        salida[('general', 'general')] = [
            redondear(v * fw[('general', 'general')], decimales, minimo, maximo)
            for v in base_pro]
    return salida


def main():
    datos = json.load(io.open('sql/_sb_evaluaciones.json', encoding='utf-8'))
    plantillas = {t['name']: t for t in datos['templates']}

    reales = {}
    for r in datos['ranges']:
        nombre = next(t['name'] for t in datos['templates'] if t['id'] == r['template_id'])
        reales.setdefault((nombre, r['field_key']), {})[r['competitive_level']] = [
            r['elite_threshold'], r['good_threshold'],
            r['average_threshold'], r['poor_threshold']]

    faltan = [n for n in list(DUPLICADOS.values()) + [d['plantilla'] for d in NUEVAS.values()]
              if n not in plantillas]
    if faltan:
        raise SystemExit('Plantillas que no existen en la biblioteca: %s' % faltan)

    cubiertas = set(DUPLICADOS.values()) | {d['plantilla'] for d in NUEVAS.values()}
    sueltas = set(plantillas) - cubiertas
    if sueltas:
        raise SystemExit('Plantillas sin clasificar: %s' % sorted(sueltas))

    resultado = {}
    for clave, spec in NUEVAS.items():
        p = plantillas[spec['plantilla']]
        campos = {c[0]: c for c in spec['campos']}
        baremos = {}

        for campo in spec.get('reales', []):
            _, _, _, minimo, maximo, dec, _, direccion, _ = campos[campo]
            filas = reales.get((spec['plantilla'], campo))
            if not filas:
                raise SystemExit('Sin baremo real para %s.%s' % (clave, campo))
            baremos[campo] = desde_reales(filas, dec, minimo, maximo, direccion)

        for campo, (direccion, escala, puntos) in spec['anclas'].items():
            _, _, _, minimo, maximo, dec, _, dir_campo, _ = campos[campo]
            if dir_campo != direccion:
                raise SystemExit('Dirección incoherente en %s.%s' % (clave, campo))
            baremos[campo] = generar(direccion, escala, puntos, dec, minimo, maximo)

        resultado[clave] = {'plantilla': p, 'spec': spec, 'baremos': baremos}

    json.dump({k: {'baremos': {c: {'%s|%s' % ctx: v for ctx, v in t.items()}
                               for c, t in v['baremos'].items()}}
               for k, v in resultado.items()},
              io.open('sql/_baremos_generados.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    print('Pruebas nuevas: %d   duplicadas: %d   total biblioteca: %d'
          % (len(NUEVAS), len(DUPLICADOS), len(plantillas)))
    print('Campos con baremo generado: %d'
          % sum(len(v['baremos']) for v in resultado.values()))
    return resultado


if __name__ == '__main__':
    main()
