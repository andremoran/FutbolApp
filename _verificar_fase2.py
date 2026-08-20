# -*- coding: utf-8 -*-
"""Fase 2 — comprobación de que el catálogo sigue en pie y las 40 puntúan."""
import sys

sys.path.insert(0, r'C:\MisApps\FutbolAppWeb')

from futbol import tests_catalogo as cat  # noqa: E402

fallos = []


def check(cond, msg):
    if not cond:
        fallos.append(msg)


# ─── 1. Nada de lo que ya existía se rompió ────────────────────────────────
check(len(cat.CLAVES_MVP) == 14, 'Las 14 del MVP: hay %d' % len(cat.CLAVES_MVP))
check(len(cat.CLAVES_AVALADAS) == 40, 'Avaladas: %d' % len(cat.CLAVES_AVALADAS))
check(len(cat.CATALOGO) == 58, 'Catálogo: %d (31 + 27)' % len(cat.CATALOGO))

#  El texto del MVP no se tocó.
sprint = cat.CATALOGO['sprint_30m']
check(sprint['descripcion'] == 'Test de velocidad pura en 30 metros',
      'La descripción del MVP cambió: %r' % sprint['descripcion'])
check(sprint['baremos']['time_seconds'][('general', 'elite')] == [4.02, 4.14, 4.27, 4.44],
      'El baremo del MVP cambió')
check(sprint.get('avalado') is True, 'Sprint 30m debería quedar marcada como avalada')
check('objetivo' in sprint, 'Sprint 30m no recibió la ficha larga')

# ─── 2. Las 40 avaladas tienen ficha completa ──────────────────────────────
for clave in sorted(cat.CLAVES_AVALADAS):
    t = cat.CATALOGO.get(clave)
    check(t is not None, 'Avalada sin entrada en el catálogo: %s' % clave)
    if not t:
        continue
    for campo in ('objetivo', 'material', 'protocolo_detallado', 'variables',
                  'normativa', 'bibliografia', 'descripcion', 'protocolo'):
        check(bool(t.get(campo)), '%s: le falta %s' % (clave, campo))

# ─── 3. Las 27 nuevas puntúan de verdad ────────────────────────────────────
NUEVAS = sorted(cat.CLAVES_AVALADAS - set(cat.CATALOGO) | set())
nuevas = [c for c in cat.CLAVES_AVALADAS
          if c not in cat.CLAVES_MVP and 'baremos' in (cat.CATALOGO.get(c) or {})]

sin_puntaje = []
for clave in sorted(cat.CLAVES_AVALADAS):
    t = cat.CATALOGO[clave]
    principal = cat.campo_principal(t)
    check(principal is not None, '%s no tiene campo principal' % clave)
    if not principal:
        continue
    #  Se puntúa el umbral «bueno» del sub-17, que es la categoría del equipo
    #  sembrado. Tiene que salir élite o bueno, nunca None.
    baremo = cat.baremo_para(clave, principal['clave'], 'sub_17', 'general')
    if not baremo:
        sin_puntaje.append('%s.%s' % (clave, principal['clave']))
        continue
    valor = baremo['cortes'][1]
    r = cat.evaluar_valor(clave, principal['clave'], valor, 'sub_17', 'general')
    check(r['nivel'] in ('elite', 'bueno'),
          '%s: el corte de «bueno» (%s) sale como %r' % (clave, valor, r['nivel']))
    check(r['puntaje'] is not None and 0 <= r['puntaje'] <= 100,
          '%s: puntaje fuera de rango: %r' % (clave, r['puntaje']))

check(not sin_puntaje, 'Sin baremo en el campo principal: %s' % sin_puntaje)

# ─── 4. La progresión no se cruza en ninguna escalera ──────────────────────
#  Las dos escaleras del baremo, de más exigente a menos. Que cada una vaya
#  siempre en su sentido no es cosmético: si el sub-17 pide más que el sub-18,
#  el mismo chico empeora de nivel al cumplir años. Pasó de verdad con el Tiro
#  con Potencia y no lo cazó ninguna comprobación anterior, porque solo se
#  miraba el sub-14 contra el profesional.
ESCALERAS = [
    [('general', 'elite'), ('general', 'profesional'),
     ('general', 'semipro'), ('general', 'amateur')],
    [('sub_18', 'general'), ('sub_17', 'general'), ('sub_16', 'general'),
     ('sub_15', 'general'), ('sub_14', 'general'), ('sub_12', 'general')],
]

