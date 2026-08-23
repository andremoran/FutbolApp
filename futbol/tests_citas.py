# -*- coding: utf-8 -*-
"""Los títulos que les faltaban a las citas.

De las 58 pruebas, 33 guardaban solo autor, año, revista y volumen —«Haugen,
Tønnessen & Seiler (2013), IJSPP 8(2):148-156»— sin el título del artículo.
Eso no es solo incomodidad: sin título no hay forma de comprobar que la cita
habla de la prueba, y así fue como el saque de banda estuvo citando un estudio
sobre velocidad de esprint sin que nadie lo notara.

Aquí van los títulos. El texto sustituye SOLO la parte de la cita: lo que
venga después del marcador «▸» —los clubes y federaciones del documento de
origen— se conserva tal cual.

QUÉ SE COMPLETÓ Y QUÉ NO
------------------------
Están las referencias que se pudieron dar por buenas: artículos conocidos y
sin ambigüedad, o comprobados uno a uno. Las que no se pudieron confirmar se
quedan como estaban y aparecen en NO_CONFIRMADAS, con el motivo. Inventar un
título es exactamente el error que se acaba de quitar del saque de banda, y
además el más difícil de detectar después, porque una cita completa parece más
fiable que una a medias.
"""

CITAS = {
    # ── Fisiología y resistencia ───────────────────────────────────────────
    'cooper':
        'Cooper, K.H. (1968). A means of assessing maximal oxygen intake: '
        'correlation between field and treadmill testing. JAMA, 203(3), 201–204.',

    'course_navette':
        'Léger, L.A., Mercier, D., Gadoury, C., & Lambert, J. (1988). The '
        'multistage 20 metre shuttle run test for aerobic fitness. Journal of '
        'Sports Sciences, 6(2), 93–101.',

    'vo2max':
        'Stølen, T., Chamari, K., Castagna, C., & Wisløff, U. (2005). Physiology '
        'of soccer: an update. Sports Medicine, 35(6), 501–536.',

    'conduccion_cambio_ritmo':
        'Stølen, T., Chamari, K., Castagna, C., & Wisløff, U. (2005). Physiology '
        'of soccer: an update. Sports Medicine, 35(6), 501–536.',

    #  Corregida: la que había —Nicholas et al. (1995), 13(6), 474–481— no es el
    #  LIST. El artículo de 1995 de Nicholas trata sobre bebida con
    #  carbohidratos y va en otras páginas. El LIST se publicó en 2000.
    'list_test':
        'Nicholas, C.W., Nuttall, F.E., & Williams, C. (2000). The Loughborough '
        'Intermittent Shuttle Test: a field test that simulates the activity '
        'pattern of soccer. Journal of Sports Sciences, 18(2), 97–104.',

    'rsa':
        'Girard, O., Mendez-Villanueva, A., & Bishop, D. (2011). Repeated-sprint '
        'ability — Part I: factors contributing to fatigue. Sports Medicine, '
        '41(8), 673–694.',

    # ── Velocidad ──────────────────────────────────────────────────────────
    'sprint_10m':
        'Haugen, T., Tønnessen, E., & Seiler, S. (2013). The difference is in the '
        'start: impact of timing and start procedure on sprint running '
        'performance. International Journal of Sports Physiology and '
        'Performance, 8(2), 148–156.',

    'sprint_20m':
        'Haugen, T., Tønnessen, E., & Seiler, S. (2013). The difference is in the '
        'start: impact of timing and start procedure on sprint running '
        'performance. International Journal of Sports Physiology and '
        'Performance, 8(2), 148–156.',

    # ── Fuerza y potencia ──────────────────────────────────────────────────
    'squat_1rm':
        'Brzycki, M. (1993). Strength testing: predicting a one-rep max from '
        'reps-to-fatigue. Journal of Physical Education, Recreation & Dance, '
        '64(1), 88–90.',

    'margaria_kalamen':
        'Kalamen, J. (1968). Measurement of maximum muscular power in man. '
        'Tesis doctoral, The Ohio State University.',

    # ── Flexibilidad ───────────────────────────────────────────────────────
    'sit_and_reach':
        'Wells, K.F., & Dillon, E.K. (1952). The sit and reach: a test of back '
        'and leg flexibility. Research Quarterly, 23(1), 115–118. Valores de '
        'referencia en ACSM Guidelines (2022).',

    # ── Técnica ────────────────────────────────────────────────────────────
    'lspt':
        'Ali, A., Williams, C., Hulse, M., Strudwick, A., Reddin, J., Howarth, '
        'L., Eldred, J., Hirst, M., & McGregor, S. (2007). Reliability and '
        'validity of two tests of soccer skill. Journal of Sports Sciences, '
        '25(13), 1461–1470.',

    'golpeo_porteria_ali':
        'Ali, A., Williams, C., Hulse, M., Strudwick, A., Reddin, J., Howarth, '
        'L., Eldred, J., Hirst, M., & McGregor, S. (2007). Reliability and '
        'validity of two tests of soccer skill. Journal of Sports Sciences, '
        '25(13), 1461–1470.',

    'conduccion_recta':
        'Reilly, T., & Holmes, M. (1983). A preliminary analysis of selected '
        'soccer skills. Physical Education Review, 6(1), 64–71.',

    'conduccion_vallas':
        'Reilly, T., & Holmes, M. (1983). A preliminary analysis of selected '
        'soccer skills. Physical Education Review, 6(1), 64–71.',

    'conduccion_conos':
        'Adaptado de Mor, D., & Christian, V. (1979). The development of a skill '
        'test battery to measure general soccer ability (Mor-Christian General '
        'Soccer Ability Skill Test Battery).',

    'pase_precision':
        'Adaptado de Mor, D., & Christian, V. (1979). The development of a skill '
        'test battery to measure general soccer ability (Mor-Christian General '
        'Soccer Ability Skill Test Battery).',

    'regate_1vs0':
        'Rampinini, E., Impellizzeri, F.M., Castagna, C., Coutts, A.J., & '
        'Wisløff, U. (2009). Technical performance during soccer matches of the '
        'Italian Serie A league: effect of fatigue and competitive level. '
        'Journal of Science and Medicine in Sport, 12(1), 227–233.',

    'tiros_porteria':
        'Adaptado de Rösch, D., Hodgson, R., Peterson, L., Graf-Baumann, T., '
        'Junge, A., Chomiak, J., & Dvorak, J. (2000). Assessment and evaluation '
        'of football performance. American Journal of Sports Medicine, '
        '28(5 Suppl), S29–S39.',

    # ── Perfiles de observación ────────────────────────────────────────────
    'perfil_mental':
        'Adaptado de Gucciardi, D.F., Hanton, S., Gordon, S., Mallett, C.J., & '
        'Temby, P. (2015). The concept of mental toughness: tests of '
        'dimensionality, nomological network, and traitness. Journal of '
        'Personality, 83(1), 26–44.',

    'perfil_tactico':
        'Adaptado de Kannekens, R., Elferink-Gemser, M.T., & Visscher, C. (2011). '
        'Positioning and deciding: key factors for talent development in soccer. '
        'Scandinavian Journal of Medicine & Science in Sports, 21(6), 846–852.',

    # ── Antropometría y baremos generales ──────────────────────────────────
    'antropometria':
        'Reilly, T., Bangsbo, J., & Franks, A. (2000). Anthropometric and '
        'physiological predispositions for elite soccer. Journal of Sports '
        'Sciences, 18(9), 669–683. Estimación de grasa según Faulkner, J.A. '
        '(1968).',

    'abalakov':
        'Protocolo de Abalakov (1938). Valores de referencia según Reilly, T., '
        'Bangsbo, J., & Franks, A. (2000). Anthropometric and physiological '
        'predispositions for elite soccer. Journal of Sports Sciences, 18(9), '
        '669–683.',

    'abdominales_30s':
        'Council of Europe (1993). EUROFIT: Handbook for the EUROFIT Tests of '
        'Physical Fitness (2ª ed.). Estrasburgo.',
}


#  Las que se quedan como estaban, y por qué. Se listan para que el hueco esté
#  documentado y no parezca un olvido.
#
#  Ya no está aquí `recepcion_orientada`: su cita resultó ser un trabajo sobre
#  fitness aeróbico y tests Yo-Yo, así que se retiró igual que la del saque de
#  banda. Las academias que la acompañaban se conservaron.
NO_CONFIRMADAS = {
    'salto_horizontal':
        'La referencia a Meylan et al. (2009), JSCR 23(9), no cuadra con las '
        'páginas 2674–2681 que figuran. No se ha podido confirmar el artículo.',

    'reaccion':
        'No se ha podido confirmar Del Rossi et al. (2014), J Athl Train 49(2), '
        '189–193. Hay trabajos de ese autor sobre tiempo de reacción clínico, '
        'pero de otros años.',

    'test_505':
        'La referencia a Nimphius, McGuigan & Newton (2010) no se ha comprobado '
        'una por una; el test 505 en sí procede de Draper & Lancaster (1985).',

    'conduccion_circuito_30s':
        'La cita de Impellizzeri et al. (2008) es un trabajo sobre condición '
        'física específica en sub-17. Encaja de forma razonable, pero no es el '
        'protocolo del circuito en sí.',
}
