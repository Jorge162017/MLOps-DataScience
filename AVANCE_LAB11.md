# Laboratorio 11 — Fase 1: Tikal y Flores, Petén

Jorge Luis Lopez · 221038 · Grupo 2 · CC3066 Data Science · Universidad del Valle de Guatemala

29 de octubre de 2026

## 1. Alcance y variable de estimación

El grupo 2 desarrolla el enfoque A: triangulación de fuentes, conectividad aérea y Tikal. El pipeline genera estimaciones de enero y febrero de 2026 para El Remate Y Alrededores Lago, Isla De Flores y Mundo Maya Aeropuerto, con la definición de visitantes de la fuente de movilidad mensual. Cada sitio conserva su propia serie. No se suman los tres sitios como personas únicas de Petén: una persona puede visitar varios.

La variable de salida es el número de visitantes mensuales por destino según movilidad, con cantidades decimales válidas. No equivale a entradas internacionales, boletos de Tikal, pasajeros aéreos, operaciones aeronáuticas, pernoctaciones ni ocupación hotelera. Las fuentes se contrastan conservando sus unidades.

Las estimaciones son retrospectivas y académicas. No existen observaciones comparables de movilidad para enero-febrero de 2026; por tanto, no se calcula MAE ni RMSE de esos dos meses. La validación se realiza sobre meses con observaciones anteriores a los objetivos.

## 2. Fuentes, columnas y cobertura

Migración: hoja Datos del Excel Base_Migracion_2009-2026jun, disponible en referencias/lab1 del repositorio del Lab 10. Se utilizan Año, Mes cod, Tipo de Viajero y Viajero; la serie nacional suma exclusivamente Turista + Excursionista. Las dimensiones de clasificación forman la clave de validación. La cobertura es enero de 2009-junio de 2026; el ajuste usa solo enero de 2023-diciembre de 2025 para reducir mezcla del quiebre metodológico de 2023.

Movilidad: BD_moviidad_mensual.xlsx, hoja Peten (el nombre del archivo conserva su escritura original). Columnas destino, sub_grupo, anio, mes, pais, es_consecutivo, fecha, visitantes, dias_persona y permanencia_prom. Cobertura: septiembre-diciembre de 2025 y marzo-agosto de 2026. Faltan enero-febrero de 2026. Se agregan las filas por mes y sitio, conservando las categorías de permanencia y países sin duplicar filas de totales. No se utiliza una suma de presencias diarias.

Tikal: Peten/Visitantes_Tikal_2017-2026.xlsx, hoja Datos. Columnas año, mes, nacionales, extranjeros, otros y total. Cobertura enero de 2017-agosto de 2026. Se comprueba total = nacionales + extranjeros + otros; no se vuelve a sumar el total con los componentes. Los ceros históricos no demuestran ausencia real de visitas y generan advertencia de revisión.

AIMM consolidado: Base Consolidada, con encabezado en la tercera fila. Año, N° Mes, Tipo de Flujo, Tipo de Pasajero y Pasajeros. Cubre 2022, 2024 y 2025. Entrada y Salida se mantienen separadas; los segmentos Doméstico, Internacional y Privado se agregan una sola vez.

AIMM aerolíneas: Base de Datos, con Año, mes_numero, Aerolínea, Tipo de Flujo, Pasajeros y Total Mes Aerolínea. Cubre 2023-abril de 2026. Se suma Pasajeros por flujo; Total Mes Aerolínea está repetido en Entrada/Salida y solo se usa para validación. La reconstrucción aporta 2023, sin sumar nuevamente 2024/2025; 2026 se conserva como extensión parcial identificada.

AIMM operaciones: Base de Operaciones, encabezado en la tercera fila. Año, N° Mes, Operador, Tipo de Operación y Operaciones; enero de 2022-abril de 2026. Se separan aterrizajes y despegues y se normalizan alias TAG/T.A.G., AVIANCA/AVIATECA y AERORUTAMAYA/AERO RUTA MAYA. Cada registro mide movimientos, no pasajeros. No se incorporan cruces ni operaciones de Poptún al total de AIMM.

