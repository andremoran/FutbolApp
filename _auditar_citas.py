# -*- coding: utf-8 -*-
"""¿La cita de cada prueba habla de esa prueba?

El saque de banda citaba «Measurement of sprinting speed of professional and
amateur soccer players». Un estudio sobre VELOCIDAD DE ESPRINT en una prueba
de saques de banda. Venia asi del documento de origen y ahi llevaba desde el
principio, con pinta de dato verificado.

Esto compara el TEMA del titulo con el tema de la prueba para buscar mas
casos. No lee los articulos, solo sus titulos.

HASTA DONDE LLEGA
-----------------
Solo puede juzgar las citas que guardan el TITULO del articulo: 21 de las 58.
Las otras 33 guardan autor, año, revista y volumen, y ahi un error como el del
saque de banda no se ve. Que este script no avise no quiere decir que todas
las citas esten bien; quiere decir que las que se pueden leer, encajan.

Y hay que quitar el nombre de la revista antes de comparar: «Journal of
STRENGTH and Conditioning Research» hacia que toda prueba publicada alli
pareciera de fuerza. Con eso, los avisos bajaron de 11 a 2.

    .venv/Scripts/python.exe _auditar_citas.py
"""
import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'C:\MisApps\FutbolAppWeb')

import futbol.tests_catalogo as cat

#  Temas y las palabras que los delatan, en ingles y en español.
TEMAS = {
    'esprint':     ('sprint', 'sprinting', 'acceleration', 'speed', 'velocidad'),
    'salto':       ('jump', 'jumping', 'vertical', 'salto', 'plyometric'),
    'resistencia': ('endurance', 'aerobic', 'vo2', 'intermittent', 'recovery',
                    'yo-yo', 'shuttle', 'interval', 'physiology', 'fitness'),
    'fuerza':      ('strength', 'force', 'grip', 'squat', '1rm', 'resistance'),
    'agilidad':    ('agility', 'change of direction', 'cod'),
    'pase':        ('passing', 'pass', 'kick', 'kicking', 'instep', 'pase'),
    'conduccion':  ('dribbling', 'dribble', 'conduccion'),
    'cabeceo':     ('heading', 'header', 'aerial'),
    'control':     ('trapping', 'ball control', 'first touch', 'receiving'),
    'flexibilidad': ('flexibility', 'sit-and-reach', 'sit and reach', 'hamstring'),
    'equilibrio':  ('balance', 'stability', 'postural'),
    'mental':      ('anxiety', 'mental', 'psychological', 'attention', 'toughness',
                    'personality', 'tactical', 'decision'),
    'antropo':     ('anthropometric', 'body composition', 'skinfold', 'body fat'),
    'lumbar':      ('low back', 'lumbar', 'trunk', 'core'),
    'reaccion':    ('reaction time', 'reaction'),
}

#  Que tema le toca a cada prueba. Solo las que tienen uno claro.
DE_LA_PRUEBA = {
    'sprint_10m': 'esprint', 'sprint_20m': 'esprint', 'sprint_30m': 'esprint',
    'rsa': 'esprint', 'rast': 'esprint',
    'cmj': 'salto', 'sj': 'salto', 'abalakov': 'salto',
    'salto_horizontal': 'salto', 'margaria_kalamen': 'salto',
    'cooper': 'resistencia', 'course_navette': 'resistencia',
    'yoyo_ir1': 'resistencia', 'vo2max': 'resistencia',
    'ift_30_15': 'resistencia', 'list_test': 'resistencia',
    'squat_1rm': 'fuerza', 'dinamometria': 'fuerza',
    'illinois': 'agilidad', 't_test': 'agilidad', 'test_505': 'agilidad',
    'lspt': 'pase', 'pase_precision': 'pase', 'pase_largo_precision': 'pase',
    'golpeo_largo': 'pase', 'golpeo_porteria_ali': 'pase',
    'tiros_porteria': 'pase', 'tiro_potencia_radar': 'pase',
    'penalti_test': 'pase', 'pared_primer_toque': 'pase',
    'conduccion_conos': 'conduccion', 'conduccion_recta': 'conduccion',
    'conduccion_vallas': 'conduccion', 'conduccion_circuito_30s': 'conduccion',
    'conduccion_cambio_ritmo': 'conduccion', 'dribbling_fpf': 'conduccion',
    'regate_1v1': 'conduccion', 'regate_1vs0': 'conduccion',
    'cabeceo_bangsbo': 'cabeceo', 'juego_aereo': 'cabeceo',
    'trapping_test': 'control', 'recepcion_orientada': 'control',
    'recepcion_pivot': 'control', 'control_orientado': 'control',
    'sit_and_reach': 'flexibilidad',
    'y_balance': 'equilibrio',
    'perfil_mental': 'mental', 'perfil_tactico': 'mental',
    'antropometria': 'antropo',
    'plancha': 'lumbar',
    'reaccion': 'reaccion',
}

