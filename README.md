# Laboratorio 11 — Avance de MLOps

**Jorge Luis Lopez · 221038 · Grupo 2 · CC3066 · 29 de octubre de 2026**

Entrega de avance: **29 de octubre, antes de las 17:20 (Guatemala)**, El trabajo completo vence el 1 de noviembre.

El avance requiere **alcance, diagrama, pipeline inicial y controles de calidad funcionales**. El PDF documenta el alcance, diagrama, implementación y verificaciones.

## Archivos para revisar

- `AVANCE_LAB11.pdf`: documento del avance, alcance, diagrama, controles, resultados y pendientes.
- `AVANCE_LAB11.md`: alcance y explicación en texto versionable.
- `diagrama_flujo.svg`: diagrama del flujo implementado y límites del avance.
- `pipeline.py`: ejecución independiente del tablero; seis controles, preparación, SES, evaluación temporal y publicación mediante un manifiesto.
- `config.json`: rutas, cobertura, períodos, definición de visitantes y regla de aceptación.
- `requirements.txt`: versiones directas utilizadas.
- `test_pipeline.py`: once pruebas con datos sintéticos; incluye conservación de la versión aprobada ante un fallo.
- `evidencia_avance.json`: resumen de verificaciones, sin filas de la fuente institucional.
- `Lab10-DataScience/`: tablero del Lab 10 y fuentes de trabajo locales.

Los archivos nuevos del avance están en la **raíz**, sin modificar el código del Lab 10.

## Ejecutar desde la raíz

Usar Python **3.13**, versión con la que se verificó este avance.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python pipeline.py
python -m unittest -v test_pipeline
```

No requiere una sesión de notebook ni editar archivos intermedios. `--config otra_config.json` permite usar otra configuración. Las rutas de fuente y salida relativas se interpretan desde la raíz del proyecto. Los datos originales deben estar disponibles localmente en la ruta indicada en `config.json`; para otro equipo, ajustar únicamente esa ruta o montar allí el archivo institucional autorizado.

El script devuelve código 1 ante fallo técnico o control crítico y código 0 si la ejecución termina, incluso si la candidata se rechaza por desempeño. Consultar siempre `estado` y `aprobado` en el reporte.

## Salidas y publicación

Cada ejecución crea `resultados/ejecuciones/<run_id>/` con:

- `ejecucion.json`: inicio, fin, etapas, estado, calidad, hashes de fuente/configuración/código, versiones y estado de Git.
- `calidad.json`: los seis controles; se entrega también si hay un fallo de calidad.
- `config.json`: configuración efectiva.
- `serie_mensual.csv`: visitantes por mes, sin completar ausencias con cero.
- `evaluacion.csv`: observado, estimado, referencia, fecha límite del ajuste y alpha para cada mes evaluado.
- `metricas.json`, `parametros.json`: MAE/RMSE y parámetros/fórmula del procedimiento.
- `estimaciones.csv`: destino, período, valor, unidad, identificador de ejecución, fecha y versión.

Si falla lectura o validación, los archivos de etapas posteriores no se crean: no se inventan métricas.

Solo una ejecución aprobada actualiza `resultados/aprobada.json`, mediante reemplazo atómico. Ese manifiesto apunta a los archivos de una ejecución completa. Las carpetas anteriores se conservan. Ante fallo o rechazo, el manifiesto anterior no cambia. Si no existe, las estimaciones aprobadas no están disponibles.

**La conexión de ese manifiesto con la interfaz Streamlit está pendiente para el trabajo final.** Hoy se entrega el pipeline inicial; el tablero del Lab 10 sigue leyendo sus exportaciones históricas. El contrato de lectura previsto es resolver `estimaciones` y `metricas` desde `aprobada.json` y mostrar únicamente esa versión. Cambiar filtros no debe ejecutar `pipeline.py`.

Para abrir el tablero anterior, seguir su propio README e instalar sus dependencias en otro entorno. No es necesario abrirlo para verificar el avance.

## Verificación y evidencia

Las pruebas sintéticas cubren esquema, tipos, fechas inválidas/fraccionarias, cobertura, duplicados con conteos distintos, faltantes, negativos/no finitos, fuente diaria, categorías desconocidas, exclusión de no visitantes, factor inválido, conservación de ceros y ausencia de información futura en evaluación. Una prueba ejecuta el pipeline con una fuente inválida simulada y comprueba que no cambia la versión aprobada ni registra métricas inexistentes.

`evidencia_avance.json` documenta también dos ejecuciones reales y la comparación de sus salidas numéricas. Los identificadores y fechas de ejecución cambian; las estimaciones y métricas deben ser equivalentes.

Las salidas y el Excel son locales y están excluidos del versionado del repositorio raíz. Compartirlos únicamente por el medio institucional autorizado. El repositorio debe permanecer privado y dar acceso a docentes y auxiliares. No se efectuó ninguna publicación ni envío externo.

## Límites y trabajo restante

La serie nacional representa entradas nacionales comparables, **no personas únicas ni afluencia de un destino**. El factor 1 significa ausencia de reparto territorial. La estimación territorial del grupo 2 requiere confirmar su destino y factor de reparto en el archivo de asignaciones.

Se reutiliza suavizamiento exponencial simple del Lab 1, reestimado en 2023–junio de 2026. No se reproduce aquí el experimento de horizonte fijo de los tres modelos del Lab 10. La evaluación del avance es mensual con historia previa, en enero–junio de 2026; julio–agosto son proyecciones académicas posteriores a la cobertura disponible.

Para el final faltan MLflow, integración del manifiesto con el tablero, monitoreo operativo, demostración de restauración desde la interfaz, Docker/volúmenes y verificación desde una copia limpia. La prueba de fallo de hoy no sustituye esas demostraciones finales. El informe final y los registros completos de MLflow también quedan pendientes.

El pipeline registra el commit si existe, además del estado del árbol de trabajo. Mientras los cambios no estén confirmados, el hash del script ayuda a identificarlos pero **no sustituye un commit**. Antes de la entrega final se debe confirmar el código y volver a ejecutar con esa versión.
