# -*- coding: utf-8 -*-
"""Dónde se usa cada una de las 18 pruebas que no lo decían.

Las 40 avaladas ya traen esto dentro de su bibliografía, con el marcador «▸»:
son los clubes y federaciones que venían en el documento de origen. Esas no se
tocan. Aquí van solo las 18 restantes.

QUÉ SE PUEDE ESCRIBIR AQUÍ Y QUÉ NO
-----------------------------------
Va la institución que creó la prueba o el ámbito donde está documentado que es
estándar: una federación, una universidad, un centro de investigación, una
batería oficial. Todo lo que hay se apoya en la cita que la prueba ya llevaba
en `fuente` —la afiliación de quien la publicó— o en un hecho notorio.

Lo que NO se escribe es el nombre de un club inventado. Las 40 tienen los suyos
porque venían en el documento; para estas 18 no hay de dónde sacarlos, y poner
«lo usa el Bayern» sin saberlo convierte la ficha en algo que no se puede
creer. Si aparece la fuente de que un club concreto usa alguna, se añade aquí
diciendo de dónde salió el dato.

Tres se quedan sin entrada a propósito —control orientado, golpeo largo y
regate 1v1— porque son valoración del propio cuerpo técnico y no tienen
institución detrás. Su `fuente` ya lo dice.
"""

DONDE_SE_USA = {

    # ── Baterías oficiales ─────────────────────────────────────────────────
    'abdominales_30s':
        '▸ Batería EUROFIT del Consejo de Europa, aplicada en los sistemas '
        'escolares europeos para el seguimiento de la condición física.',

    'antropometria':
        '▸ El estándar de referencia para tomar pliegues y perímetros es el '
        'protocolo ISAK (International Society for the Advancement of '
        'Kinanthropometry), que es el que siguen los servicios médicos que '
        'certifican a sus antropometristas.',

    # ── Centros de investigación identificables ────────────────────────────
    'cooper':
        '▸ Creado por Kenneth Cooper para las Fuerzas Aéreas de Estados Unidos '
        'y difundido después por el Cooper Institute. Es la prueba de '
        'resistencia de campo más conocida del mundo y sigue siendo la que se '
        'usa cuando no hay más material que una pista y un cronómetro.',

    'sprint_10m':
        '▸ Los valores de referencia salen del trabajo de Haugen en '
        'Olympiatoppen, el centro de alto rendimiento del deporte olímpico '
        'noruego, con futbolistas de la liga profesional de aquel país.',

    'sprint_20m':
        '▸ Misma procedencia que el de 10 m: Haugen y Olympiatoppen, el centro '
        'de alto rendimiento noruego, con datos de futbolistas profesionales.',

    'plancha':
        '▸ Del trabajo de Stuart McGill en la Universidad de Waterloo, '
        'referencia en la prevención de la lesión lumbar; sus pruebas de '
        'resistencia del tronco se usan en fisioterapia deportiva.',

    'reaccion':
        '▸ La prueba de la regla es un clásico de la valoración neuromuscular; '
        'en el deporte se ha usado sobre todo en el ámbito del entrenamiento '
        'deportivo estadounidense para seguir la recuperación tras una '
        'conmoción.',

    'perfil_tactico':
        '▸ Las dimensiones vienen de la línea de trabajo de Kannekens y '
        'Elferink-Gemser en la Universidad de Groningen, sobre habilidades '
        'tácticas en el fútbol formativo neerlandés.',

    'perfil_mental':
        '▸ Las cinco dimensiones se apoyan en el marco de fortaleza mental de '
        'Gucciardi, uno de los más usados en psicología del deporte para '
        'describir el comportamiento competitivo.',

    'tiros_porteria':
        '▸ La forma de puntuar por zonas viene del trabajo de Rösch dentro del '
        'programa de investigación médica de la FIFA (F-MARC).',

    # ── Baterías técnicas de origen académico ──────────────────────────────
    'pase_precision':
        '▸ Adaptado de la batería Mor-Christian, desarrollada en el fútbol '
        'universitario estadounidense como forma de puntuar la habilidad '
        'técnica con material mínimo.',

    'conduccion_conos':
        '▸ Adaptado de la misma batería Mor-Christian del fútbol universitario '
        'estadounidense, de donde sale el recorrido en zigzag entre conos.',

    # ── Prácticas extendidas, sin una institución que las firme ────────────
    'abalakov':
        '▸ Protocolo de la escuela soviética, incorporado después al control de '
        'la potencia en deportes de equipo junto al CMJ. Se toma en las mismas '
        'sesiones de control que este, porque la diferencia entre los dos dice '
        'cuánto aprovecha el jugador el braceo.',

    'checkin_diario':
        '▸ Los cuestionarios breves de bienestar diario —energía, ánimo y '
        'sueño— son práctica corriente en el control de la carga en el fútbol '
        'profesional, porque avisan de la fatiga acumulada antes de que se vea '
        'en las pruebas físicas.',

    'juegos_malabares':
        '▸ De uso extendido en el fútbol formativo de todo el mundo como '
        'referencia de coordinación, aunque no forma parte de ninguna batería '
        'oficial ni tiene baremos publicados con muestra amplia.',
}
