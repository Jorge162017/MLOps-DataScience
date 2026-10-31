# Laboratorio 11 — Informe técnico: Tikal y Flores, Petén

Jorge Luis Lopez · 221038 · Grupo 2 · CC3066 Data Science · Universidad del Valle de Guatemala

31 de octubre de 2026

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

La salida está en resultados_peten/ejecuciones/<run_id>/. Esa carpeta es independiente de resultados/, que conserva el antecedente nacional; sus versiones aprobadas no se confunden con Petén. Solo se actualiza resultados_peten/aprobada.json si todos los sitios pasan. La candidata actual no se publica. La conexión del contrato con Streamlit, MLflow, monitoreo y Docker está implementada en los módulos de la fase 2, descritos a continuación.

## 8. Resultados del procedimiento

Las cifras de esta sección corresponden a la ejecución local de macOS; las métricas Linux/Docker y sus diferencias se conservan en evidencia_fase2.json. Estado de la candidata conjunta: REJECTED. Los controles de datos no tienen fallos críticos; el rechazo se debe a desempeño en El Remate y Flores. No se modificó el umbral para aprobarla.

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

La fase 1 aporta 15 de las 26 pruebas automatizadas aprobadas, incluyendo contratos de las ocho fuentes, cobertura por sitio, tipos, fechas fraccionarias, duplicados con valor distinto, ceros/faltantes permitidos, negativos/no finitos, coherencia de Tikal, separación de unidades, reconstrucción 2023, ausencia de fuga temporal y fallo seguro. Los detalles, identificadores y métricas están en evidencia_fase2.json (sección evidencia_fase1) y en las carpetas locales de ejecución.


## 9. MLflow y trazabilidad

El experimento real se denomina Peten-Grupo2 y el experimento de demostración Peten-Grupo2-SINTETICO. El almacenamiento es local: SQLite y artefactos en mlflow_data; en Docker se conservan en /state/mlflow_data mediante el volumen lab_state.

Cada ejecución registra el ID propio y el de MLflow, fecha de inicio y fin, commit Git, estado del árbol, hashes SHA-256 del código, fuentes y configuración; rutas, coberturas, períodos, parámetros del procedimiento, regla de aceptación y versiones de dependencias. Se adjuntan controles, datos preparados, evaluación, métricas, estimaciones, factores, parámetros y monitoreo como artefactos. Los archivos permiten reproducir el cálculo sin capturas ni memoria de una sesión.

La candidata real se registra como FINISHED en MLflow y pipeline.decision=REJECTED: el procedimiento terminó, pero no autoriza publicación. Los fallos críticos se registran FAILED con su causa. Si el flujo se detuvo antes de evaluar, no se inventan MAE/RMSE. Una falla de seguimiento impide publicar; si el registro final falla después del cambio de manifiesto, se revierte el puntero y se revoca esa versión.

Se consultaron los experimentos y runs desde la API y la interfaz MLflow. El paquete local de revisión contiene la base y los artefactos completos, además del resumen evidencia_fase2.json. Las capturas complementan esos registros.

## 10. Integración con el tablero

El tablero Streamlit consulta observados.json para explorar tablas agregadas que pasaron calidad, y aprobada.json para estimaciones. Los lectores verifican rutas, hashes, metadatos, controles y aceptación. Cambiar un filtro solo vuelve a leer/representar datos; no importa ni ejecuta el ajuste.

La interfaz organiza movilidad y Tikal, conectividad aérea, alojamiento y estimaciones. Presenta evolución por sitio, componentes de boletos Tikal, pasajeros por flujo, aerolíneas, operaciones por operador, ocupación y dos vistas de capacidad. Las selecciones de año aéreo enlazan pasajeros y operaciones sin sumar sus unidades. Los meses ausentes de movilidad se insertan como huecos para no trazar una continuidad observada inventada.

En producción no hay una candidata aprobada para los tres sitios. La interfaz muestra estimaciones no disponibles y no grafica ni descarga las candidatas rechazadas como si hubieran sido aprobadas. Los observados validados siguen disponibles. No se reemplaza la falta de aprobación con resultados sintéticos.

Cuando hay una versión aprobada, se distinguen observado y estimado mediante etiquetas, línea continua/discontinua y color. Se muestran fecha de actualización, unidad, MAE y explicación de los tres meses evaluados; se advierte que no hay errores observados comparables de enero-febrero y que los sitios pueden compartir visitantes. Los parámetros y detalles de ejecución permanecen en MLflow y la documentación.

## 11. Monitoreo y publicación controlada

Actualización: se verifica el último período presente de cada fuente frente a la cobertura configurada, y los objetivos de salida frente a enero-febrero de 2026. La cobertura esperada no se sustituye por la fecha del reloj. El ejercicio es retrospectivo; el control no afirma que las fuentes estén actualizadas a octubre de 2026.

Calidad: se conservan los seis controles de las ocho fuentes y se detectan cambios en sus errores/advertencias, faltantes, duplicados y cobertura respecto al control anterior. Los faltantes descriptivos permitidos y los ceros mantienen su tratamiento documentado.

Resultados: se bloquean valores negativos o no finitos. Una variación superior al 50% frente al último observado o a una versión aprobada comparable genera alerta para revisión. El umbral identifica cambios amplios en series cortas y estacionales; no demuestra pérdida de precisión. No se calculan nuevos errores de pronóstico sin observaciones comparables.

Cada ejecución registra etapas completadas, inicio/finalización, advertencias, errores y resultado de publicación. Solo se publica una carpeta completa aprobada, con seguimiento persistido, controles válidos, integridad y aceptación predictiva. Se copian versiones inmutables con hashes; el manifiesto se sustituye atómicamente. Un bloqueo del almacén evita que pipeline y restauración compitan por el puntero.