Ocupación: indice_ocupacion_mensual_2023_2025_1.csv; filtro departamento Petén, 36 meses continuos en 2023-2025. Columnas anio, mes, departamento e indice_ocupacion. El índice es una fracción de 0 a 1, no una cantidad de visitantes.

Capacidad: oferta_hotelera_2022_2026.csv; filtro departamento Petén, 15 filas por tipo de alojamiento en cinco cortes: cuarto trimestre de 2022, 2023, 2024 y 2025, y primer trimestre de 2026. Se conservan establecimientos, habitaciones y plazas_cama por corte. No se suman capacidades entre años ni se fabrican observaciones mensuales.

La encuesta de Petén 2025 permanece como antecedente opcional. No se extrapolan sus 500 respuestas a la población ni se calcula una probabilidad de visita a Tikal sin justificar diseño, pesos y universo.

## 3. Procedimiento, corte y reparto

Se reutiliza Holt-Winters del Lab 1: tendencia aditiva amortiguada, estacionalidad aditiva de 12 meses, inicialización estimada y ajuste optimizado. No hay búsqueda de modelos ni selección de hiperparámetros con los objetivos de 2026. Para estabilidad numérica, la serie nacional se divide entre 100000 durante el ajuste y se vuelve a su escala al pronosticar.

Corte de producción retrospectiva: diciembre de 2025. Ajuste nacional: enero de 2023-diciembre de 2025. Horizonte fijo: enero y febrero de 2026. Los datos nacionales de 2026, la movilidad de marzo-agosto de 2026, Tikal y aeropuerto posteriores al corte no participan en el ajuste ni en el factor.

Para cada sitio d se calcula factor_d = suma de movilidad_d en meses observados hasta el corte / suma de visitantes nacionales en exactamente esos meses. La estimación del sitio es factor_d × pronóstico nacional. Para los objetivos se utilizan septiembre-diciembre de 2025, cuatro meses coincidentes.

El factor es una escala empírica entre poblaciones diferentes: la movilidad incluye países como Guatemala y Migración mide entradas internacionales. No es una probabilidad ni una participación territorial identificada; no se obliga a que los factores sumen uno. Se supone provisionalmente que la estacionalidad nacional aproxima la del sitio y que la escala se conserva a corto plazo. La validación comprueba parcialmente ese supuesto, no lo demuestra.

- El Remate Y Alrededores Lago: 0.32413679, con 4 meses de calibración.
- Isla De Flores: 0.34376044, con 4 meses de calibración.
- Mundo Maya Aeropuerto: 0.39456831, con 4 meses de calibración.

Los parámetros de nivel, tendencia, estacionalidad, amortiguamiento, escala numérica, factores, numeradores, denominadores y períodos quedan guardados. Las versiones de dependencias y la semilla 221038 se registran; el ajuste no requiere muestreo aleatorio.

## 4. Validación temporal y regla de aceptación

Validación nacional: enero-diciembre de 2025, con seis cortes y horizontes fijos de uno/dos meses. Cada ajuste termina antes del bloque evaluado. Referencia: mismo mes del año anterior. Se evalúan exactamente los mismos 12 meses para ambos procedimientos.

Validación de destinos: octubre-diciembre de 2025. El primer corte es septiembre y predice octubre-noviembre sin incorporar sus observaciones; el segundo corte es noviembre y predice diciembre. La escala se vuelve a calcular solo con meses disponibles hasta cada corte. Referencia: último valor de movilidad observado antes del bloque, mantenido durante el horizonte. Cada sitio aporta tres meses distintos; no se cuentan meses repetidos como observaciones independientes.

Limitación de evaluación: antes de enero de 2026 solo hay cuatro meses de movilidad. El primer factor se estima con un mes y no existe un enero-febrero histórico del destino para reproducir esa estación. La validación tiene muestra pequeña y no acredita precisión general. Los archivos tampoco aportan versiones históricas que permitan garantizar cuándo estaban disponibles en tiempo real; la simulación respeta fechas de observación, no una disponibilidad documental demostrada.

