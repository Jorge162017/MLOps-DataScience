# Laboratorio 11 — Alcance y avance

Jorge Luis Lopez · 221038 · Grupo 2 · Data Science · Universidad del Valle de Guatemala

29 de octubre de 2026 · Avance: alcance, diagrama, pipeline inicial y controles de calidad funcionales.

## 1. Propósito y continuidad con el Lab 10

Automatizar fuera de Streamlit la lectura de la fuente mensual, su validación, preparación, ajuste de un procedimiento ya utilizado, evaluación y generación de resultados trazables. El tablero permite consultar el panorama nacional de visitantes. La futura conexión consumirá archivos aprobados; los filtros no volverán a ajustar el modelo.

Este avance implementa la serie nacional de visitantes. La estimación territorial requiere el destino y el factor de reparto indicados en la asignación del grupo 2; los totales nacionales no se presentan como afluencia de un destino.

## 2. Variable, fuente, granularidad y supuestos

**Variable:** visitantes mensuales = suma de `Viajero` de las filas cuyo `Tipo de Viajero` es Turista o Excursionista. Unidad: visitantes; puede contener decimales de estimaciones expandidas. Son entradas, no personas únicas.

**Fuente:** `Lab10-DataScience/referencias/lab1/Laboratorio 1. Series de Tiempo 2026 - Base_Migracion_2009-2026jun.xlsx`, hoja `Datos`, con notas metodológicas en `Notas`. Cobertura esperada: enero de 2009 a junio de 2026, 210 meses. La hoja documenta uso académico y fuentes históricas/IGM/INGUAT; no son cifras oficiales.

**Columnas de cálculo:** Año, Mes cod, Tipo de Viajero y Viajero. Las dimensiones Vía, Frontera, País, Región, Región dos, Regiones OMT, MCEO y Agrupación Residencia se validan para comprobar la granularidad de entrada. La columna descriptiva Mes no participa en el cálculo y no es indispensable.

**Clave:** Año + Mes cod + Vía + Frontera + País + Región + Región dos + Regiones OMT + MCEO + Agrupación Residencia + Tipo de Viajero. Se incluyen las dimensiones de clasificación: la fuente contiene combinaciones históricas que coinciden en país/frontera/tipo pero difieren en agrupación de residencia. No se eliminan esas filas legítimas. Un duplicado de la clave completa detiene el flujo, aunque cambie el conteo.

**Salida:** total nacional por mes, sin sumar series de totales con desgloses. Se excluyen Viajero y Cruceristas. Los ceros registrados se conservan; un mes ausente bloquea el flujo, no se rellena con cero. No se redondea la serie antes del ajuste.

**Factor de reparto:** 1.0, porque no se hace reparto territorial. La configuración conserva el factor y su justificación; para otro destino se necesita una metodología y fuente autorizadas. El factor no convierte por sí solo entradas nacionales en personas únicas ni en visitas locales.

**Limitaciones:** quiebre de fuente/metodología desde 2023, cambios en agrupaciones de país, cobertura marítima limitada y ruptura pandémica. Se ajusta desde 2023 para reducir mezcla de metodologías; eso deja una historia corta. Los resultados son académicos y no miden gasto, ocupación o sostenibilidad.

## 3. Procedimiento y períodos

Se reutiliza **suavizamiento exponencial simple (SES)**, uno de los algoritmos del Lab 1 integrados al Lab 10. Se conserva la inicialización estimada y el ajuste optimizado. Se reestiman parámetros con la ventana configurada; no se reutilizan como si fueran nuevas las predicciones históricas exportadas del Lab 10.

Fórmula: nivel_t = alpha × observado_t + (1 − alpha) × nivel_(t−1). El pronóstico a futuro es el último nivel. Se guardan alpha, nivel inicial, nivel final, versión del procedimiento y períodos. La semilla configurada es 221038; SES no requiere muestreo aleatorio.

**Evaluación temporal:** enero–junio de 2026, seis meses. Cada mes se oculta durante su ajuste y se estima usando exclusivamente datos desde enero de 2023 hasta el mes anterior. Los meses ya observados se incorporan para la siguiente evaluación, simulando actualizaciones mensuales. El referente es el último valor observado, sobre los mismos meses.

