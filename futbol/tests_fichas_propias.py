# -*- coding: utf-8 -*-
"""La ficha larga de las 18 pruebas que no venían de la biblioteca avalada.

Las 40 de `tests_biblioteca.py` traen su protocolo y su bibliografía tal como
se publicaron. Estas 18 son pruebas de uso corriente —el Cooper, la plancha,
las dominadas, los perfiles de observación— que en el catálogo tenían solo una
línea de protocolo y ningún detalle: la ficha salía vacía y el entrenador que
no conociera la prueba no tenía de dónde agarrarse.

Este texto lo escribimos NOSOTROS a partir del protocolo estándar de cada
prueba, así que estas NO se marcan como avaladas: la insignia queda para las
que tienen protocolo publicado. La cita que ya tenía cada una en `fuente` se
mantiene y es la que se enseña como procedencia.

Los VALORES NORMATIVOS solo se rellenan donde la cifra es estándar y
comprobable —la fórmula del Cooper, la física de la regla que cae—. Donde no
lo es se deja vacío a propósito: un número inventado en una ficha es peor que
un hueco, porque el hueco se nota y el número no.
"""

FICHAS_PROPIAS = {

    # ═══════════════════════ FÍSICAS ═══════════════════════

    'abalakov': {
        'objetivo': 'Medir la potencia del tren inferior aprovechando el impulso '
                    'de los brazos, que es como se salta de verdad en un partido: '
                    'a rematar, a despejar y a disputar un balón dividido.',
        'material': 'Alfombra de contacto, plataforma de fuerzas o app de vídeo a '
                    'cámara lenta. Como alternativa, pared lisa y tiza para medir '
                    'la diferencia entre el alcance de pie y el del salto.',
        'protocolo_detallado':
            'El jugador se coloca de pie, sin carrera previa. Baja libremente hasta '
            'la flexión que le resulte natural —no se le marca una profundidad— y '
            'sube con toda la potencia acompañando con los dos brazos. Se exige '
            'caer en el mismo sitio y con las rodillas flexionadas. Tres intentos '
            'con un minuto de descanso entre ellos y se anota el mejor. La '
            'diferencia con el CMJ, que se hace con las manos en la cadera, indica '
            'cuánto sabe aprovechar el braceo: lo normal es de 4 a 8 cm más.',
        'variables': 'Altura del salto (cm). Comparada con el CMJ, además, el '
                     'aporte del braceo (cm y %).',
    },

    'abdominales_30s': {
        'objetivo': 'Valorar la resistencia de la musculatura abdominal, que es la '
                    'que sostiene la postura al golpear, al girar y al frenar.',
        'material': 'Colchoneta, cronómetro y un compañero que sujete los pies.',
        'protocolo_detallado':
            'Tumbado boca arriba, rodillas dobladas a 90 grados, pies apoyados y '
            'sujetos por un compañero, y las manos en las sienes sin entrelazar los '
            'dedos detrás de la cabeza. A la señal sube hasta tocar las rodillas con '
            'los codos y baja hasta que la espalda vuelve a tocar la colchoneta: si '
            'no baja del todo, esa repetición no cuenta. Se cronometran 30 segundos '
            'exactos y se anotan las repeticiones completas. Un solo intento.',
        'variables': 'Repeticiones completas en 30 segundos.',
    },

    'antropometria': {
        'objetivo': 'Tener la talla, el peso y la composición corporal para leer el '
                    'resto de pruebas con cabeza: la misma marca no significa lo '
                    'mismo en un chaval que ha pegado el estirón que en uno que no.',
        'material': 'Tallímetro o cinta métrica fija a la pared, báscula y, si se '
                    'mide la grasa, plicómetro (lipocalibre).',
        'protocolo_detallado':
            'Talla descalzo, de espaldas a la pared, con talones, glúteos y espalda '
            'en contacto y la cabeza mirando al frente; se mide al final de una '
            'inspiración. Peso en ropa ligera y descalzo, a la misma hora del día '
            'siempre que se pueda, porque a lo largo de la jornada varía. El '
            'porcentaje de grasa se estima con pliegues cutáneos, siempre en el lado '
            'derecho y repitiendo cada pliegue dos veces: si las dos medidas se '
            'separan más de un 5%, se toma una tercera. Conviene que lo mida siempre '
            'la misma persona, porque la técnica del plicómetro cambia bastante de '
            'unas manos a otras.',
        'variables': 'Talla (cm), peso (kg) y porcentaje de grasa corporal (%).',
        'normativa': 'En futbolistas varones adultos el porcentaje de grasa suele '
                     'moverse entre el 8 y el 12%. En formación es normal que sea '
                     'más alto y no debe interpretarse como un problema.',
    },

    'cooper': {
        'objetivo': 'Estimar la capacidad aeróbica máxima con una prueba de campo '
                    'que no necesita más que una pista y un cronómetro.',
        'material': 'Pista o circuito medido —lo habitual es una pista de atletismo '
                    'de 400 m—, cronómetro y conos cada 50 o 100 m para poder afinar '
                    'la distancia final.',
        'protocolo_detallado':
            'Calentamiento de 10 minutos. El jugador corre durante 12 minutos '
            'intentando cubrir la mayor distancia posible; puede andar si lo '
            'necesita, pero no parar. Se avisa del tiempo que queda a los 6 minutos, '
            'a los 3 y en el último minuto. Al sonar el final se detiene en el sitio '
            'y se mide la distancia hasta el último cono pasado. Es una prueba '
            'máxima: conviene no hacerla el día antes de competir y no tomarla con '
            'jugadores que arrastren molestias.',
        'variables': 'Distancia recorrida en 12 minutos (m). De ahí se estima el '
                     'VO₂ máx (ml/kg/min).',
        'normativa': 'VO₂ máx estimado = (distancia en metros − 504,9) / 44,73. '
                     'Un futbolista adulto entrenado suele cubrir entre 2800 y '
                     '3400 m, lo que equivale a unos 51-65 ml/kg/min.',
    },

    'plancha': {
        'objetivo': 'Medir la resistencia de la musculatura que estabiliza el tronco, '
                    'la que evita que la cadera se descuelgue al final del partido.',
        'material': 'Colchoneta y cronómetro.',
        'protocolo_detallado':
            'Apoyo sobre los antebrazos y las puntas de los pies, codos justo debajo '
            'de los hombros, cuerpo formando una línea recta de la cabeza a los '
            'talones. El cronómetro arranca cuando la postura está montada. Se para '
            'en cuanto la cadera cae, se eleva en punta o el jugador apoya las '
            'rodillas, y se le avisa una sola vez para que corrija antes de dar la '
            'prueba por terminada. Un intento por sesión: repetirla el mismo día no '
            'da una medida comparable.',
        'variables': 'Tiempo aguantado con la postura correcta (s).',
    },

    'reaccion': {
        'objetivo': 'Estimar el tiempo de reacción visual, que es lo que separa '
                    'llegar y no llegar a un balón dividido.',
        'material': 'Regla rígida de 30 cm o regla de reacción graduada en '
                    'milisegundos.',
        'protocolo_detallado':
            'El jugador se sienta con el antebrazo apoyado en la mesa y la mano '
            'fuera del borde, con el pulgar y el índice abiertos unos 3 cm. El '
            'evaluador sujeta la regla en vertical con el cero a la altura de los '
            'dedos y la suelta sin avisar y sin cuenta atrás, dejando un tiempo '
            'irregular entre un intento y otro para que no se anticipe. Se anota el '
            'centímetro por el que la agarra. Tres intentos de prueba y cinco '
            'válidos; se promedian los cinco y se descarta cualquiera en el que se '
            'haya adelantado.',
        'variables': 'Distancia de caída (cm), convertible a tiempo de reacción (s).',
        'normativa': 'El tiempo sale de la caída libre: t = √(2d/g). 15 cm son unos '
                     '0,175 s y 20 cm unos 0,20 s. En adultos jóvenes lo corriente '
                     'está entre 15 y 21 cm.',
    },

    'sprint_10m': {
        'objetivo': 'Medir la capacidad de arranque, que es el tramo que más se '
                    'repite en un partido: la mayoría de los esprints de fútbol no '
                    'llegan a los 20 metros.',
        'material': 'Células fotoeléctricas o cronómetro manual, 10 m medidos y '
                    'conos.',
        'protocolo_detallado':
            'Salida de parado, con el pie adelantado justo detrás de la línea y sin '
            'balanceo previo. No se da señal de salida: el jugador arranca cuando '
            'quiere y el cronómetro se dispara con su primer movimiento, para que el '
            'tiempo de reacción no ensucie la marca. Tres intentos con 3 minutos de '
            'descanso y se anota el mejor. Con cronómetro manual el error ronda las '
            'dos décimas, que en 10 metros es mucho: si se toma a mano, conviene '
            'compararse siempre consigo mismo y no con el baremo.',
        'variables': 'Tiempo en 10 m (s).',
    },

    'sprint_20m': {
        'objetivo': 'Medir la aceleración en la distancia en la que se resuelven la '
                    'mayoría de las disputas: el desmarque, el achique y la carrera '
                    'atrás.',
        'material': 'Células fotoeléctricas o cronómetro manual, 20 m medidos y '
                    'conos.',
        'protocolo_detallado':
            'Igual que el de 10 m: salida de parado, sin señal, cronómetro al primer '
            'movimiento. Dos o tres intentos con 3 minutos de descanso entre ellos y '
            'se anota el mejor. Se toma siempre con el mismo calzado y en la misma '
            'superficie, porque el cambio de césped natural a artificial mueve la '
            'marca más que la mayoría de los planes de entrenamiento.',
        'variables': 'Tiempo en 20 m (s).',
    },

    # ═══════════════════════ TÉCNICAS ═══════════════════════

    'conduccion_conos': {
        'objetivo': 'Valorar el control del balón en conducción con cambios de '
                    'dirección continuos, con el pie y con la cabeza levantada.',
        'material': 'Ocho conos, cinta métrica, cronómetro y un balón del tamaño que '
                    'corresponda a la categoría.',
        'protocolo_detallado':
            'Ocho conos en línea separados 1,5 m, con la salida a 1,5 m del primero. '
            'El jugador conduce en zigzag hasta el último cono, lo rodea y vuelve por '
            'el mismo recorrido hasta cruzar la línea de salida. El cronómetro arranca '
            'con el primer contacto con el balón. Cada cono que se salta o que se '
            'derriba cuenta como un error, y los errores se anotan aparte en vez de '
            'sumarse al tiempo: así se distingue al que va rápido y sucio del que va '
            'limpio. Dos intentos y se anota el mejor tiempo.',
        'variables': 'Tiempo del recorrido (s) y número de errores.',
    },

    'control_orientado': {
        'objetivo': 'Valorar la calidad del primer toque: si el control deja el balón '
                    'listo para seguir jugando o hay que dar un toque de más.',
        'material': 'Un pasador, balones, cuatro conos de colores alrededor del '
                    'jugador y un espacio de unos 15×15 m.',
        'protocolo_detallado':
            'El jugador espera en el centro. El pasador le envía el balón a media '
            'altura y, en el momento del pase, le canta un color. El jugador debe '
            'controlar y salir conducido hacia ese cono. Se valora de 1 a 10 mirando '
            'tres cosas: si el primer toque va ya en la dirección pedida, si el balón '
            'queda a distancia de zancada y si el cuerpo estaba orientado antes de '
            'recibir. Diez repeticiones alternando lado y altura del pase. La nota es '
            'una valoración del cuerpo técnico, no una medición: conviene que la '
            'ponga siempre la misma persona para que las comparaciones valgan.',
        'variables': 'Valoración de 1 a 10.',
    },

    'golpeo_largo': {
        'objetivo': 'Medir el alcance y la precisión del golpeo largo, que es lo que '
                    'permite cambiar el juego de banda y sacar la presión.',
        'material': 'Balones, conos para marcar un círculo de 5 m de radio, cinta '
                    'métrica y un espacio de al menos 60 m.',
        'protocolo_detallado':
            'Se marca un círculo de 5 m de radio con el centro a 40 m del punto de '
            'golpeo. El jugador golpea cinco balones parados intentando que caigan '
            'dentro; se cuenta el bote, no dónde acaba rodando. Después se le pide un '
            'golpeo libre a máxima distancia y se mide dónde bota. Se golpea siempre '
            'con el pie dominante salvo que se quiera valorar el otro, en cuyo caso se '
            'anota aparte. Con viento a favor o en contra la distancia cambia mucho: '
            'conviene apuntarlo en las notas.',
        'variables': 'Golpeos que caen dentro del círculo (de 5) y distancia máxima (m).',
    },

    'juegos_malabares': {
        'objetivo': 'Valorar la sensibilidad con el balón y la coordinación, sobre '
                    'todo con el pie no dominante. Es una prueba de formación: dice '
                    'poco del rendimiento en partido y mucho de las horas de balón.',
        'material': 'Un balón del tamaño de la categoría y una superficie lisa.',
        'protocolo_detallado':
            'El jugador arranca con el balón en las manos, lo suelta y encadena toques '
            'sin que caiga al suelo, alternando pie derecho, pie izquierdo y muslo. No '
            'valen dos toques seguidos con la misma superficie ni el uso de la cabeza '
            'para descansar. Se cuenta hasta que el balón toca el suelo o se rompe la '
            'alternancia. Dos intentos y se anota el mejor.',
        'variables': 'Número de toques encadenados.',
    },

    'pase_precision': {
        'objetivo': 'Medir la precisión del pase raso a media distancia con el '
                    'interior del pie.',
        'material': 'Balones, dos conos separados 1 m que hagan de portería y cinta '
                    'métrica.',
        'protocolo_detallado':
            'Se plantan dos conos separados 1 m a 20 m del punto de pase. El jugador '
            'da diez pases rasos con el interior desde balón parado, intentando pasar '
            'el balón entre los dos conos. Cuenta el pase que entra entre los conos a '
            'ras de suelo; si va por alto o toca un cono, no cuenta. Se dan todos los '
            'pases con el mismo pie y se anota cuál. Repetir la prueba con el pie no '
            'dominante y guardarla aparte da una foto mucho más útil que la media de '
            'los dos.',
        'variables': 'Pases acertados de 10.',
    },

    'regate_1v1': {
        'objetivo': 'Valorar la capacidad de superar a un defensor en el uno contra '
                    'uno, que es la situación que decide los partidos igualados.',
        'material': 'Conos para delimitar un pasillo de unos 10×15 m, balones y un '
                    'defensor.',
        'protocolo_detallado':
            'Se delimita un pasillo y se marca una línea de meta al fondo. El atacante '
            'arranca con balón y el defensor sale a su encuentro. Se considera '
            'superado el uno contra uno si el atacante cruza la línea con el balón '
            'controlado. Cinco repeticiones, alternando el lado por el que ataca. Se '
            'anota cuántas supera y, aparte, una valoración de 1 a 10 sobre cómo lo '
            'hace: si engaña con el cuerpo, si protege el balón y si cambia de ritmo. '
            'Importa dejar dicho antes si el defensor va pasivo o a tope, porque la '
            'misma prueba con las dos consignas no se puede comparar.',
        'variables': 'Uno contra unos superados (de 5) y valoración de 1 a 10.',
    },

    'tiros_porteria': {
        'objetivo': 'Medir la precisión del remate, premiando el tiro a las zonas '
                    'donde el portero no llega.',
        'material': 'Portería reglamentaria, balones y cinta o conos para señalar las '
                    'zonas de puntuación.',
        'protocolo_detallado':
            'Se divide la portería en zonas: las dos escuadras valen 3 puntos, la '
            'franja junto a cada palo 2 puntos y el centro 1 punto. El jugador tira '
            'cinco balones parados desde el borde del área. Solo puntúa el tiro que '
            'entra; el que se va fuera o lo para el portero vale cero. Se anotan dos '
            'cosas: los puntos sumados y los goles, porque un jugador puede meter '
            'cinco y sumar poco si todos van al centro. Con portero o sin él cambia '
            'mucho el resultado: hay que hacerlo siempre igual.',
        'variables': 'Puntuación total (de 15) y goles (de 5).',
    },

    # ═══════════════════════ MENTALES Y DE OBSERVACIÓN ═══════════════════════

    'checkin_diario': {
        'objetivo': 'Detectar pronto la fatiga acumulada y los bajones de ánimo, que '
                    'se ven antes preguntando que esperando a que aparezcan en el '
                    'rendimiento.',
        'material': 'Ninguno. Se pregunta al llegar al entrenamiento, antes de '
                    'calentar.',
        'protocolo_detallado':
            'Tres preguntas de 1 a 10 al empezar la sesión: cómo se encuentra de '
            'energía, con cuántas ganas viene y qué tal ha dormido. Se pregunta '
            'siempre a la misma hora y antes de entrenar, nunca después, porque el '
            'propio entrenamiento cambia la respuesta. Lo que importa no es el número '
            'de un día suelto sino la caída respecto a la media del propio jugador: '
            'una bajada sostenida de dos o tres puntos durante varios días avisa antes '
            'que cualquier prueba física. No es un diagnóstico y no sustituye hablar '
            'con el chaval.',
        'variables': 'Energía (1-10), motivación (1-10) y calidad del sueño (1-10).',
    },

    'perfil_mental': {
        'objetivo': 'Poner por escrito lo que el cuerpo técnico ya observa del '
                    'comportamiento del jugador, para poder seguirlo en el tiempo en '
                    'vez de fiarlo a la memoria.',
        'material': 'Ninguno. Se rellena a partir de la observación en entrenamientos '
                    'y partidos.',
        'protocolo_detallado':
            'Cinco dimensiones de 1 a 10: concentración, confianza, respuesta a la '
            'presión, disciplina y liderazgo. Se rellena después de haber visto al '
            'jugador en varias sesiones y al menos un partido, nunca en caliente '
            'después de un mal día. Conviene que lo puntúe siempre la misma persona y '
            'que se revise cada uno o dos meses: lo que dice algo es el cambio, no la '
            'cifra suelta. NO es una evaluación psicológica ni sirve para detectar un '
            'problema de salud mental; si aparece algo que preocupe, lo que toca es '
            'derivar a un profesional.',
        'variables': 'Concentración, confianza, respuesta a la presión, disciplina y '
                     'liderazgo, cada una de 1 a 10.',
    },

    'perfil_tactico': {
        'objetivo': 'Registrar la lectura de juego del jugador, que es lo que peor se '
                    've en una prueba de campo y mejor se ve en un partido.',
        'material': 'Ninguno. Se rellena observando partidos, mejor con vídeo si se '
                    'tiene.',
        'protocolo_detallado':
            'Seis dimensiones de 1 a 10: colocación, toma de decisiones, lectura del '
            'juego, presión, transiciones y trabajo colectivo. Se rellena tras ver al '
            'jugador en DOS O TRES PARTIDOS, no en un entrenamiento suelto: en el '
            'entrenamiento las situaciones están dirigidas y no se ve lo mismo. Se '
            'puntúa en relación con lo que se le pide en su puesto y en su categoría, '
            'no contra un ideal abstracto. Si se puede, se revisa con vídeo antes de '
            'poner la nota, porque desde la banda se pierde la mitad del campo.',
        'variables': 'Colocación, decisión, lectura, presión, transiciones y trabajo '
                     'colectivo, cada una de 1 a 10.',
    },
}