#  La flexibilidad va al revés y no es un error: se pierde con el estirón y con
#  la edad, así que el ACSM le pide MÁS centímetros a un sub-15 (13) que a un
#  adulto (9). Ninguna de las 27 generadas mide flexibilidad; esta es de las
#  que ya estaban, con su baremo publicado.
SIN_ESCALERA = {'sit_and_reach'}

for clave in sorted(cat.CLAVES_AVALADAS - SIN_ESCALERA):
    t = cat.CATALOGO[clave]
    for campo, tabla in (t.get('baremos') or {}).items():
        d = cat.direccion_de(clave, campo)
        for escalera in ESCALERAS:
            pasos = [(ctx, tabla[ctx]) for ctx in escalera if ctx in tabla]
            for (ctx_a, a), (ctx_b, b) in zip(pasos, pasos[1:]):
                for i, etq in enumerate(['élite', 'bueno', 'promedio', 'débil']):
                    #  Hacia abajo en la escalera el listón afloja: en «menor
                    #  mejor» el número sube y en «mayor mejor» baja.
                    ok = a[i] <= b[i] if d == cat.MENOR else a[i] >= b[i]
                    check(ok, '%s.%s: %s de %s (%s) contra %s (%s) va al revés'
                          % (clave, campo, etq, ctx_a[0] if ctx_a[1] == 'general' else ctx_a[1],
                             a[i], ctx_b[0] if ctx_b[1] == 'general' else ctx_b[1], b[i]))

#  Y un sub-14 nunca puede pedir más que un profesional.
for clave in sorted(cat.CLAVES_AVALADAS):
    t = cat.CATALOGO[clave]
    for campo, tabla in (t.get('baremos') or {}).items():
        joven, pro = tabla.get(('sub_14', 'general')), tabla.get(('general', 'profesional'))
        if not joven or not pro or joven == pro:
            continue
        d = cat.direccion_de(clave, campo)
        ok = joven[1] >= pro[1] if d == cat.MENOR else joven[1] <= pro[1]
        check(ok, '%s.%s: el sub-14 (%s) exige más que el pro (%s)'
              % (clave, campo, joven[1], pro[1]))

# ─── 5. El resumen que ve el entrenador se arma ────────────────────────────
for clave in sorted(cat.CLAVES_AVALADAS):
    t = cat.CATALOGO[clave]
    p = cat.campo_principal(t)
    if p:
        check(bool(cat.resumen_baremo(clave, p['clave'], 'sub_17', 'general')),
              '%s: resumen de baremo vacío' % clave)

# ─── Informe ────────────────────────────────────────────────────────────────
print('Catálogo:      %d pruebas  (%d del MVP · %d avaladas de la biblioteca)'
      % (len(cat.CATALOGO), len(cat.CLAVES_MVP), len(cat.CLAVES_AVALADAS)))
por_fam = {}
for c, t in cat.CATALOGO.items():
    por_fam[t['categoria']] = por_fam.get(t['categoria'], 0) + 1
print('Por familia:   %s' % ', '.join('%s %d' % kv for kv in sorted(por_fam.items())))
aval_fam = {}
for c in cat.CLAVES_AVALADAS:
    f = cat.CATALOGO[c]['categoria']
    aval_fam[f] = aval_fam.get(f, 0) + 1
print('Avaladas:      %s' % ', '.join('%s %d' % kv for kv in sorted(aval_fam.items())))
campos_con_baremo = sum(len(t.get('baremos') or {}) for c, t in cat.CATALOGO.items()
                        if c in cat.CLAVES_AVALADAS)
print('Campos con baremo en las avaladas: %d' % campos_con_baremo)

print()
if fallos:
    print('FALLOS (%d):' % len(fallos))
    for f in fallos[:40]:
        print('  ·', f)
    sys.exit(1)
print('Sin fallos.')