El Excel contiene observaciones de enero y febrero de 2026; se pueden usar para esta prueba retrospectiva nacional. No se afirma que estaban disponibles en tiempo real ni que equivalen a observaciones de un destino sin fuente comparable. El ejercicio no reproduce la situación original de falta de datos institucionales para un destino.

**Estimaciones candidatas:** julio y agosto de 2026, posteriores a la cobertura del Excel. Ajuste final: enero de 2023–junio de 2026. No son estimaciones de octubre ni se dispone de observaciones para calcular sus errores.

## 4. Diagrama y ejecución

Ver `diagrama_flujo.svg` y el diagrama del PDF.

Fuente mensual + configuración → lectura y huella → seis controles → preparación → ajuste SES y evaluación temporal → estimaciones candidatas → regla de aceptación → manifiesto aprobado → tablero (conexión pendiente para el final).

Ante control crítico fallido se guarda el reporte y se detiene el flujo. Ante rechazo por desempeño se conservan las salidas candidatas para revisión. En ambos casos se mantiene intacta la versión aprobada anterior.

Comando único, desde la raíz: `python pipeline.py`. No requiere modificar archivos intermedios ni mantener una sesión abierta. Cada ejecución conserva configuración, hashes, dependencias, estado de Git, inicio/fin y etapas.

## 5. Controles automáticos

| Control | Verifica | Advertencia | Detención |
|---|---|---|---|
| Columnas y tipos | Variables indispensables; numéricas y dimensiones textuales | No aplica: esquema indispensable | Columna ausente o tipo incompatible |
| Fechas y cobertura | Año/mes enteros válidos; visitantes en cada mes esperado | Filas válidas fuera de la cobertura configurada: se excluyen de la serie | Fecha inválida o mes requerido ausente |
| Unicidad | Clave completa al nivel original | No aplica | Una o más claves duplicadas |
| Faltantes | Nulos y textos vacíos | Solo campos no críticos configurados como permitidos; ninguno habilitado en esta fuente | Falta un campo crítico o una parte de la clave |
| Valores y denominadores | Conteos finitos y no negativos; factor válido | Cociente MAE no disponible si el MAE de referencia es cero: se registra null | Conteo negativo/no finito o factor fuera de (0,1] |
| Regla metodológica | Fuente declarada mensual, sin columna diaria; categorías conocidas; selección Turista + Excursionista | Las limitaciones de fuente quedan documentadas | Fuente diaria, frecuencia distinta o categoría desconocida |

La regla de periodicidad es una comprobación de contrato y esquema: no puede demostrar por sí sola cómo un tercero construyó un Excel. La procedencia mensual se respalda en la hoja Notas y se identifica con SHA-256 en cada ejecución. La selección de visitantes se prueba automáticamente para no sumar Viajero ni Cruceristas.

No hay denominadores de conteos en SES ni en la agregación. Para comparar errores se evita dividir entre cero: el cociente MAE es null si la referencia vale cero y se compara directamente el MAE absoluto. No se utiliza MAPE.

## 6. Regla de aceptación y contrato de salida

La candidata se aprueba solo si pasan los controles críticos, sus períodos son únicos y completos, las estimaciones son finitas/no negativas y su MAE no supera al referente. Umbral previo: MAE_SES ≤ 1.0 × MAE_último_valor. Se compara desempeño sobre los mismos seis meses y en visitantes. Se admite igualdad; si la referencia tiene MAE cero, SES debe tener también MAE cero. El umbral exige al menos el desempeño de una estrategia simple; seis meses no permiten garantizar precisión futura.

Cada `estimaciones.csv` incluye destino, período, valor, unidad, run_id, fecha de generación y versión. `resultados/aprobada.json` apunta a los archivos de la ejecución aprobada. Se reemplaza al terminar las validaciones; se conservan directorios previos. Sin versión aprobada, la futura interfaz deberá mostrar que las estimaciones no están disponibles.

## 7. Evidencia y pendientes

Las verificaciones realizadas y los resultados reales están en `evidencia_avance.json` y en el PDF. Los reportes detallados y resultados institucionales permanecen localmente en `resultados/`.

El avance implementa los cuatro elementos exigidos para hoy. No presenta como terminados los requisitos de la entrega final: MLflow, integración con la interfaz, monitoreo operativo, recuperación demostrada desde el tablero, Docker y prueba desde una copia limpia. El PDF del avance no sustituye el código, los reportes ejecutables ni el informe final completo.
