# Laboratorio 11 — Tikal y Flores (Petén)

Jorge Luis Lopez · 221038 · Grupo 2 · CC3066 Data Science

La fase 1 implementa la estimación de movilidad de enero-febrero de 2026 para los tres sitios asignados, la triangulación con Tikal y hoteles, la reconstrucción de pasajeros AIMM 2023, el análisis de operadores y la validación temporal. Los sitios se mantienen separados; no hay un total de personas únicas de Petén.

**Resultado:** la candidata conjunta fue rechazada por desempeño en dos de los tres sitios. El pipeline conserva las estimaciones como candidatas y no actualiza el manifiesto aprobado. Este resultado aplica la regla definida; no es un fallo técnico.

## Ejecución

Usar Python 3.13 desde la raíz:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python pipeline.py
python -m unittest -v test_pipeline
```

El pipeline lee `config.json`; otra configuración se indica con `python pipeline.py --config otra_config.json`. Las rutas relativas se resuelven desde la raíz. Los archivos intermedios no requieren edición manual ni una sesión de notebook. Un fallo técnico o de calidad devuelve código 1; una candidata aprobada o rechazada tras evaluación devuelve código 0. Consultar el campo `estado`.

## Fuentes institucionales locales

Las rutas son configurables. Deben proporcionarse localmente o mediante montaje autorizado; no se incluyen en Git.

- `BD_moviidad_mensual.xlsx`, hoja `Peten`: movilidad mensual de los tres destinos. Se conserva el nombre original del archivo.
- `indice_ocupacion_mensual_2023_2025_1.csv`: ocupación, filtro `Petén`.
- `oferta_hotelera_2022_2026.csv`: capacidad por corte, filtro `Petén`.
- `Peten/Visitantes_Tikal_2017-2026.xlsx`.
- `Peten/AIMM_Consolidado_2022-2025.xlsx`.
- `Peten/AIMM_Aerolineas_2023-2026.xlsx`.
- `Peten/AIMM_Operaciones_Aeronauticas_2022-2026.xlsx`.
- Base de Migración en `Lab10-DataScience/referencias/lab1/Laboratorio 1. Series de Tiempo 2026 - Base_Migracion_2009-2026jun.xlsx`.

El código del Lab 10 y su entorno no son dependencias del pipeline: únicamente se utiliza su Excel institucional. Puede colocarse la base en otra carpeta y modificar `migration.path`. La encuesta del ZIP se conserva como antecedente opcional, sin extrapolar sus respuestas.

## Código y documentos

- `pipeline.py`: configuración, ajuste, reparto, validación, triangulación y decisión.
- `fuentes.py`: lectura, seis controles por fuente y preparación de las ocho fuentes.
- `validacion_migracion.py`: contrato de la serie nacional mensual.
- `utilidades.py`: escritura atómica, huellas y procedencia Git.
- `config.json`: fuentes, cobertura, períodos, modelo y umbral previo de aceptación.
- `requirements.txt`: versiones directas usadas, incluido SciPy para el ajuste.
- `test_pipeline.py`: 15 pruebas sintéticas sin dependencia de archivos institucionales.
- `AVANCE_LAB11.md` y `AVANCE_LAB11.pdf`: informe actualizado de la fase 1.
- `diagrama_flujo.svg`: el mismo diagrama incluido en el PDF.
- `evidencia_avance.json`: controles, métricas, factores, candidatas, reproducibilidad y prueba de fallo.

## Método y aislamiento temporal

Se reutiliza Holt-Winters aditivo amortiguado del Lab 1, con ciclo de 12 meses. El ajuste final usa enero de 2023-diciembre de 2025 y pronostica enero-febrero de 2026. El factor de cada sitio es la razón de las sumas de movilidad y Migración en los mismos meses observados anteriores al corte; para los objetivos son septiembre-diciembre de 2025.

La escala empírica no es una participación de mercado: movilidad incluye visitantes nacionales y Migración representa entradas internacionales. No se fuerza la suma de factores a uno. La evaluación de ese supuesto es parte del resultado.

La validación de destinos oculta octubre-noviembre de 2025 desde el corte de septiembre, y diciembre desde noviembre. El factor y el modelo se ajustan solo con información anterior al bloque. La referencia conserva el último valor observado antes del bloque. Hay solo tres meses evaluables por sitio, una limitación sustancial. No se utilizan marzo-agosto de 2026 para calibrar las estimaciones de enero-febrero.

La validación nacional cubre los 12 meses de 2025 en bloques de hasta dos meses, frente al mismo mes del año anterior. Se guardan MAE y RMSE. No se calcula error de movilidad para enero-febrero de 2026 porque faltan observaciones comparables.

La regla exige controles críticos válidos, salidas íntegras y MAE no superior al referente en cada sitio, con al menos tres meses de validación. La candidata pasa en Mundo Maya Aeropuerto y falla en Flores y El Remate: el conjunto se rechaza. No se modifica el umbral ni se publica un modelo alternativo seleccionado después de ver los errores.

## Salidas

Cada ejecución crea `resultados_peten/ejecuciones/<run_id>/` con:

- `ejecucion.json`, `config.json`, `calidad.json`: etapas, fechas UTC, estado, huellas de código/fuentes, versiones, estado de Git y 48 controles (seis en cada fuente).
- `nacional.csv`, `movilidad.csv`, `tikal.csv`, `ocupacion.csv`, `capacidad.csv`: fuentes preparadas, conservando sus unidades y coberturas.
- `aeropuerto.csv`: serie 2022-abril de 2026 por Entrada/Salida, identificando reconstrucción 2023 y extensión parcial 2026.
- `aerolineas.csv`, `operadores.csv`: pasajeros y operaciones en tablas separadas.
- `conciliacion_aeropuerto.csv`: comparación de fuentes superpuestas; no se suman.
- `evaluacion_destinos.csv`, `evaluacion_nacional.csv`, `metricas.json`: predicciones, referentes, cortes, factores y errores.
- `ajustes_validacion.json`, `parametros.json`, `factores.json`: parámetros del modelo, escala numérica y calibración reproducible.
- `estimaciones.csv`: seis candidatas con destino, período, valor, unidad, corte, factor, run_id, fecha y versión.
- `triangulacion.csv`: boletos, movilidad observada/candidata, pasajeros de entrada y ocupación disponible, con ausencias preservadas.

La capacidad se conserva por corte, sin sumarla entre años ni interpolarla como observaciones mensuales. Los ratios Tikal/movilidad son razones entre fuentes, no porcentajes de compradores únicos. Las filas que usan denominadores estimados se etiquetan como candidatas.

Solo si todos los sitios pasan se reemplaza atómicamente `resultados_peten/aprobada.json`. Ante fallo o rechazo se conserva la versión anterior; si no existe, no hay estimaciones aprobadas disponibles. `resultados/` conserva el antecedente nacional y no se utiliza como aprobación de Petén. La integración con Streamlit está pendiente.

## Verificación

Las pruebas cubren las ocho fuentes, cobertura por sitio, tipos, fechas fraccionarias, duplicados con valores diferentes, faltantes permitidos/críticos, negativos/no finitos, ceros, denominadores, coherencia de Tikal, reconstrucción 2023 sin doble conteo y separación de unidades. También modifican los datos posteriores al corte para comprobar que no afectan las estimaciones; ocultan bloques de dos meses y verifican que una ejecución fallida no reemplaza un manifiesto previo ni inventa métricas.

La evidencia local incluye dos ejecuciones completas equivalentes con tolerancia absoluta `1e-8` y relativa cero, y una ejecución de fallo con una copia del Excel mensual que contiene una clave duplicada. Las diferencias numéricas observadas entre las ejecuciones válidas fueron cero.

## Fase 2

Quedan MLflow, integración del manifiesto con el tablero, monitoreo, restauración demostrada desde la interfaz, Docker con persistencia y comprobación desde una copia limpia. El repositorio debe ser privado y conceder acceso a docentes y auxiliares. Los datos y resultados institucionales se comparten solo por el medio autorizado.