#  Temas que se solapan de verdad y no deben dar aviso.
COMPATIBLES = {
    ('esprint', 'agilidad'), ('agilidad', 'esprint'),
    ('esprint', 'resistencia'), ('resistencia', 'esprint'),
    ('salto', 'fuerza'), ('fuerza', 'salto'),
    ('pase', 'conduccion'), ('conduccion', 'pase'),
    ('control', 'pase'), ('pase', 'control'),
    ('cabeceo', 'pase'), ('lumbar', 'fuerza'),
    ('equilibrio', 'lumbar'),
}

#  Nombres de revistas y libros: lo que hay que ignorar al buscar el tema.
PUBLICACIONES = [
    'journal of strength and conditioning research',
    'j. strength and conditioning research',
    'strength and conditioning journal',
    "nsca's performance training journal",
    'european journal of applied physiology',
    'international journal of sports physiology and performance',
    'int. j. sports medicine', 'int j sports med', 'ijspp',
    'journal of sports sciences', 'j sports sci',
    'medicine and science in sports and exercise',
    'sports medicine', 'sports med',
    'fitness training in football — a scientific approach',
    'fitness training in football',
    'j. science and medicine in sport', 'journal of science and medicine in sport',
    'scand j med sci sports', 'j athl train', 'j orthopaedic & sports physical therapy',
    'american journal of sports medicine', 'am j sports med',
    'research quarterly', 'physical education review', 'science and soccer',
    "acsm's guidelines for exercise testing and prescription",
    'acsm guidelines', 'jama', 'joperd', 'j pers',
    'low back disorders', 'science and football',
    'physical fitness: a way of life',
    'the yo-yo intermittent recovery test',
]

print('Citas cuyo titulo habla de otra cosa')
print('=' * 74)
sospechas = 0
for k in sorted(cat.CATALOGO):
    esperado = DE_LA_PRUEBA.get(k)
    if not esperado:
        continue
    t = cat.CATALOGO[k]
    texto = ((t.get('bibliografia') or '') + ' ' + (t.get('fuente') or '')).split('▸')[0].lower()
    #  Fuera el nombre de la revista antes de comparar: «Journal of STRENGTH
    #  and Conditioning Research» hacia que toda prueba publicada ahi pareciera
    #  de fuerza, y «FITNESS Training in Football» que el cabeceo pareciera de
    #  resistencia. El tema hay que buscarlo en el titulo del articulo, no en
    #  donde se publico.
    for revista in PUBLICACIONES:
        texto = texto.replace(revista, ' ')
    if 'sin referencia' in texto or 'valoración observacional' in texto:
        continue

    encontrados = {tema for tema, palabras in TEMAS.items()
                   if any(p in texto for p in palabras)}
    if not encontrados:
        continue                       # el titulo no dice el tema: no se juzga
    if esperado in encontrados:
        continue                       # coincide
    if any((esperado, e) in COMPATIBLES for e in encontrados):
        continue
    #  Citas de dos partes: «el protocolo es de X, los valores de referencia
    #  son de Y». El tema de Y no tiene por que ser el de la prueba, y el
    #  propio texto ya lo explica.
    if 'valores de referencia' in texto or 'baremos de' in texto:
        continue

    sospechas += 1
    print()
    print('  %s · %s' % (k, t['nombre']))
    print('     la prueba mide:  %s' % esperado)
    print('     el titulo habla de: %s' % ', '.join(sorted(encontrados)))
    print('     cita: %s' % ((t.get('bibliografia') or t.get('fuente') or '').split('▸')[0].strip()[:150]))

print()
print('%d sospecha(s) para mirar a mano.' % sospechas)