## 12. Fallo, recuperación y restauración demostrados

Se ejecutó una prueba real con una copia del Excel de movilidad que contiene una clave duplicada: el control de unicidad detiene el flujo antes de evaluar, MLflow registra FAILED con causa y sin errores predictivos, y no se crea una aprobación real. Tras corregir la fuente, la ejecución vuelve a completar el procedimiento y mantiene REJECTED por desempeño.

Para demostrar el ciclo completo de publicación/restauración sin forzar una aprobación institucional se generaron ocho fuentes sintéticas aisladas. Se usa la misma lógica y el mismo criterio de aceptación. El proceso obtiene dos versiones aprobadas, introduce un duplicado, comprueba que el manifiesto de la segunda versión no cambia, corrige la fuente y vuelve a ejecutar. Después restaura la primera versión y el tablero vuelve a consultarla.

La demo usa directorios separados, un experimento separado y el aviso permanente DATOS SINTÉTICOS. Un entorno de producción no puede leer/restaurar esas versiones. Los resultados sintéticos no se presentan como cifras de Petén ni como prueba de precisión del modelo real.

La restauración se demuestra desde el comando versiones.py y mediante la administración local del tablero. Las pruebas de interfaz seleccionan otra versión, pulsan Restaurar versión y comprueban que cambian los datos consultados. También se prueba el rechazo de archivos alterados, candidatas rechazadas y metadatos incompletos. Una versión anterior no se sobrescribe.

## 13. Docker, persistencia y copia limpia

La imagen usa Python 3.13 fijado por digest y requirements.lock con versiones exactas. Dockerfile y .dockerignore permiten únicamente código y configuración. Los datos institucionales se montan en /datos en modo lectura y no se incluyen en la imagen. El entorno se levantó desde una copia git archive limpia, sin archivos intermedios del equipo.

Compose define tablero, MLflow, pipeline, pruebas y una demo opcional. Solo se publican puertos locales: 8501 para el tablero, 5000 para MLflow y 8502 para la demo. El volumen lab_state conserva resultados, versiones, registros y artefactos cuando se eliminan/recrean contenedores. El README documenta requisitos, fuentes, construcción, inicio, acceso, ejecución, pruebas, detención y restauración.

La prueba de persistencia compara exactamente los identificadores MLflow y el identificador de la versión restaurada antes y después de recrear los servicios sin eliminar volúmenes. Se conserva la evidencia en el paquete de revisión.

Se verificó que /app no contiene Excel ni CSV institucionales. El paquete de entrega se genera por separado con una copia consistente de SQLite, artefactos, resultados y versiones. importar_entrega.py lo extrae a una carpeta nueva y reubica las URI locales de MLflow, para revisarlo desde otro equipo sin recalcular modelos. Los archivos institucionales originales se obtienen por el canal autorizado si se desea reproducir el ajuste.

## 14. Verificación final y límites numéricos

Pasaron 26 pruebas localmente y en la imagen Docker: contratos de fuentes, aislamiento temporal, denominadores, bloqueo de publicación por falla MLflow, fallo sin métricas inventadas, versiones corruptas/rechazadas, separación de entornos, monitoreo, conservación del manifiesto y restauración desde el tablero. Las pruebas de filtros confirman que no se ajusta el modelo desde la interfaz.

Dos ejecuciones completas con la misma plataforma y configuración produjeron resultados equivalentes con tolerancia absoluta 1e-8 y relativa cero. El ajuste optimizado presenta pequeñas diferencias entre macOS y Linux; no se afirma identidad entre plataformas. La comparación cuantificada está en evidencia_fase2.json. Se mantienen los mismos umbrales y la decisión REJECTED en ambas plataformas.

La reproducción operativa no elimina las limitaciones estadísticas: solo existen tres meses de validación por sitio y cuatro de calibración final, las poblaciones de Migración y movilidad no son idénticas y los boletos no identifican compradores individuales. El observatorio mantiene estas advertencias y la separación entre observados, candidatos y aprobados.



La comparación macOS/Linux registró diferencias máximas absolutas de 0.001295 visitantes en las candidatas finales, 3.128542 en predicciones de validación de destinos y 7.324845 en la validación nacional. Son resultados observados del ajuste numérico en plataformas distintas, no tolerancias elegidas para aprobar. Dentro de Docker las diferencias entre las dos ejecuciones fueron cero con tolerancia de comprobación 1e-8. Ambas plataformas rechazan los mismos dos destinos.

La copia limpia verificada corresponde al commit de código 3844e56. Los runs reales de Docker son 20261031T172204-e0a90589 y 20261031T172257-b4cb3930. Tras recrear los servicios se conservaron exactamente los seis IDs MLflow y la versión sintética restaurada 20261031T172222-574ec0de. La importación del paquete en otra carpeta permitió consultar los seis runs y sus artefactos, y leer la versión restaurada sin recalcular.

## 15. Evidencia visual

Las capturas corresponden a los servicios locales verificados. El tablero real conserva los observados y anuncia que no hay estimaciones aprobadas. La demo de restauración está identificada como sintética. La evidencia completa de runs, métricas, archivos y estados está en el paquete MLflow y no se sustituye por imágenes.

![Tablero real](.entrega/capturas/tablero_real.png)

![Estimaciones no disponibles](.entrega/capturas/sin_estimaciones_aprobadas.png)

![Consulta de runs reales en MLflow](.entrega/capturas/mlflow_runs_reales.png)

![Versión sintética aprobada tras restauración](.entrega/capturas/demo_restauracion.png)