Regla fijada antes de ejecutar: controles críticos válidos, seis estimaciones completas/finitas/no negativas y, en cada sitio, al menos tres meses evaluados y MAE del candidato menor o igual al MAE de referencia. Todos los sitios deben pasar para publicar el conjunto. El MAE se expresa en visitantes; el criterio exige no empeorar el referente sencillo. No se usa MAPE. Si la referencia tiene MAE cero se compara el MAE absoluto, sin dividir entre cero. Una muestra de tres meses sigue siendo insuficiente para garantizar utilidad operativa.

## 5. Calidad y controles funcionales

Se aplican seis controles en cada una de las ocho fuentes: 48 resultados. Cada control registra fuente, estado, cantidad de errores/advertencias y explicación. Los controles críticos detienen el pipeline antes de sustituir resultados aprobados. Un rechazo predictivo conserva los archivos candidatos para revisión.

Columnas y tipos: se exigen medidas numéricas y dimensiones textuales de cada contrato. Una columna indispensable ausente o un tipo incompatible detiene el flujo.

Fechas y cobertura: años/meses enteros válidos, consistencia fecha-año-mes y cobertura configurada. Se comprueba cobertura por sitio en movilidad y por flujo/segmento en AIMM. Enero-febrero de movilidad son huecos declarados para estimación; no ceros. Una fecha inválida o un período necesario ausente bloquea. Filas fuera de cobertura generan advertencia.

Unicidad: clave de fuente antes de agregar. Movilidad usa destino, sub_grupo, año, mes, país y categoría de permanencia; AIMM usa mes, flujo y segmento/aerolínea/operador; Tikal usa año-mes; hoteles usa departamento, período y tipo cuando corresponde. Una clave repetida bloquea aunque cambie la medida. No se eliminan duplicados silenciosamente.

Faltantes: faltantes en período, destino o medidas indispensables bloquean. En movilidad hay ocho registros sin país con conteos válidos: se conservan como país no identificado y generan advertencia, porque el análisis no estratifica por país. También hay ocho permanencias ausentes con visitantes y días-persona cero: se permiten sin calcular 0/0. No son las mismas filas. No se eliminan sus conteos ni se imputan cifras.

Valores y denominadores: negativos, infinitos y medidas críticas ausentes bloquean. La permanencia se comprueba solo con visitantes positivos; visitantes cero con días-persona positivos bloquea. La escala exige denominadores nacionales positivos en cada mes de calibración. Ocupación debe estar en [0,1].

Reglas metodológicas: no mezclar frecuencia diaria con mensual ni sumar visitantes entre sitios como únicos; no duplicar totales; comprobar componentes de Tikal; separar operaciones de pasajeros y preservar cortes de capacidad. La periodicidad declarada se respalda en procedencia y esquema; no demuestra por sí sola cómo un tercero produjo el archivo.

## 6. Triangulación y reconstrucción aérea

La reconstrucción de AIMM 2023 suma Pasajeros de aerolíneas por mes y flujo. Produce 284365 movimientos de pasajeros de Entrada + Salida en 12 meses. Esta suma no representa 284365 turistas únicos. La conciliación de 2024/2025 entre consolidado y aerolíneas tiene diferencia cero; las fuentes se comparan, no se suman. La serie resultante identifica fuente y año reconstruido y añade enero-abril de 2026 como cobertura parcial de aerolíneas.

Los operadores se entregan en dos tablas independientes: pasajeros por aerolínea/flujo y operaciones por operador/aterrizaje-despegue. No se convierte un vuelo en un pasajero ni se infiere ocupación de aeronave. Las denominaciones privadas de ambas fuentes no se enlazan automáticamente como si fueran un operador idéntico.

Triangulación: por mes se contrastan boletos de Tikal, movilidad por sitio, pasajeros de entrada AIMM e índice de ocupación disponible. La capacidad se entrega en una tabla independiente por corte. No se extrapola la ocupación después de 2025 ni se rellenan períodos sin cobertura.

