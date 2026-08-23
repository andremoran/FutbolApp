# -*- coding: utf-8 -*-
"""
futbol/tests_biblioteca.py — La ficha larga de las 40 pruebas avaladas.

ESTE ARCHIVO ESTÁ GENERADO. No editar a mano: sale de `_emitir_bloque_c.py`,
que lee las 40 plantillas de `evaluation_templates` (las mismas que muestra la
app nativa en «Biblioteca de tests»).

`tests_catalogo.py` fusiona esto con `setdefault`, así que lo que una prueba ya
traía del MVP NO se pisa: la descripción y el protocolo que el entrenador ya
conoce siguen literales, y solo se le añaden los campos que antes no existían.

De las 40, trece ya estaban en el catálogo midiendo lo mismo y se enriquecen en
su sitio; las otras veintisiete se dan de alta en el bloque C del catálogo.
"""

BIBLIOTECA = {
    'abdominales_60s': {
        'nombre_biblioteca': 'Resistencia Abdominal (NSCA/ACSM)',
        'objetivo': 'Evaluar la resistencia muscular del core y su capacidad de proteger '
        'la columna durante el juego.',
        'material': 'Colchoneta, cronómetro, asistente para fijar pies.',
        'protocolo_detallado': 'El jugador en decúbito supino, rodillas a 90°, pies en el suelo, '
        'manos sobre los muslos. Sube el tronco deslizando las manos hasta '
        'que los dedos toquen las rodillas y regresa hasta que la espalda '
        'baja toque la colchoneta. Se cuentan las repeticiones correctas en '
        '60 s. Criterios de invalidación: manos separadas de los muslos, no '
        'alcanza las rodillas, o eleva la cabeza antes que el tronco.',
        'variables': 'Número de repeticiones en 60 s.',
        'normativa': 'Bueno (20–29 años masculino): 44–49 reps. Excelente: ≥ 50 reps.',
        'bibliografia': 'ACSM. (2022). ACSM\'s Guidelines for Exercise Testing and '
        'Prescription (11th ed.). ▸ Aplicado en evaluaciones de la Liga MX, '
        'CONMEBOL y academias de Chivas de Guadalajara.',
        'descripcion': 'Resistencia muscular del core. Repeticiones en 1 minuto.',
        'protocolo': 'El jugador en decúbito supino, rodillas a 90°, pies en el suelo, '
        'manos sobre los muslos. Sube el tronco deslizando las manos hasta '
        'que los dedos toquen las rodillas y regresa hasta que la espalda '
        'baja toque la colchoneta. Se cuentan las repeticiones correctas en '
        '60 s. Criterios de invalidación: manos separadas de los muslos, no '
        'alcanza las rodillas, o eleva la cabeza antes que el tronco.',
    },

    'cabeceo_bangsbo': {
        'nombre_biblioteca': 'Cabeceo — Precisión y Distancia (Bangsbo)',
        'objetivo': 'Medir la precisión y la fuerza del cabeceo desde condiciones '
        'estáticas y en salto.',
        'material': 'Portería o zonas marcadas en pared, balones, cinta métrica.',
        'protocolo_detallado': 'Modalidad 1 — Precisión estática: desde 4 m, el evaluador lanza el '
        'balón a altura de cabeza. El jugador golpea de cabeza hacia zonas '
        'marcadas en portería (esquinas 3 pts, centro 1 pt). 5 intentos. '
        'Modalidad 2 — Distancia en salto: el evaluador realiza un saque de '
        'banda alto. El jugador salta y golpea en el punto máximo intentando '
        'enviar el balón la mayor distancia posible. Se mide la distancia del '
        'impacto al punto de caída. 5 intentos.',
        'variables': 'Puntuación de precisión (sobre 15), distancia máxima en salto (m).',
        'normativa': 'Bueno sub-18: ≥ 9/15 en precisión. Distancia en salto: > 8 m.',
        'bibliografia': 'Bangsbo, J. (1994). Fitness Training in Football — A Scientific '
        'Approach. HO+Storm. ▸ Referenciado por Selecciones de Dinamarca, '
        'Holanda y academias del PSV Eindhoven.',
        'descripcion': 'Técnica de cabeceo estático y en salto.',
        'protocolo': 'Modalidad 1 — Precisión estática: desde 4 m, el evaluador lanza el '
        'balón a altura de cabeza. El jugador golpea de cabeza hacia zonas '
        'marcadas en portería (esquinas 3 pts, centro 1 pt). 5 intentos. '
        'Modalidad 2 — Distancia en salto: el evaluador realiza un saque de '
        'banda alto. El jugador salta y golpea en el punto máximo intentando '
        'enviar el balón la mayor distancia posible. Se mide la distancia del '
        'impacto al punto de caída. 5 intentos.',
    },

    'cmj': {
        'nombre_biblioteca': 'Countermovement Jump (CMJ)',
        'objetivo': 'Cuantificar la potencia explosiva del tren inferior y monitorear la '
        'fatiga neuromuscular.',
        'material': 'Plataforma de fuerza (Kistler, AMTI) o aplicación validada (My Jump '
        '2), cinta métrica.',
        'protocolo_detallado': 'El jugador se coloca erguido con manos en caderas. Realiza un '
        'contramovimiento rápido hacia abajo (flexión de rodillas ~90°) '
        'seguido inmediatamente de un salto vertical máximo. Los brazos '
        'permanecen en cadera durante toda la ejecución para aislar el tren '
        'inferior. Tres intentos válidos con 2 min de descanso. Se registra '
        'la altura máxima de vuelo (h = g·tv²/8). Es fundamental estandarizar '
        'la profundidad del contramovimiento y verificar con video. El CMJ se '
        'usa también como marcador de fatiga: una caída >10% respecto al '
        'baseline indica fatiga neuromuscular.',
        'variables': 'Altura de salto (cm), tiempo de vuelo (ms), potencia estimada '
        '(W/kg), índice de carga (ratio CMJ/SJ).',
        'normativa': 'Élite masculino: 40–55 cm. Sub-16: 28–38 cm. Alerta fatiga: caída '
        '>10% del promedio semanal.',
        'bibliografia': 'Bosco, C., Luhtanen, P., & Komi, P.V. (1983). European Journal of '
        'Applied Physiology, 50(2), 273–282. ▸ Usado como monitoreo semanal '
        'por: Liverpool FC, Real Madrid, Manchester City, Inter de Milán.',
    },

    'conduccion_cambio_ritmo': {
        'nombre_biblioteca': 'Conducción con Cambio de Ritmo',
        'objetivo': 'Medir el control técnico durante cambios de velocidad con el balón.',
        'material': 'Conos de salida, aceleración y desaceleración, balón, fotocélulas o '
        'cronómetro.',
        'protocolo_detallado': 'El circuito tiene 3 segmentos de 10 m cada uno marcados con conos. '
        'Segmento 1 (0–10 m): conducción a máxima velocidad. Segmento 2 '
        '(10–20 m): desaceleración controlada hasta casi detenerse en la '
        'marca. Segmento 3 (20–30 m): nueva aceleración máxima. En la zona de '
        'desaceleración un evaluador señala la dirección del segmento 3 '
        '(izquierda o derecha) para agregar toma de decisión. El balón debe '
        'quedar bajo control en todo el recorrido. Tiempo total cronometrado.',
        'variables': 'Tiempo total (s), balones perdidos (número), cambio de dirección '
        'correcto (sí/no).',
        'normativa': 'Bueno sub-18: < 8,5 s sin perder el balón. Élite: < 7,5 s con '
        'decisión correcta.',
        'bibliografia': 'Stølen, T. et al. (2005). Sports Medicine, 35(6), 501–536. ▸ '
        'Incorporado en el modelo de entrenamiento técnico del RB Leipzig, '
        'Red Bull Salzburg y academias del grupo Red Bull.',
        'descripcion': 'Aceleración-desaceleración con balón y toma de decisión.',
        'protocolo': 'El circuito tiene 3 segmentos de 10 m cada uno marcados con conos. '
        'Segmento 1 (0–10 m): conducción a máxima velocidad. Segmento 2 '
        '(10–20 m): desaceleración controlada hasta casi detenerse en la '
        'marca. Segmento 3 (20–30 m): nueva aceleración máxima. En la zona de '
        'desaceleración un evaluador señala la dirección del segmento 3 '
        '(izquierda o derecha) para agregar toma de decisión. El balón debe '
        'quedar bajo control en todo el recorrido. Tiempo total cronometrado.',
    },

    'conduccion_circuito_30s': {
        'nombre_biblioteca': 'Conducción en Circuito Cerrado 30 s',
        'objetivo': 'Medir la resistencia técnica y la velocidad de conducción en '
        'circuito repetido.',
        'material': 'Circuito marcado de ~15 m perimetro (4 conos en cuadrado de 4 × 4 m '
        'aproximadamente), balón, cronómetro.',
        'protocolo_detallado': 'El jugador conduce el balón alrededor del circuito cuadrado (4 × 4 '
        'm) a máxima velocidad durante 30 s. Se cuentan las vueltas completas '
        'más los metros adicionales. Se puede variar la dirección '
        '(horaria/antihoraria) para trabajar ambos perfiles de giro. Se '
        'registra el número de vueltas completas + fracción. La diferencia '
        'entre sentido horario y antihorario indica preferencia lateral en la '
        'conducción.',
        'variables': 'Número de vueltas completas en 30 s, diferencia entre sentidos.',
        'normativa': 'Bueno sub-18: ≥ 4 vueltas en 30 s. Élite: ≥ 5 vueltas.',
        'bibliografia': 'Impellizzeri, F.M. et al. (2008). Level of competition and '
        'soccer-specific fitness of under-17 players. Int. J. Sports '
        'Medicine, 29(7), 575–582. ▸ Utilizado en academias del Udinese '
        'Calcio, Selección Sub-17 de Italia y programas del CONI.',
        'descripcion': 'Resistencia técnica y control bajo fatiga repetida.',
        'protocolo': 'El jugador conduce el balón alrededor del circuito cuadrado (4 × 4 '
        'm) a máxima velocidad durante 30 s. Se cuentan las vueltas completas '
        'más los metros adicionales. Se puede variar la dirección '
        '(horaria/antihoraria) para trabajar ambos perfiles de giro. Se '
        'registra el número de vueltas completas + fracción. La diferencia '
        'entre sentido horario y antihorario indica preferencia lateral en la '
        'conducción.',
    },

    'conduccion_recta': {
        'nombre_biblioteca': 'Velocidad de Conducción Línea Recta',
        'objetivo': 'Evaluar la velocidad máxima de conducción y el diferencial respecto '
        'al sprint sin balón.',
        'material': '30 m medidos, fotocélulas o cronómetro, conos, balón reglamentario.',
        'protocolo_detallado': 'El jugador conduce el balón en línea recta a máxima velocidad desde '
        'la línea de salida hasta los 30 m. El balón debe permanecer bajo '
        'control en todo momento (no se permiten golpes largos sin control). '
        'Tres intentos con 3–4 min de recuperación. Se compara con el tiempo '
        'del sprint libre (sin balón). El diferencial entre conducción y '
        'sprint libre indica el costo técnico-velocidad. Un mayor diferencial '
        'señala menor eficiencia técnica a alta velocidad.',
        'variables': 'Tiempo conducción 30 m (s), diferencial respecto sprint libre (s).',
        'normativa': 'Élite adulto: conducción < 5,2 s. Diferencial aceptable: < 0,5 s.',
        'bibliografia': 'Reilly, T., & Holmes, M. (1983). Physical Education Review, 6(1), '
        '64–71. ▸ Referenciado en la Universidad de Liverpool y usado por '
        'academias del Liverpool FC y Everton FC.',
        'descripcion': 'Sprint técnico con balón. Compara con sprint libre.',
        'protocolo': 'El jugador conduce el balón en línea recta a máxima velocidad desde '
        'la línea de salida hasta los 30 m. El balón debe permanecer bajo '
        'control en todo momento (no se permiten golpes largos sin control). '
        'Tres intentos con 3–4 min de recuperación. Se compara con el tiempo '
        'del sprint libre (sin balón). El diferencial entre conducción y '
        'sprint libre indica el costo técnico-velocidad. Un mayor diferencial '
        'señala menor eficiencia técnica a alta velocidad.',
    },

    'conduccion_vallas': {
        'nombre_biblioteca': 'Conducción con Vallas y Slalom',
        'objetivo': 'Medir el dominio técnico del balón en situaciones con obstáculos '
        'múltiples.',
        'material': '4 vallas (altura 40–55 cm), 4 conos para slalom, balón, cronómetro.',
        'protocolo_detallado': 'El jugador conduce hasta las vallas. Pasa el balón por encima de la '
        'primera valla, por debajo de la segunda, por encima de la tercera y '
        'por debajo de la cuarta (el jugador avanza por el lateral). A '
        'continuación conduce hasta un cono, eleva el balón y lo controla sin '
        'que toque el suelo hasta el siguiente cono. Finaliza con un slalom '
        'entre 4 conos. Se cronometra el tiempo total. Cono derribado: +0,5 '
        's. Balón perdido: se reinicia desde el último punto completado.',
        'variables': 'Tiempo total penalizado (s).',
        'normativa': 'Bueno sub-18: < 13 s. Referencia profesional: < 10 s.',
        'bibliografia': 'Reilly, T., & Holmes, M. (1983). Physical Education Review, 6(1), '
        '64–71. ▸ Adaptado y utilizado por la RFEF, CONMEBOL y en las '
        'categorías formativas del Sevilla FC.',
        'descripcion': 'Control técnico con balón bajo obstáculos múltiples.',
        'protocolo': 'El jugador conduce hasta las vallas. Pasa el balón por encima de la '
        'primera valla, por debajo de la segunda, por encima de la tercera y '
        'por debajo de la cuarta (el jugador avanza por el lateral). A '
        'continuación conduce hasta un cono, eleva el balón y lo controla sin '
        'que toque el suelo hasta el siguiente cono. Finaliza con un slalom '
        'entre 4 conos. Se cronometra el tiempo total. Cono derribado: +0,5 '
        's. Balón perdido: se reinicia desde el último punto completado.',
    },

    'course_navette': {
        'nombre_biblioteca': 'Course Navette 20 m (Léger Beep Test)',
        'objetivo': 'Estimar VO₂max y la velocidad aeróbica máxima (VAM).',
        'material': 'Espacio de 20 m, audio con pitidos Léger, conos, cronómetro.',
        'protocolo_detallado': 'El jugador corre entre dos líneas a 20 m ajustando el paso al ritmo '
        'de los pitidos. Comienza a 8,5 km/h y aumenta 0,5 km/h por minuto. '
        'El jugador debe alcanzar cada línea antes de cada pitido. Finaliza '
        'cuando no logra alcanzar dos veces seguidas. Se anota el nivel y '
        'palier final. VO₂max estimado: VO₂max = 31,025 + 3,238·V − 3,248·A + '
        '0,1536·V·A (V = velocidad último nivel, A = edad en años).',
        'variables': 'Nivel y palier completados, VAM (km/h), VO₂max estimado (ml/kg/min).',
        'normativa': 'Bueno adulto masculino: ≥ nivel 12 (12 km/h). Excelente: ≥ nivel 14.',
        'bibliografia': 'Léger, L.A., Mercier, D., Gadoury, C., & Lambert, J. (1988). Journal '
        'of Sports Sciences, 6(2), 93–101. ▸ Usado por: Real Madrid Castilla, '
        'Atletismo y Fútbol Base FIFA, selecciones nacionales sub-17 de UEFA.',
    },

    'dinamometria': {
        'nombre_biblioteca': 'Dinamometría Manual',
        'objetivo': 'Monitorear la fuerza muscular global y detectar decrementos por '
        'fatiga o lesión.',
        'material': 'Dinamómetro de mano calibrado (Jamar, Saehan o equivalente).',
        'protocolo_detallado': 'El jugador de pie, brazo dominante ligeramente separado del cuerpo '
        '(posición estándar NHANES). Agarra el dinamómetro y comprime a '
        'máxima fuerza durante 3 s. Tres intentos por mano con 1 min de '
        'descanso. Se compara con el baseline (inicio de temporada). Un '
        'decremento > 10% respecto a la línea base individual indica fatiga '
        'acumulada o posible lesión.',
        'variables': 'Fuerza prensión mano dominante y no dominante (kg), asimetría (%).',
        'normativa': 'Adulto masculino deportista: 50–65 kg. Caída > 10% del baseline = '
        'alerta.',
        'bibliografia': 'Leyk, D. et al. (2007). European Journal of Applied Physiology, '
        '99(4), 415–421. ▸ Utilizado en seguimiento de carga por Brighton & '
        'Hove Albion, Brentford FC y clubes de la Eredivisie holandesa.',
        'descripcion': 'Fuerza muscular general como marcador de estado global.',
        'protocolo': 'El jugador de pie, brazo dominante ligeramente separado del cuerpo '
        '(posición estándar NHANES). Agarra el dinamómetro y comprime a '
        'máxima fuerza durante 3 s. Tres intentos por mano con 1 min de '
        'descanso. Se compara con el baseline (inicio de temporada). Un '
        'decremento > 10% respecto a la línea base individual indica fatiga '
        'acumulada o posible lesión.',
    },

    'dominio_balon_fifa': {
        'nombre_biblioteca': 'Dominio de Balón — 5 Superficies (FIFA)',
        'objetivo': 'Medir la coordinación técnica y el dominio del balón con todas las '
        'superficies.',
        'material': 'Círculo de 1 m de diámetro marcado en el suelo, 1 balón, cronómetro.',
        'protocolo_detallado': 'Dentro del círculo marcado (1 m de diámetro), el jugador realiza '
        'toques consecutivos sin dejar caer el balón al suelo usando en '
        'orden: pie derecho, pie izquierdo, muslo derecho, muslo izquierdo y '
        'cabeza. Cada ciclo completo de 5 superficies = 1 repetición. Se '
        'cuentan los ciclos completos en 60 s. También se registra la racha '
        'máxima de toques consecutivos. Penalización: si el jugador sale del '
        'círculo se anula el ciclo en curso.',
        'variables': 'Ciclos completos en 60 s, racha máxima de toques.',
        'normativa': 'Bueno sub-16: ≥ 5 ciclos en 60 s. Avanzado: ≥ 10 ciclos. Élite: '
        'control sostenido > 60 toques.',
        'bibliografia': 'FIFA. (2014). Grassroots Football Manual — Technical Skill '
        'Assessment Protocols. Zurich: FIFA. ▸ Parte del currículo de las '
        'Academias FIFA, implementado en ligas de desarrollo de: Brasil '
        '(CBF), Argentina (AFA) y México (FMF).',
        'descripcion': 'Control de balón con diferentes superficies corporales. Avalado por '
        'FIFA.',
        'protocolo': 'Dentro del círculo marcado (1 m de diámetro), el jugador realiza '
        'toques consecutivos sin dejar caer el balón al suelo usando en '
        'orden: pie derecho, pie izquierdo, muslo derecho, muslo izquierdo y '
        'cabeza. Cada ciclo completo de 5 superficies = 1 repetición. Se '
        'cuentan los ciclos completos en 60 s. También se registra la racha '
        'máxima de toques consecutivos. Penalización: si el jugador sale del '
        'círculo se anula el ciclo en curso.',
    },

    'dribbling_fpf': {
        'nombre_biblioteca': 'Dribbling Speed Test (FPF)',
        'objetivo': 'Medir velocidad y control técnico de conducción con giros.',
        'material': '6 conos en línea separados 2 m, balón reglamentario, cronómetro o '
        'fotocélula.',
        'protocolo_detallado': 'Se colocan 6 conos en línea separados 2 m entre sí. El jugador '
        'conduce el balón en slalom (zigzag) hasta el último cono, lo rodea '
        'completamente y regresa en slalom hasta la salida. El balón debe '
        'pasar limpiamente entre cada cono. Cono derribado: penalización de '
        '0,5 s por cono o repetición del intento. 3 intentos con 3 min de '
        'recuperación. Se puede ejecutar con pierna dominante, no dominante y '
        'libre para detectar asimetrías técnicas.',
        'variables': 'Tiempo total (s), asimetría dominante/no dominante (s).',
        'normativa': 'Élite sub-18 masculino: < 8,5 s. Bueno: 8,5–9,5 s. Deficiente: > '
        '10,5 s.',
        'bibliografia': 'Federação Portuguesa de Futebol — FPF. (2017). Bateria de testes '
        'técnicos para futebol formativo. Lisboa: FPF. ▸ Usado en detección '
        'de talentos por: SL Benfica, Sporting CP, FC Porto, Selección de '
        'Portugal Sub-17.',
        'descripcion': 'Conducción de balón con cambios de dirección. Estándar de FPF '
        '(Portugal).',
        'protocolo': 'Se colocan 6 conos en línea separados 2 m entre sí. El jugador '
        'conduce el balón en slalom (zigzag) hasta el último cono, lo rodea '
        'completamente y regresa en slalom hasta la salida. El balón debe '
        'pasar limpiamente entre cada cono. Cono derribado: penalización de '
        '0,5 s por cono o repetición del intento. 3 intentos con 3 min de '
        'recuperación. Se puede ejecutar con pierna dominante, no dominante y '
        'libre para detectar asimetrías técnicas.',
    },

    'golpeo_porteria_ali': {
        'nombre_biblioteca': 'Golpeo a Portería (Ali — Loughborough)',
        'objetivo': 'Medir la precisión del disparo y diferencias entre pierna dominante '
        'y no dominante.',
        'material': 'Portería dividida en 6 zonas con cuerdas, 10 balones, radar de '
        'velocidad (opcional), conos a 16,5 m.',
        'protocolo_detallado': 'La portería (7,32 × 2,44 m) se divide en 6 zonas: 4 esquinas = 3 '
        'puntos; 2 zonas centrales = 1 punto. El jugador dispara desde 16,5 m '
        '(línea del área). 10 disparos: 5 con pierna dominante y 5 con no '
        'dominante. Balón fuera de portería = 0 pts. El balón debe estar bajo '
        'el larguero para ser válido. Se registra velocidad con radar si está '
        'disponible. Se calcula la suma total (máximo 30 pts) y el '
        'diferencial entre piernas.',
        'variables': 'Puntuación total (sobre 30), velocidad de disparo (km/h), '
        'diferencial por pierna.',
        'normativa': 'Profesional: ≥ 24/30. Bueno sub-18: ≥ 18/30. Velocidad élite adulto: '
        '90–110 km/h.',
        'bibliografia': 'Ali, A., Williams, C., Hulse, M. et al. (2007). Journal of Sports '
        'Sciences, 25(13), 1461–1470. ▸ Implementado por: Stoke City, Norwich '
        'City FC y academias de la Football Association (FA) de Inglaterra.',
        'descripcion': 'Precisión y potencia de tiro con zonas de puntuación validadas.',
        'protocolo': 'La portería (7,32 × 2,44 m) se divide en 6 zonas: 4 esquinas = 3 '
        'puntos; 2 zonas centrales = 1 punto. El jugador dispara desde 16,5 m '
        '(línea del área). 10 disparos: 5 con pierna dominante y 5 con no '
        'dominante. Balón fuera de portería = 0 pts. El balón debe estar bajo '
        'el larguero para ser válido. Se registra velocidad con radar si está '
        'disponible. Se calcula la suma total (máximo 30 pts) y el '
        'diferencial entre piernas.',
    },

    'ift_30_15': {
        'nombre_biblioteca': '30-15 Intermittent Fitness Test (30-15IFT)',
        'objetivo': 'Determinar la velocidad aeróbica intermitente máxima (VIFT) para '
        'prescripción de entrenamiento.',
        'material': 'Pista de 40 m (dos zonas: 15 m + 10 m + 15 m), audio oficial '
        '30-15IFT, conos.',
        'protocolo_detallado': 'El jugador alterna 30 s de carrera y 15 s de recuperación caminando '
        'dentro de una zona de 3 m. La velocidad de carrera comienza a 8 km/h '
        'y aumenta 0,5 km/h cada minuto. El test finaliza cuando el jugador '
        'no logra alcanzar la zona de recuperación durante los 15 s. Se '
        'registra la velocidad de la última etapa completada como VIFT. Esta '
        'velocidad se usa directamente para programar zonas de entrenamiento.',
        'variables': 'VIFT (km/h), predicción de VO₂max.',
        'normativa': 'Élite adulto masculino: VIFT 19–21 km/h. Sub-18 bueno: 17–19 km/h.',
        'bibliografia': 'Buchheit, M. (2008). The 30-15 Intermittent Fitness Test: accuracy '
        'for individualizing interval training. Journal of Strength and '
        'Conditioning Research, 22(2), 365–374. ▸ Usado por: Paris '
        'Saint-Germain, Sevilla FC, selecciones nacionales de Francia y '
        'Australia.',
        'descripcion': 'Resistencia intermitente diseñada por Buchheit. Sensible a cambios '
        'en temporada.',
        'protocolo': 'El jugador alterna 30 s de carrera y 15 s de recuperación caminando '
        'dentro de una zona de 3 m. La velocidad de carrera comienza a 8 km/h '
        'y aumenta 0,5 km/h cada minuto. El test finaliza cuando el jugador '
        'no logra alcanzar la zona de recuperación durante los 15 s. Se '
        'registra la velocidad de la última etapa completada como VIFT. Esta '
        'velocidad se usa directamente para programar zonas de entrenamiento.',
    },

    'illinois': {
        'nombre_biblioteca': 'Illinois Agility Test',
        'objetivo': 'Evaluar agilidad funcional avanzada y coordinación dinámica.',
        'material': '8 conos, espacio 10 × 5 m, cronómetro.',
        'protocolo_detallado': 'Circuito de 10 × 5 m con 4 conos centrales separados 3,3 m. El '
        'jugador comienza tumbado boca abajo (decúbito prono), manos al nivel '
        'de los hombros. A la señal se levanta, sprint inicial 10 m, giro, '
        'slalom de ida y vuelta entre 4 conos centrales, giro y sprint de '
        'regreso de 10 m. Cono derribado = repetición del intento. Mejor '
        'tiempo de 2–3 intentos válidos.',
        'variables': 'Tiempo total (s).',
        'normativa': 'Élite masculino: < 15,2 s. Bueno: 15,2–16,1 s. Deficiente: > 17 s.',
        'bibliografia': 'Roozen, M. (2004). NSCA\'s Performance Training Journal, 3(5), 5–6. '
        '▸ Usado por: academias de Arsenal FC, Villarreal CF y selecciones '
        'juveniles de la CONMEBOL.',
    },

    'juego_aereo': {
        'nombre_biblioteca': 'Juego Aéreo — Duelos de Cabeza',
        'objetivo': 'Medir la efectividad en el juego aéreo con y sin oponente.',
        'material': 'Balones, lanzador (o máquina de lanzamiento), conos para zonas, '
        'oponente pasivo.',
        'protocolo_detallado': 'El evaluador lanza el balón alto (simula un centro o balón '
        'dividido). El jugador debe saltar para ganar el duelo de cabeza, '
        'enviando el balón a una zona de 3 × 3 m marcada. Primero sin '
        'oponente (5 intentos) para medir el timing puro; luego con un '
        'oponente pasivo que salta al mismo tiempo (5 intentos) para medir la '
        'ventaja posicional. Se evalúa: balón enviado a zona = éxito; fuera '
        'de zona = fallo. Se registra también la altura del salto si se usa '
        'plataforma.',
        'variables': 'Duelos ganados sin oponente (sobre 5), duelos ganados con oponente '
        '(sobre 5), altura de salto técnico (cm).',
        'normativa': 'Bueno sub-18: ≥ 3/5 con oponente. Élite: ≥ 4/5.',
        'bibliografia': 'Bangsbo, J. (1994). Fitness Training in Football. HO+Storm. ▸ '
        'Incluido en evaluaciones de: Selección Alemana Sub-21, Hamburgo SV y '
        'en el modelo de desarrollo del Hertha BSC.',
        'descripcion': 'Dominio del juego aéreo: timing y salto técnico.',
        'protocolo': 'El evaluador lanza el balón alto (simula un centro o balón '
        'dividido). El jugador debe saltar para ganar el duelo de cabeza, '
        'enviando el balón a una zona de 3 × 3 m marcada. Primero sin '
        'oponente (5 intentos) para medir el timing puro; luego con un '
        'oponente pasivo que salta al mismo tiempo (5 intentos) para medir la '
        'ventaja posicional. Se evalúa: balón enviado a zona = éxito; fuera '
        'de zona = fallo. Se registra también la altura del salto si se usa '
        'plataforma.',
    },

    'list_test': {
        'nombre_biblioteca': 'Loughborough Intermittent Shuttle Test (LIST)',
        'objetivo': 'Simular la demanda metabólica real de un partido y evaluar la '
        'resistencia específica.',
        'material': 'Pista de 20 m marcada con conos a distintas distancias, audio '
        'oficial LIST.',
        'protocolo_detallado': 'El test alterna caminar (3,5 km/h), trotar (55% VO₂max), correr (95% '
        'VO₂max) y sprints máximos según el audio. Se realizan bloques de 15 '
        'min separados por descansos cortos. Se puede aplicar versión '
        'completa de 90 min o versión reducida de 45 min. Se registra el '
        'tiempo total que el jugador puede mantener el protocolo completo. '
        'También se mide el rendimiento en sprint (tiempo de cada sprint a lo '
        'largo del test) para detectar el punto de inflexión de la fatiga.',
        'variables': 'Tiempo total de mantenimiento (min), tiempo de sprint por bloque '
        '(s), decremento de sprint.',
        'normativa': 'Élite completa (90 min): sin fallos en sprint. Descenso > 5% en '
        'sprint = fatiga significativa.',
        'bibliografia': 'Nicholas, C.W. et al. (1995). Journal of Sports Sciences, 13(6), '
        '474–481. ▸ Desarrollado en Loughborough University y adoptado por la '
        'Federación Inglesa (FA) y el Stoke City FC.',
        'descripcion': 'Simulación de partido completo. Resistencia específica intermitente.',
        'protocolo': 'El test alterna caminar (3,5 km/h), trotar (55% VO₂max), correr (95% '
        'VO₂max) y sprints máximos según el audio. Se realizan bloques de 15 '
        'min separados por descansos cortos. Se puede aplicar versión '
        'completa de 90 min o versión reducida de 45 min. Se registra el '
        'tiempo total que el jugador puede mantener el protocolo completo. '
        'También se mide el rendimiento en sprint (tiempo de cada sprint a lo '
        'largo del test) para detectar el punto de inflexión de la fatiga.',
    },

    'lspt': {
        'nombre_biblioteca': 'Loughborough Soccer Passing Test (LSPT)',
        'objetivo': 'Evaluar la precisión y el timing del pase corto.',
        'material': '8 conos en cuadrado de 4 m, postes de rebote o compañero, '
        'cronómetro.',
        'protocolo_detallado': 'El jugador realiza pases de precisión alrededor de un circuito con '
        'conos destino marcados en el suelo. Cada pase que no llega al '
        'objetivo suma una penalización de 0,5 s. Se cronometra el tiempo '
        'total en completar 16 pases alternando piernas (o con la preferida '
        'según variante). Se suman las penalizaciones al tiempo base. Versión '
        'más simple: pase contra pared marcada con zona objetivo (60 × 60 cm) '
        'desde 5 m, 20 repeticiones, se cuenta el número de impactos precisos '
        'en 30 s.',
        'variables': 'Tiempo total + penalizaciones (s), o número de pases precisos / '
        'tiempo.',
        'normativa': 'Élite: tiempo total < 28 s sin penalización. Bueno: < 35 s.',
        'bibliografia': 'Ali, A. et al. (2007). Journal of Sports Sciences, 25(13), '
        '1461–1470. ▸ Referenciado en academias de: Manchester United, West '
        'Ham United y en los estudios de la Federación Española de Fútbol '
        '(RFEF).',
    },

    'margaria_kalamen': {
        'nombre_biblioteca': 'Margaria-Kalamen (Escalera)',
        'objetivo': 'Medir la potencia mecánica anaeróbica del tren inferior.',
        'material': 'Escalera de ≥ 6 escalones, fotocélulas en escalones 3 y 9, báscula.',
        'protocolo_detallado': 'El jugador inicia desde el escalón 1 y sube corriendo lo más rápido '
        'posible de 3 en 3 escalones. El tiempo se mide entre los escalones '
        'marcados (fotocélulas o cronómetro manual). Cálculo: P = (masa × g × '
        'h) / t, donde h = altura vertical de los escalones medidos. '
        'Convertir: P (W) = P(kgm/s) × 9,81. Tres intentos con 5 min de '
        'recuperación. Mayor potencia registrada.',
        'variables': 'Potencia (W), potencia relativa (W/kg).',
        'normativa': 'Futbolistas buenos: 1500–1800 W. Élite: > 1800 W. Relativo: > 22 '
        'W/kg.',
        'bibliografia': 'Kalamen, J. (1968). Doctoral Dissertation, The Ohio State '
        'University. ▸ Referenciado en protocolos del INEF de Madrid y '
        'academias de América y Cruz Azul (México).',
        'descripcion': 'Potencia mecánica anaeróbica explosiva del tren inferior.',
        'protocolo': 'El jugador inicia desde el escalón 1 y sube corriendo lo más rápido '
        'posible de 3 en 3 escalones. El tiempo se mide entre los escalones '
        'marcados (fotocélulas o cronómetro manual). Cálculo: P = (masa × g × '
        'h) / t, donde h = altura vertical de los escalones medidos. '
        'Convertir: P (W) = P(kgm/s) × 9,81. Tres intentos con 5 min de '
        'recuperación. Mayor potencia registrada.',
    },

    'pared_primer_toque': {
        'nombre_biblioteca': 'Pared — Pases de Primer Toque',
        'objetivo': 'Medir la velocidad y precisión del pase de primera toque.',
        'material': 'Pared de rebote o compañero a 3–5 m, zona objetivo marcada de 1 × 1 '
        'm, cronómetro.',
        'protocolo_detallado': 'El jugador se coloca a 3–5 m de la pared con zona objetivo marcada. '
        'A la señal, realiza pases de primera (sin amortiguar) contra la zona '
        'lo más rápido posible durante 30 s. Se cuentan los impactos precisos '
        'dentro de la zona objetivo. El balón que no rebota adecuadamente '
        '(sale muy alto, lejos) no se cuenta. Pausa si el jugador pierde el '
        'control del balón. Se registra el total de toques precisos en 30 s.',
        'variables': 'Toques precisos en 30 s.',
        'normativa': 'Bueno sub-18: ≥ 20 toques precisos. Élite: ≥ 28 toques. Profesional: '
        '≥ 34 toques.',
        'bibliografia': 'Grehaigne, J.F., Bouthier, D., & David, B. (1997). Dynamic-system '
        'analysis of opponent relationships in collective actions in soccer. '
        'Journal of Sports Sciences, 15(2), 137–149. ▸ Variante utilizada por '
        'el Olympique de Marsella, RC Lens y escuelas de fútbol de la Liga '
        'Francesa.',
        'descripcion': 'Velocidad de ejecución y primer toque contra pared/rebote.',
        'protocolo': 'El jugador se coloca a 3–5 m de la pared con zona objetivo marcada. '
        'A la señal, realiza pases de primera (sin amortiguar) contra la zona '
        'lo más rápido posible durante 30 s. Se cuentan los impactos precisos '
        'dentro de la zona objetivo. El balón que no rebota adecuadamente '
        '(sale muy alto, lejos) no se cuenta. Pausa si el jugador pierde el '
        'control del balón. Se registra el total de toques precisos en 30 s.',
    },

    'pase_largo_precision': {
        'nombre_biblioteca': 'Pase Largo — Precisión y Distancia',
        'objetivo': 'Medir la precisión y la distancia del pase largo con ambas piernas.',
        'material': 'Campo de fútbol, zonas marcadas con conos (radios de 1, 2 y 3 m), '
        'cinta métrica.',
        'protocolo_detallado': 'Se marcan tres zonas concéntricas a distintas distancias: corta '
        '(20–30 m), media (30–40 m) y larga (> 40 m). El jugador realiza 3 '
        'pases a cada zona (9 en total), intentando que el balón ruede o bote '
        'dentro del cono central (radio de 1 m = 3 pts, radio 2 m = 2 pts, '
        'radio 3 m = 1 pt). Se ejecuta con pierna dominante y no dominante. '
        'Total máximo: 27 puntos.',
        'variables': 'Puntuación total (sobre 27), asimetría entre piernas.',
        'normativa': 'Bueno: ≥ 16/27. Excelente: ≥ 22/27. Diferencia entre piernas ≤ 3 pts '
        '= equilibrio aceptable.',
        'bibliografia': 'Haaland, E., & Hoff, J. (2003). Non-dominant leg training improves '
        'the bilateral motor performance of soccer players. Scandinavian '
        'Journal of Medicine & Science in Sports, 13(3), 179–184. ▸ Usado por '
        'Borussia Dortmund, Selección Noruega y academias de la Eredivisie.',
        'descripcion': 'Cambio de orientación. Clave para defensas y mediocampistas.',
        'protocolo': 'Se marcan tres zonas concéntricas a distintas distancias: corta '
        '(20–30 m), media (30–40 m) y larga (> 40 m). El jugador realiza 3 '
        'pases a cada zona (9 en total), intentando que el balón ruede o bote '
        'dentro del cono central (radio de 1 m = 3 pts, radio 2 m = 2 pts, '
        'radio 3 m = 1 pt). Se ejecuta con pierna dominante y no dominante. '
        'Total máximo: 27 puntos.',
    },

    'penalti_test': {
        'nombre_biblioteca': 'Penalti — Velocidad, Precisión y Presión',
        'objetivo': 'Evaluar la calidad técnica del tiro desde el punto de penalti y la '
        'respuesta bajo presión.',
        'material': 'Portería dividida en 9 zonas, 10 balones, radar de velocidad '
        '(opcional), cronómetro.',
        'protocolo_detallado': 'El jugador coloca el balón en el punto de penalti (11 m). Realiza 10 '
        'disparos: primero 5 sin presión (solo el portero o sin portero) y '
        'luego 5 con presión simulada (ruido de la tribuna, evaluador cerca, '
        'tiempo limitado de 10 s para disparar desde que se señala la zona '
        'objetivo). Las zonas superiores e inferiores de las esquinas valen 3 '
        'pts; zonas intermedias 2 pts; zonas centrales 1 pt. Se registra '
        'también si el jugador cambia de zona tras presión.',
        'variables': 'Puntuación total (sobre 30), tiempo de decisión (s), variación de '
        'zona bajo presión.',
        'normativa': 'Profesional: ≥ 26/30. Bueno: ≥ 20/30. Variación de zona bajo presión '
        '= señal de ansiedad técnica.',
        'bibliografia': 'Wilson, M.R. et al. (2009). Anxiety, attentional control, and '
        'performance impairment in penalty kicks. J. Sport and Exercise '
        'Psychology, 31(6), 761–775. ▸ Adoptado en laboratorios de '
        'rendimiento de: Chelsea FC, Southampton FC y la KNVB (Holanda).',
        'descripcion': 'Tiro al arco desde penalti con factor psicológico.',
        'protocolo': 'El jugador coloca el balón en el punto de penalti (11 m). Realiza 10 '
        'disparos: primero 5 sin presión (solo el portero o sin portero) y '
        'luego 5 con presión simulada (ruido de la tribuna, evaluador cerca, '
        'tiempo limitado de 10 s para disparar desde que se señala la zona '
        'objetivo). Las zonas superiores e inferiores de las esquinas valen 3 '
        'pts; zonas intermedias 2 pts; zonas centrales 1 pt. Se registra '
        'también si el jugador cambia de zona tras presión.',
    },

    'rast': {
        'nombre_biblioteca': 'RAST (Running-based Anaerobic Sprint Test)',
        'objetivo': 'Cuantificar potencia anaeróbica y resistencia al agotamiento '
        'metabólico.',
        'material': '35 m con fotocélulas, báscula para masa corporal.',
        'protocolo_detallado': 'El jugador realiza 6 sprints máximos de 35 m con 10 s de '
        'recuperación pasiva. Se registra el tiempo de cada sprint. Cálculos '
        'por sprint: Velocidad (v) = 35/t. Aceleración (a) = v/t. Fuerza (F) '
        '= masa × a. Potencia (P) = F × v. Con todos los valores se obtienen '
        'Potencia Máxima, Potencia Mínima, Potencia Media e Índice de Fatiga '
        '(IF) = (Pmáx − Pmín) / Tiempo Total. Un IF alto indica alta '
        'fatigabilidad anaeróbica.',
        'variables': 'Potencia máxima (W), potencia mínima (W), potencia media (W), IF '
        '(W/s).',
        'normativa': 'Potencia máxima élite: > 900 W. IF aceptable: < 10 W/s.',
        'bibliografia': 'Zacharogiannis, E., Paradisis, G., & Tziortzis, S. (2004). Medicine '
        'and Science in Sports and Exercise, 36(5), S116. ▸ Usado por: '
        'Flamengo, Santos FC, River Plate y otros clubes de Sudamérica en '
        'pretemporada.',
        'descripcion': 'Potencia anaeróbica e índice de fatiga con 6 sprints de 35 m.',
        'protocolo': 'El jugador realiza 6 sprints máximos de 35 m con 10 s de '
        'recuperación pasiva. Se registra el tiempo de cada sprint. Cálculos '
        'por sprint: Velocidad (v) = 35/t. Aceleración (a) = v/t. Fuerza (F) '
        '= masa × a. Potencia (P) = F × v. Con todos los valores se obtienen '
        'Potencia Máxima, Potencia Mínima, Potencia Media e Índice de Fatiga '
        '(IF) = (Pmáx − Pmín) / Tiempo Total. Un IF alto indica alta '
        'fatigabilidad anaeróbica.',
    },

    'recepcion_orientada': {
        'nombre_biblioteca': 'Recepción y Control Orientado',
        'objetivo': 'Medir la precisión y velocidad del control orientado del balón.',
        'material': 'Zona marcada de 2 × 2 m a 5 m, 10 balones, compañero evaluador o '
        'pared de rebote.',
        'protocolo_detallado': 'El evaluador lanza el balón (5 rodados + 5 aéreos) desde 8–10 m. El '
        'jugador debe controlar con el primer toque orientando el balón '
        'dentro de la zona marcada (2 × 2 m). Éxito si el balón queda en la '
        'zona con máximo dos contactos. Se contabiliza el número de controles '
        'exitosos sobre 10 intentos. Se puede añadir presión de tiempo (< 2 s '
        'para controlar y orientar).',
        'variables': 'Controles exitosos / 10 intentos, tiempo de reacción.',
        'normativa': 'Excelente: ≥ 8/10. Bueno: 6–7/10. Deficiente: < 5/10.',
        #  La cita que traia —Castagna et al. (2006), JSCR 20(2), 320-325—
        #  corresponde a «Aerobic fitness and yo-yo continuous and intermittent
        #  tests performances in soccer players»: un trabajo sobre FITNESS
        #  AEROBICO, no sobre recepcion ni control orientado. Mismo caso que el
        #  saque de banda, y se le da el mismo trato: fuera la cita, que las
        #  academias si valen y se quedan.
        'bibliografia': 'Sin referencia publicada propia: el protocolo es de uso '
        'corriente pero no procede de un estudio concreto. ▸ Incluido en '
        'protocolos técnicos de las academias de Feyenoord, RB Leipzig y '
        'Selección Sub-17 de España.',
        'descripcion': 'Primer toque orientado, con balón rodado y aéreo.',
        'protocolo': 'El evaluador lanza el balón (5 rodados + 5 aéreos) desde 8–10 m. El '
        'jugador debe controlar con el primer toque orientando el balón '
        'dentro de la zona marcada (2 × 2 m). Éxito si el balón queda en la '
        'zona con máximo dos contactos. Se contabiliza el número de controles '
        'exitosos sobre 10 intentos. Se puede añadir presión de tiempo (< 2 s '
        'para controlar y orientar).',
    },

    'recepcion_pivot': {
        'nombre_biblioteca': 'Recepción en Movimiento — Pivot',
        'objetivo': 'Medir la calidad técnica del primer toque en situaciones de '
        'recepción con giro.',
        'material': '3 conos en triángulo (radio 3 m), 10 balones, compañero o lanzador.',
        'protocolo_detallado': 'El jugador comienza de espaldas al lanzador. A la señal, gira 180° y '
        'recibe el pase del lanzador (desde 8–10 m). Debe controlar y '
        'orientar el balón hacia el cono objetivo designado por el evaluador '
        '(cambia en cada intento). Se evalúa si el primer toque orienta '
        'correctamente el balón hacia el objetivo (sí/no). Diez intentos. '
        'También se puede cronometrar el tiempo desde el giro hasta que el '
        'balón queda orientado (< 1,5 s = óptimo).',
        'variables': 'Controles orientados correctamente / 10, tiempo de orientación (s).',
        'normativa': 'Bueno: ≥ 7/10 correctos. Excelente: ≥ 9/10. Tiempo óptimo: < 1,5 s.',
        'bibliografia': 'Dellal, A. et al. (2011). Comparison of technical performances of '
        'players in the top five European professional soccer league '
        'tournaments. Journal of Sports Medicine and Physical Fitness, 51(4), '
        '690–700. ▸ Utilizado en Olympique Lyonnais, Selección Sub-20 de '
        'Francia y el INSEP (Instituto Nacional del Deporte, Francia).',
        'descripcion': 'Recepción con giro y control orientado tras pivote.',
        'protocolo': 'El jugador comienza de espaldas al lanzador. A la señal, gira 180° y '
        'recibe el pase del lanzador (desde 8–10 m). Debe controlar y '
        'orientar el balón hacia el cono objetivo designado por el evaluador '
        '(cambia en cada intento). Se evalúa si el primer toque orienta '
        'correctamente el balón hacia el objetivo (sí/no). Diez intentos. '
        'También se puede cronometrar el tiempo desde el giro hasta que el '
        'balón queda orientado (< 1,5 s = óptimo).',
    },

    'regate_1vs0': {
        'nombre_biblioteca': 'Regate 1vs0 con Finta Obligatoria',
        'objetivo': 'Medir la capacidad de regate con cambio de dirección y calidad del '
        'amague.',
        'material': '5 conos separados 2 m, 1 maniquí o cono grande central, balón, '
        'cronómetro.',
        'protocolo_detallado': 'El jugador conduce el balón en slalom entre 5 conos, realiza una '
        'finta real frente al maniquí (amague obligatorio, evaluado por el '
        'juez), sortea por el lado indicado y finaliza con un pase a zona '
        'delimitada. Penalizaciones: tocar el maniquí (+1 s), finta '
        'inexistente según juez (+1 s), cono derribado (+0,5 s). Tres '
        'intentos, mejor tiempo penalizado. El juez evalúa la finta en escala '
        '1–3 (3 = engaño de centro de gravedad real).',
        'variables': 'Tiempo total penalizado (s), puntuación de calidad de finta (1–3).',
        'normativa': 'Bueno sub-18: < 10 s sin penalización. Finta calidad 3 = estándar '
        'élite.',
        'bibliografia': 'Rampinini, E. et al. (2009). J. Science and Medicine in Sport, '
        '12(1), 227–233. ▸ Variante usada en academias del Inter de Milán, '
        'Valencia CF y en los estudios técnicos del Barça Innovation Hub.',
        'descripcion': 'Habilidad de regate y destreza con balón bajo velocidad.',
        'protocolo': 'El jugador conduce el balón en slalom entre 5 conos, realiza una '
        'finta real frente al maniquí (amague obligatorio, evaluado por el '
        'juez), sortea por el lado indicado y finaliza con un pase a zona '
        'delimitada. Penalizaciones: tocar el maniquí (+1 s), finta '
        'inexistente según juez (+1 s), cono derribado (+0,5 s). Tres '
        'intentos, mejor tiempo penalizado. El juez evalúa la finta en escala '
        '1–3 (3 = engaño de centro de gravedad real).',
    },

    'rsa': {
        'nombre_biblioteca': 'RSA Test (Repeated Sprint Ability)',
        'objetivo': 'Medir la fatiga en sprints máximos repetidos con recuperación '
        'parcial.',
        'material': '30–40 m medidos, células fotoeléctricas, conos.',
        'protocolo_detallado': 'Protocolo estándar: 6 sprints de 30–40 m con 20–25 s de recuperación '
        'pasiva entre cada uno. Posición inicial estática. Se registra el '
        'tiempo de cada sprint. Cálculos: Tiempo Ideal (TI) = mejor tiempo × '
        'n° sprints; Tiempo Total (TT) = suma de todos; Porcentaje de '
        'Decremento (PD%) = [(TT − TI) / TI] × 100. Un PD% bajo indica alta '
        'capacidad RSA. Un PD% > 5–8% señala bajo rendimiento en sprint '
        'repetido.',
        'variables': 'Tiempo por sprint (s), mejor tiempo, PD%.',
        'normativa': 'Élite: PD% < 3%. Bueno: 3–5%. Deficiente: > 8%.',
        'bibliografia': 'Girard, O., Mendez-Villanueva, A., & Bishop, D. (2011). Sports '
        'Medicine, 41(8), 673–694. ▸ Implementado por: Atlético de Madrid, '
        'Tottenham Hotspur, Selección de Brasil, Napoli.',
    },

    'salto_horizontal': {
        'nombre_biblioteca': 'Salto Horizontal (Broad Jump)',
        'objetivo': 'Evaluar potencia explosiva en el plano horizontal y detectar '
        'asimetrías.',
        'material': 'Suelo liso, cinta métrica, chalk o línea de referencia.',
        'protocolo_detallado': 'El jugador se coloca de pie detrás de la línea de salida con pies '
        'juntos o separados al ancho de hombros. Realiza un contramovimiento '
        'con balanceo de brazos y salta lo más lejos posible aterrizando con '
        'ambos pies. Se mide desde la línea de salida hasta el talón más '
        'cercano en el punto de aterrizaje. Tres intentos, mejor resultado. '
        'Variante unipodal: salto con cada pierna por separado para detectar '
        'asimetrías (diferencia > 15 cm = alerta).',
        'variables': 'Distancia de salto (cm), asimetría entre piernas (%).',
        'normativa': 'Bueno adulto masculino: > 220 cm. Élite: > 250 cm. Asimetría máxima '
        'aceptable: < 15%.',
        'bibliografia': 'Meylan, C. et al. (2009). J. Strength and Conditioning Research, '
        '23(9), 2674–2681. ▸ Incluido en el protocolo de evaluación del Ajax '
        'Cape Town y las academias de la MLS.',
    },

    'saque_banda': {
        'nombre_biblioteca': 'Saque de Banda — Distancia y Precisión',
        'objetivo': 'Evaluar la distancia máxima y la precisión del saque de banda.',
        'material': 'Campo de fútbol, cinta métrica, conos para marcar zonas de '
        'precisión.',
        'protocolo_detallado': 'El jugador realiza el saque de banda con técnica reglamentaria '
        '(ambos pies en el suelo o con carrera permitida según categoría). '
        'Para la distancia: se mide el punto de caída del balón en el suelo. '
        'Para la precisión: se marcan 3 zonas en el campo (cerca: 0–15 m, '
        'media: 15–25 m, larga: > 25 m) y el jugador debe enviar el balón a '
        'la zona indicada en 5 intentos por zona. Cinco intentos para '
        'distancia máxima. Se registra la mayor distancia y el porcentaje de '
        'acierto por zona.',
        'variables': 'Distancia máxima (m), precisión por zona (% de aciertos).',
        'normativa': 'Profesional adulto: > 30 m. Bueno sub-18: > 20 m. Precisión zona '
        'media: ≥ 4/5.',
        #  La cita que traia aqui —Kollath & Quade, «Measurement of sprinting
        #  speed of professional and amateur soccer players»— es de un estudio
        #  sobre VELOCIDAD DE ESPRINT y no tiene nada que ver con el saque de
        #  banda. Venia asi en el documento de origen. Se quita en vez de
        #  sustituirla: una cita equivocada es peor que ninguna, porque parece
        #  verificada y no lo esta. Los equipos que la acompañaban si valen y
        #  se quedan.
        'bibliografia': 'Sin referencia publicada propia: el protocolo es de uso '
        'corriente pero no procede de un estudio concreto. ▸ Incorporado en '
        'evaluaciones de la DFB (Federación Alemana), Selección Alemana Sub-19 '
        'y academias del Bayern München.',
        'descripcion': 'Técnica de saque de banda con medición de distancia y zonas.',
        'protocolo': 'El jugador realiza el saque de banda con técnica reglamentaria '
        '(ambos pies en el suelo o con carrera permitida según categoría). '
        'Para la distancia: se mide el punto de caída del balón en el suelo. '
        'Para la precisión: se marcan 3 zonas en el campo (cerca: 0–15 m, '
        'media: 15–25 m, larga: > 25 m) y el jugador debe enviar el balón a '
        'la zona indicada en 5 intentos por zona. Cinco intentos para '
        'distancia máxima. Se registra la mayor distancia y el porcentaje de '
        'acierto por zona.',
    },

    'sit_and_reach': {
        'nombre_biblioteca': 'Sit and Reach (Wells & Dillon)',
        'objetivo': 'Medir la extensibilidad isquiotibial y la movilidad lumbar.',
        'material': 'Cajón de Wells estandarizado (o cinta en suelo con línea a 26 cm '
        'desde los pies).',
        'protocolo_detallado': 'El jugador se sienta en el suelo, piernas extendidas, plantas de los '
        'pies planas contra el cajón. Con rodillas totalmente extendidas, '
        'desliza ambas manos hacia adelante de manera lenta (sin rebote). '
        'Mantiene la posición máxima 3 s. Tres intentos, mejor resultado. '
        'Positivo = sobrepasa la línea de los pies. Negativo = no alcanza los '
        'pies. Siempre se realiza tras calentamiento de 10 min.',
        'variables': 'Distancia alcanzada (cm), positivo o negativo respecto a referencia.',
        'normativa': 'Bueno adulto masculino: 6–20 cm. Deficiente: < 0 cm. Ideal '
        'preventivo: > 10 cm.',
        'bibliografia': 'Wells, K.F., & Dillon, E.K. (1952). Research Quarterly, 23(1), '
        '115–118. ACSM Guidelines (2022). ▸ Incluido en baterías de la FIFA y '
        'UEFA para categorías formativas.',
    },

    'sj': {
        'nombre_biblioteca': 'Squat Jump (SJ)',
        'objetivo': 'Evaluar la fuerza concéntrica pura y diferenciarla del ciclo '
        'estiramiento-acortamiento.',
        'material': 'Plataforma de salto o My Jump 2.',
        'protocolo_detallado': 'El jugador adopta posición estática de semisquat (rodillas ~90°, '
        'manos en caderas) y mantiene la posición sin movimiento durante 3 s. '
        'A la señal, salta verticalmente sin ningún contramovimiento previo. '
        'El evaluador verifica visualmente que no haya descenso antes del '
        'despegue. Tres intentos con 2 min de descanso. Se calcula el Índice '
        'de Reutilización Elástica (IRE): IRE (%) = [(CMJ − SJ) / SJ] × 100. '
        'Un IRE < 8% sugiere deficiencia en el ciclo '
        'estiramiento-acortamiento.',
        'variables': 'Altura SJ (cm), IRE (%).',
        'normativa': 'IRE normal en fútbol: 8–15%. Deficiencia: < 8%. Óptimo élite: > 12%.',
        'bibliografia': 'Bosco, C. (1994). La valoración de la fuerza con el test de Bosco. '
        'Paidotribo. ▸ Usado por: FC Barcelona, Olympique de Lyon, Bayer '
        'Leverkusen en pretemporada para diagnóstico neuromuscular.',
    },

    'sprint_30m': {
        'nombre_biblioteca': 'Sprint 10 m, 20 m y 30 m',
        'objetivo': 'Cuantificar la capacidad de aceleración (10–20 m) y velocidad máxima '
        '(30 m lanzado).',
        'material': 'Células fotoeléctricas (Brower, Fusion Sport, o Witty), 30 m '
        'medidos, conos.',
        'protocolo_detallado': 'Se colocan fotocélulas a 0, 10, 20 y 30 m. El jugador parte desde '
        'posición de pie estática (pie delantero a 30 cm de la primera '
        'fotocélula), sin señal de salida manual para evitar tiempo de '
        'reacción. El cronómetro inicia con el paso por la primera célula. '
        'Tres intentos máximos con recuperación completa de 4–5 min. Se '
        'registran los tiempos parciales de 0–10 m (aceleración inicial), '
        '10–20 m (aceleración media) y 0–30 m (velocidad máxima). Se reporta '
        'el mejor tiempo en cada tramo.',
        'variables': 'T10 m (s), T20 m (s), T30 m (s), velocidad máxima (m/s o km/h).',
        'normativa': 'Élite adulto: T10 m < 1,80 s. T30 m < 3,80 s. Velocidad máxima > 30 '
        'km/h.',
        'bibliografia': 'Little, T., & Williams, A.G. (2005). Journal of Strength and '
        'Conditioning Research, 19(1), 76–78. ▸ Usado por: Bayern München, '
        'Juventus FC, Borussia Dortmund, Chelsea FC — protocolo estándar '
        'pretemporada.',
    },

    'squat_1rm': {
        'nombre_biblioteca': '1RM Back Squat',
        'objetivo': 'Medir la fuerza máxima del tren inferior para programar el '
        'entrenamiento de fuerza.',
        'material': 'Barra olímpica, discos, jaula de sentadilla, collares de seguridad.',
        'protocolo_detallado': 'Calentamiento: 5 min aeróbico + 2 series de 10 reps con barra vacía '
        '+ 1 serie de 5 reps al 50% del estimado. Protocolo ascendente: '
        'series de 1 repetición con incrementos de 5–10% hasta el máximo con '
        'técnica correcta (espalda recta, rodillas alineadas, descenso a '
        'paralelo). Recuperación 3–5 min entre intentos. Máximo 5 intentos al '
        'límite. Estimación alternativa con fórmula de Brzycki: 1RM = '
        'peso/(1,0278 − 0,0278 × reps), usando 3–6 RM.',
        'variables': 'Carga máxima (kg), ratio 1RM / peso corporal.',
        'normativa': 'Bueno en fútbol: 1RM ≥ 1,5× peso corporal. Élite: ≥ 1,8×.',
        'bibliografia': 'Brzycki, M. (1993). JOPERD, 64(1), 88–90. ▸ Incluido en programas de '
        'fuerza de Juventus FC, Real Madrid, Manchester United y Selección '
        'Alemana (DFB).',
        'descripcion': 'Fuerza máxima del tren inferior. Estándar para programar cargas.',
        'protocolo': 'Calentamiento: 5 min aeróbico + 2 series de 10 reps con barra vacía '
        '+ 1 serie de 5 reps al 50% del estimado. Protocolo ascendente: '
        'series de 1 repetición con incrementos de 5–10% hasta el máximo con '
        'técnica correcta (espalda recta, rodillas alineadas, descenso a '
        'paralelo). Recuperación 3–5 min entre intentos. Máximo 5 intentos al '
        'límite. Estimación alternativa con fórmula de Brzycki: 1RM = '
        'peso/(1,0278 − 0,0278 × reps), usando 3–6 RM.',
    },

    't_test': {
        'nombre_biblioteca': 'T-Test de Agilidad',
        'objetivo': 'Medir la velocidad de cambio de dirección y la agilidad funcional.',
        'material': '4 conos, cinta métrica, cronómetro o fotocélula.',
        'protocolo_detallado': 'Cono A (salida) a 9,14 m del cono B (centro). Conos C y D a 4,57 m a '
        'cada lado del B formando una T. El jugador sale de A, corre hasta B, '
        'desplazamiento lateral con paso cruzado hasta C (sin cruzar pies), '
        'regresa lateralmente hasta D, vuelve al centro B, retrocede hasta A. '
        'Penalización por cruce de pies o derribo de conos. Tres intentos, '
        'mejor tiempo registrado.',
        'variables': 'Tiempo total (s).',
        'normativa': 'Excelente masculino: < 9,5 s. Bueno: 9,5–10,5 s. Deficiente: > 11,5 '
        's.',
        'bibliografia': 'Pauole, K. et al. (2000). Journal of Strength and Conditioning '
        'Research, 14(4), 443–450. ▸ Usado por: Borussia Dortmund, Valencia '
        'CF, academias de LA Galaxy y New York City FC.',
    },

    'tecnica_bajo_fatiga': {
        'nombre_biblioteca': 'Técnica Bajo Fatiga (FTT)',
        'objetivo': 'Medir el deterioro técnico causado por la fatiga física.',
        'material': 'Circuito físico (carrera de alta intensidad 4 × 40 m), zona técnica '
        'marcada, balones, cronómetro.',
        'protocolo_detallado': 'El jugador realiza primero 4 sprints de 40 m con 30 s de '
        'recuperación (fase de fatiga). Inmediatamente después (<10 s) '
        'ejecuta un test técnico estandarizado (pases cortos, tiro o '
        'control). Se comparan los resultados técnicos pre-fatiga y '
        'post-fatiga. Índice de deterioro técnico = [(resultado pre − '
        'resultado post) / resultado pre] × 100. Un índice alto indica bajo '
        'mantenimiento técnico bajo fatiga.',
        'variables': 'Resultado técnico pre y post-fatiga, índice de deterioro (%).',
        'normativa': 'Élite: deterioro técnico < 10%. Aceptable: < 20%. Preocupante: > '
        '25%.',
        'bibliografia': 'Rampinini, E., Impellizzeri, F.M., Castagna, C. et al. (2008). '
        'Technical performance during soccer matches of the Italian Serie A '
        'league. J. Science and Medicine in Sport, 12(1), 179–184. ▸ '
        'Investigado en conjunto con Chievo Verona, Atalanta y el '
        'departamento de ciencias del deporte del Inter de Milán.',
        'descripcion': 'Calidad técnica después de esfuerzo físico. Réplica del final de '
        'partido.',
        'protocolo': 'El jugador realiza primero 4 sprints de 40 m con 30 s de '
        'recuperación (fase de fatiga). Inmediatamente después (<10 s) '
        'ejecuta un test técnico estandarizado (pases cortos, tiro o '
        'control). Se comparan los resultados técnicos pre-fatiga y '
        'post-fatiga. Índice de deterioro técnico = [(resultado pre − '
        'resultado post) / resultado pre] × 100. Un índice alto indica bajo '
        'mantenimiento técnico bajo fatiga.',
    },

    'test_505': {
        'nombre_biblioteca': '505 COD Test',
        'objetivo': 'Medir la velocidad de cambio de dirección y detectar asimetrías '
        'entre pierna de giro.',
        'material': '10 m medidos, fotocélulas a 5 m, conos.',
        'protocolo_detallado': 'El jugador corre 15 m de aproximación, cruza la fotocélula de inicio '
        'a velocidad máxima, recorre 2,5 m hasta un cono, gira 180° sobre la '
        'pierna de pivote designada, regresa los 5 m hasta la fotocélula de '
        'llegada. El tiempo medido es únicamente los 5 m del tramo '
        'cronometrado (giro + regreso). Se realizan 3 intentos por pierna. '
        'Asimetría entre pierna dominante y no dominante > 0,05 s indica '
        'asimetría significativa.',
        'variables': 'Tiempo 505 COD (s) por pierna, asimetría bilateral (s).',
        'normativa': 'Élite adulto masculino: < 2,20 s. Bueno sub-18: < 2,40 s. Asimetría '
        'aceptable: < 0,05 s.',
        'bibliografia': 'Nimphius, S., McGuigan, M.R., & Newton, R.U. (2010). J. Strength and '
        'Conditioning Research, 24(10), 2681–2686. ▸ Implementado por '
        'Brentford FC, Leicester City, Ajax y selecciones de Nueva Zelanda.',
    },

    'tiro_potencia_radar': {
        'nombre_biblioteca': 'Tiro con Potencia (Radar)',
        'objetivo': 'Medir la velocidad máxima de disparo con pie dominante y no '
        'dominante.',
        'material': 'Radar de velocidad deportivo (JUGS, Bushnell o similar), portería o '
        'pared, balones.',
        'protocolo_detallado': 'El jugador coloca el balón estático a 16,5 m de la portería (o '
        'marca). Ejecuta un disparo máximo con pierna dominante. El radar '
        'mide la velocidad pico en km/h justo tras el impacto. 5 disparos con '
        'pierna dominante y 5 con no dominante con 1 min de recuperación '
        'entre cada uno. Se registra la velocidad máxima y la media de los 5 '
        'mejores. También se puede evaluar la velocidad en disparo tras '
        'conducción de 5 m (más representativo de situación de juego real).',
        'variables': 'Velocidad máxima de disparo (km/h), velocidad media (km/h), '
        'diferencial por pierna.',
        'normativa': 'Élite profesional adulto: 90–120 km/h. Sub-18 bueno: 70–85 km/h. '
        'Diferencial aceptable: < 20 km/h.',
        'bibliografia': 'Levanon, J., & Dapena, J. (1998). Comparison of the kinematics of '
        'the full-instep and pass kicks in soccer. Medicine & Science in '
        'Sports & Exercise, 30(6), 917–927. ▸ Utilizado por: Real Madrid, '
        'Napoli, Selección Italiana y en el análisis biomecánico del Barça '
        'Innovation Hub.',
        'descripcion': 'Velocidad de golpeo medida directamente con radar.',
        'protocolo': 'El jugador coloca el balón estático a 16,5 m de la portería (o '
        'marca). Ejecuta un disparo máximo con pierna dominante. El radar '
        'mide la velocidad pico en km/h justo tras el impacto. 5 disparos con '
        'pierna dominante y 5 con no dominante con 1 min de recuperación '
        'entre cada uno. Se registra la velocidad máxima y la media de los 5 '
        'mejores. También se puede evaluar la velocidad en disparo tras '
        'conducción de 5 m (más representativo de situación de juego real).',
    },

    'trapping_test': {
        'nombre_biblioteca': 'Control en Suelo — Trapping Test',
        'objetivo': 'Medir la calidad y variedad del control de balón en estático.',
        'material': '10 balones, zona objetivo de 1 × 1 m, compañero lanzador a 10–12 m.',
        'protocolo_detallado': 'El lanzador envía el balón con trayectoria específica (rodado, '
        'botado, aéreo bajo, aéreo alto). El jugador amortigua el balón con '
        'la superficie indicada previamente por el evaluador (planta, '
        'interna, externa, empeine). Éxito: el balón queda en zona de control '
        '(< 1 m del jugador), sin rebotar fuera, en máximo 2 contactos. Diez '
        'intentos, 2–3 por superficie. Evaluación binaria: éxito (1) o fallo '
        '(0).',
        'variables': 'Controles exitosos / 10, éxito por superficie.',
        'normativa': 'Bueno sub-16: ≥ 7/10. Élite sub-20: ≥ 9/10.',
        'bibliografia': 'Reilly, T., & Williams, A.M. (Eds.). (2003). Science and Soccer (2nd '
        'ed.). Routledge. ▸ Utilizado en academias de Arsenal FC, Tottenham '
        'Hotspur y la Selección de Irlanda del Norte.',
        'descripcion': 'Control estático con diferentes superficies del pie.',
        'protocolo': 'El lanzador envía el balón con trayectoria específica (rodado, '
        'botado, aéreo bajo, aéreo alto). El jugador amortigua el balón con '
        'la superficie indicada previamente por el evaluador (planta, '
        'interna, externa, empeine). Éxito: el balón queda en zona de control '
        '(< 1 m del jugador), sin rebotar fuera, en máximo 2 contactos. Diez '
        'intentos, 2–3 por superficie. Evaluación binaria: éxito (1) o fallo '
        '(0).',
    },

    'vo2max': {
        'nombre_biblioteca': 'VO₂max Directo (Ergometría)',
        'objetivo': 'Medir directamente el VO₂max con analizador de gases.',
        'material': 'Cinta ergométrica calibrada, analizador metabólico (COSMED, CORTEX '
        'MetaMax), pulsómetro.',
        'protocolo_detallado': 'Protocolo incremental (p.ej. Bruce o Balke modificado para fútbol): '
        'el jugador inicia a 8 km/h y la velocidad aumenta 1 km/h cada 2 min '
        'hasta el agotamiento. Se monitorea VO₂, FC, RER y lactato opcional. '
        'El VO₂max se confirma cuando RER > 1,10, FC ≥ FC máx teórica '
        '(220−edad) y el VO₂ no aumenta más de 2 ml/kg/min a pesar del '
        'aumento de carga.',
        'variables': 'VO₂max (ml/kg/min), umbral ventilatorio (VT1/VT2), FCmáx.',
        'normativa': 'Élite masculino fútbol: 60–70 ml/kg/min. Mediocampistas: 65–70 '
        'ml/kg/min.',
        'bibliografia': 'Stølen, T. et al. (2005). Sports Medicine, 35(6), 501–536. ▸ Usado '
        'en pretemporada por: FC Barcelona Medical Dept., Bayern München, AS '
        'Roma, Selección de Argentina.',
    },

    'y_balance': {
        'nombre_biblioteca': 'Y-Balance Test (YBT)',
        'objetivo': 'Medir equilibrio dinámico y detectar asimetrías entre piernas.',
        'material': 'Kit YBT o cinta en suelo con tres líneas a 120°, regla para medir '
        'longitud miembro inferior (LMI).',
        'protocolo_detallado': 'El jugador se coloca en la intersección de las tres líneas sobre una '
        'pierna. Con la pierna libre alcanza lo más lejos posible en '
        'dirección anterior (ANT), posteromedial (PM) y posterolateral (PL), '
        'sin apoyar el pie de alcance. El pie de apoyo no puede moverse. 3 '
        'intentos por dirección. Distancia normalizada (%) = (distancia / '
        'LMI) × 100. Score compuesto = (ANT + PM + PL) / (3 × LMI) × 100. '
        'Asimetría entre piernas en la dirección ANT > 4 cm = riesgo de '
        'lesión.',
        'variables': 'Alcance normalizado por dirección (%), score compuesto (%), '
        'asimetría (cm y %).',
        'normativa': 'Riesgo de lesión: ANT normalizado < 89% o asimetría > 4 cm entre '
        'piernas.',
        'bibliografia': 'Plisky, P.J. et al. (2006). J. Orthopaedic & Sports Physical '
        'Therapy, 36(12), 911–919. ▸ Protocolizado por los departamentos '
        'médicos de Chelsea FC, PSV Eindhoven y la Selección de USA.',
        'descripcion': 'Equilibrio dinámico unipodal. Predictor de riesgo de lesión en '
        'fútbol.',
        'protocolo': 'El jugador se coloca en la intersección de las tres líneas sobre una '
        'pierna. Con la pierna libre alcanza lo más lejos posible en '
        'dirección anterior (ANT), posteromedial (PM) y posterolateral (PL), '
        'sin apoyar el pie de alcance. El pie de apoyo no puede moverse. 3 '
        'intentos por dirección. Distancia normalizada (%) = (distancia / '
        'LMI) × 100. Score compuesto = (ANT + PM + PL) / (3 × LMI) × 100. '
        'Asimetría entre piernas en la dirección ANT > 4 cm = riesgo de '
        'lesión.',
    },

    'yoyo_ir1': {
        'nombre_biblioteca': 'Yo-Yo Intermittent Recovery Test (IR1/IR2)',
        'objetivo': 'Evaluar la capacidad de recuperación entre esfuerzos de alta '
        'intensidad y estimar VO₂max.',
        'material': 'Pista de 20 m marcada, audio oficial con pitidos (Bangsbo), conos, '
        'zona de recuperación de 5 m.',
        'protocolo_detallado': 'Se colocan dos líneas a 20 m de distancia y una zona de recuperación '
        'activa de 5 m detrás de la línea de salida. El jugador realiza '
        'carreras de ida y vuelta de 20 m siguiendo el ritmo de los pitidos, '
        'con 10 segundos de trote de recuperación entre cada par de carreras. '
        'La velocidad aumenta progresivamente. El test finaliza cuando el '
        'jugador no alcanza la línea en dos ocasiones consecutivas. IR1 '
        'comienza a 10 km/h (apto para jóvenes y amateurs); IR2 comienza a '
        '11,5 km/h (para élite). Se registra la distancia total recorrida '
        'como resultado principal.',
        'variables': 'Distancia total recorrida (m), estimación de VO₂max (fórmula Bangsbo '
        '2008).',
        'normativa': 'Élite profesional masculino: IR1 >2200 m. IR2 >1200 m. Sub-17 bueno: '
        'IR1 >1400 m.',
        'bibliografia': 'Bangsbo, J., Iaia, F.M., & Krustrup, P. (2008). The Yo-Yo '
        'Intermittent Recovery Test. Sports Medicine, 38(1), 37–51. ▸ Usado '
        'por: Liverpool FC, Manchester City, FC Barcelona, Selección Nacional '
        'de Portugal, Ajax.',
    },

}