Se reporta 100 × boletos_Tikal / visitantes_del_sitio como razón descriptiva entre fuentes, separando denominadores observados de estimados candidatos. No es el porcentaje de personas de Petén que compró boleto: no hay enlace individual y existen diferencias de población, repetición y cobertura. No se fuerza la razón a [0,100] ni se suman los tres sitios para fabricar un denominador regional. La fracción de compradores únicos requiere datos enlazados o un diseño adicional que estas fuentes no aportan.

Los datos observados de Tikal de enero-febrero de 2026 pueden contextualizar retrospectivamente esos meses, pero no validar el número de visitantes de movilidad ni entrar al pronóstico anterior al corte.

## 7. Diagrama y ejecución

Ver `diagrama_flujo.svg` y el diagrama del PDF.

Comando desde la raíz: python pipeline.py. Cada ejecución escribe configuración efectiva, huellas SHA-256 de las ocho fuentes y del código, versiones, estado de Git, inicio/final, etapas, controles, tablas preparadas, evaluación, parámetros, factores y seis estimaciones. No requiere memoria de un notebook ni editar archivos intermedios.

La salida está en resultados_peten/ejecuciones/<run_id>/. Esa carpeta es independiente de resultados/, que conserva el antecedente nacional; sus versiones aprobadas no se confunden con Petén. Solo se actualiza resultados_peten/aprobada.json si todos los sitios pasan. La candidata actual no se publica. La conexión de este contrato con Streamlit, MLflow, monitoreo y Docker corresponden a la fase 2.

## 8. Resultados y evidencia de la fase 1

Estado de la candidata conjunta: REJECTED. Los controles de datos no tienen fallos críticos; el rechazo se debe a desempeño en El Remate y Flores. No se modificó el umbral para aprobarla.

| Destino | MAE candidato | MAE referencia | Decisión |
| --- | --- | --- | --- |
| El Remate Y Alrededores Lago | 13,021.16 | 12,571.72 | Rechazado |
| Isla De Flores | 14,214.90 | 8,901.06 | Rechazado |
| Mundo Maya Aeropuerto | 10,776.16 | 14,297.58 | Aceptado |

El componente nacional obtuvo MAE 14198.62 frente a 16241.42 de la referencia estacional, sobre 12 meses. Eso no garantiza que la escala territorial conserve la precisión.

Las siguientes seis cifras son estimaciones candidatas, no aprobadas para el tablero y sin error observado comparable en enero-febrero:

| Destino | Período | Visitantes candidatos |
| --- | --- | --- |
| El Remate Y Alrededores Lago | 2026-01 | 100,503.58 |
| El Remate Y Alrededores Lago | 2026-02 | 90,129.47 |
| Isla De Flores | 2026-01 | 106,588.19 |
| Isla De Flores | 2026-02 | 95,586.02 |
| Mundo Maya Aeropuerto | 2026-01 | 122,341.95 |
| Mundo Maya Aeropuerto | 2026-02 | 109,713.66 |

Se verificaron dos ejecuciones completas con datos/configuración idénticos: diferencia numérica máxima cero en estimaciones y evaluaciones (tolerancia absoluta 1e-8, relativa cero). Los identificadores y fechas cambian por diseño.

Se introdujo una clave duplicada en una copia real del Excel mensual. El pipeline detectó mobility/unicidad, terminó FAILED antes de evaluar y no generó métricas. No cambió el manifiesto aprobado existente ni creó uno para la candidata rechazada. La prueba sintética automatizada también verifica la conservación de una versión previa.

Hay 15 pruebas automatizadas aprobadas, incluyendo contratos de las ocho fuentes, cobertura por sitio, tipos, fechas fraccionarias, duplicados con valor distinto, ceros/faltantes permitidos, negativos/no finitos, coherencia de Tikal, separación de unidades, reconstrucción 2023, ausencia de fuga temporal y fallo seguro. Los detalles, identificadores y métricas están en evidencia_avance.json y en las carpetas locales de ejecución.
