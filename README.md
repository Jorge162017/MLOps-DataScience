# Laboratorio 11 — Observatorio de Tikal y Flores (Petén)

Jorge Luis Lopez · 221038 · Grupo 2 · CC3066 Data Science

Pipeline reproducible, seis controles por fuente, evaluación temporal, MLflow, tablero, monitoreo, versiones verificadas y despliegue local con Docker. El informe completo es `INFORME_LAB11.pdf`.

**Resultado real:** el candidato no supera al último valor observado en Flores y El Remate. Se conserva como REJECTED y no se publica. El tablero informa que no hay estimaciones aprobadas y permite explorar los datos observados validados. La recuperación se demuestra con fuentes sintéticas aisladas y claramente identificadas, sin alterar el criterio real.

## Requisitos y fuentes

Docker Desktop con el motor iniciado y Docker Compose v2. Para ejecución sin contenedores: Python 3.13 y las versiones de `requirements.lock`. La imagen base está fijada por digest y todas las dependencias están fijadas por versión.

Los datos institucionales deben estar disponibles en una carpeta autorizada con esta estructura relativa:

```text
BD_moviidad_mensual.xlsx
indice_ocupacion_mensual_2023_2025_1.csv
oferta_hotelera_2022_2026.csv
Peten/Visitantes_Tikal_2017-2026.xlsx
Peten/AIMM_Consolidado_2022-2025.xlsx
Peten/AIMM_Aerolineas_2023-2026.xlsx
Peten/AIMM_Operaciones_Aeronauticas_2022-2026.xlsx
Lab10-DataScience/referencias/lab1/Laboratorio 1. Series de Tiempo 2026 - Base_Migracion_2009-2026jun.xlsx
```

`BD_moviidad_mensual.xlsx` conserva su nombre original. La hoja se llama `Peten`. La base de Migración puede estar en otra ubicación si se ajusta `migration.path` en `config.json`. El código del Lab 10 no es una dependencia; solo se necesita su Excel institucional. La encuesta de Petén se conserva como antecedente opcional y no se extrapola sin diseño y ponderación justificados.

Los Excel/CSV originales, las salidas y los registros MLflow están excluidos de Git. El Dockerfile usa una lista explícita de código/configuración; el contexto no contiene datos institucionales.

## Ejecutar con Docker

Desde la raíz del repositorio, crear `.env` usando `.env.example`. `DATOS_DIR` es la carpeta que contiene la estructura anterior; se monta en `/datos` en **solo lectura**. Si los archivos están en la raíz actual, `DATOS_DIR=.`. Las rutas internas de las fuentes en `config.json` se mantienen relativas.

```sh
GIT_COMMIT=$(git rev-parse HEAD) docker compose build
GIT_COMMIT=$(git rev-parse HEAD) docker compose up -d tablero mlflow
GIT_COMMIT=$(git rev-parse HEAD) docker compose run --rm pipeline
```

Abrir:

- Tablero: http://localhost:8501
- MLflow: http://localhost:5000

Los puertos se publican únicamente en la interfaz local. El experimento real se llama `Peten-Grupo2`. Cada ejecución registra ID, commit, hashes de código/fuentes/configuración, períodos, parámetros, métricas, controles, estimaciones y archivos necesarios para reproducir el procedimiento. Una ejecución fallida antes de evaluar queda FAILED, con causa y sin métricas predictivas inventadas; una candidata evaluada pero rechazada queda FINISHED con etiqueta `pipeline.decision=REJECTED`.

La salida del comando distingue FAILED, REJECTED y APPROVED. FAILED devuelve código 1. Las otras decisiones devuelven 0 porque el procedimiento terminó; eso no significa que la candidata haya sido aprobada.

Consultar salud y ejecutar pruebas:

```sh
docker compose ps
docker compose run --rm pruebas
```

## Persistencia y detención

El volumen `lab_state` conserva `/state/resultados_peten`, `/state/mlflow_data` y `/state/demo_sintetico` incluso después de eliminar/recrear contenedores. Los artefactos y SQLite comparten ese volumen entre el pipeline y MLflow. El registro utiliza SQLite local y artefactos locales; no se envían datos a un proveedor de tracking externo.

```sh
docker compose down
docker compose --profile demo up -d tablero mlflow demo
```

`down` conserva el volumen. No usar `down -v` para una detención habitual: esa opción elimina el almacenamiento del proyecto. Para comprobar persistencia se compararon IDs MLflow y la versión restaurada antes y después de recrear los servicios.

## Demostrar fallo, recuperación y restauración

```sh
docker compose run --rm pipeline python contenedor.py demo
docker compose --profile demo up -d demo
```

Abrir http://localhost:8502. Esta interfaz muestra un aviso permanente de **DATOS SINTÉTICOS**. La demostración usa un experimento separado `Peten-Grupo2-SINTETICO` y una carpeta diferente de producción.

`demo.py` genera las ocho fuentes sintéticas, obtiene dos versiones aprobadas con la misma regla, introduce una clave duplicada en el Excel mensual, ejecuta y comprueba el fallo, verifica el hash del manifiesto previo, corrige la fuente, vuelve a ejecutar y restaura la primera versión. Guarda `evidencia_demo.json`. No cambia los umbrales para aprobar datos reales ni modifica los archivos institucionales.

En el tablero de demostración, abrir «Administración local · restaurar versión», elegir una versión y pulsar «Restaurar versión». La gráfica consulta inmediatamente el archivo restaurado. Las pruebas de interfaz verifican el cambio y que los filtros no entrenan modelos.

También se puede restaurar por comando, reemplazando VERSION por uno de los identificadores mostrados en la demo:

```sh
docker compose exec demo python versiones.py --output /state/demo_sintetico/salidas --restore VERSION --environment synthetic
```

Para una futura versión real aprobada, usar `/state/resultados_peten` y `--environment production`. Hoy no hay una versión real aprobada que restaurar. El lector verifica hashes, metadatos, controles, aceptación y entorno antes de cambiar el manifiesto. Un archivo alterado, una ejecución rechazada o una versión sintética no pueden restaurarse como producción. Las versiones anteriores no se sobrescriben. Las operaciones de pipeline/restauración usan un bloqueo del almacén y el manifiesto se reemplaza atómicamente.

## Monitoreo

Cada ejecución escribe `monitoreo.json` con:

- **Actualización:** cobertura máxima de cada fuente frente a `monitoring.expected_latest`, y períodos de salida frente a enero-febrero de 2026. La cobertura esperada procede de los archivos y no del reloj: esta es una estimación histórica, no una afirmación de actualidad de octubre de 2026.
- **Calidad:** faltantes permitidos/críticos, duplicados, cobertura y cambios respecto al control anterior.
- **Resultados:** valores negativos/no finitos y variaciones superiores al 50% frente al último observado o a una versión aprobada comparable. El umbral requiere revisión ante cambios amplios en series cortas/estacionales; no se interpreta como pérdida de precisión.

Solo se actualizan MAE/RMSE sobre observaciones comparables. No se calcula error de movilidad para enero-febrero de 2026 porque faltan sus observados. Una alarma crítica bloquea publicación. Los ceros y las ausencias conservan significados distintos.

## Ejecución sin Docker

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python pipeline.py
streamlit run app.py
```

En otra terminal, desde la misma raíz:

```sh
source .venv/bin/activate
mlflow server --backend-store-uri sqlite:///mlflow_data/mlflow.db --host 127.0.0.1 --port 5000 --no-serve-artifacts
```

La demo local:

```sh
python demo.py
LAB_OUTPUT=demo_sintetico/salidas LAB_ENVIRONMENT=synthetic LAB_ADMIN=1 streamlit run app.py --server.port 8502
```

La administración está oculta para usuarios habituales y se habilita únicamente con `LAB_ADMIN=1`. Los detalles de runs/parámetros se consultan en MLflow. El producto muestra destinos, cobertura, fecha de actualización, unidades, MAE y sus limitaciones; no ofrece descarga masiva de microdatos.

## Archivos y resultados

- `pipeline.py`, `fuentes.py`, `validacion_migracion.py`: ajuste, fuentes y 48 controles.
- `seguimiento.py`: registro y consulta MLflow.
- `monitoreo.py`: actualización, calidad y resultados.
- `versiones.py`: versiones inmutables verificadas y restauración.
- `tablero.py`, `app.py`: lectura de observados validados y estimaciones aprobadas; no importan ni ejecutan el ajuste.
- `config.json`: rutas, coberturas, períodos, supuestos y reglas.
- `demo.py`, `test_pipeline.py`, `test_fase2.py`: demostración y 26 pruebas.
- `Dockerfile`, `.dockerignore`, `compose.yaml`, `contenedor.py`: entorno y servicios.
- `evidencia_fase2.json`: evidencia consolidada de ambas fases. Los registros completos permanecen en almacenamiento local.
- `INFORME_LAB11.md`, `INFORME_LAB11.pdf`, `diagrama_flujo.svg`: documentación técnica final.

Cada carpeta de ejecución contiene datos preparados, `calidad.json`, `config.json`, `ejecucion.json`, `monitoreo.json`, evaluación, métricas, parámetros, factores y candidatas. Se guardan en `resultados_peten/ejecuciones/<run_id>` (Docker: `/state/resultados_peten/...`). Las fuentes no se copian a la imagen. `versiones/` contiene las versiones aprobadas y sus hashes; `historial/` registra publicación/restauración. Sin `aprobada.json`, no hay estimaciones aprobadas disponibles. `observados.json` permite explorar datos validados sin exponer candidatas rechazadas.

## Registros completos para revisión

Exportar desde Docker:

```sh
docker compose exec mlflow python exportar_entrega.py --output /state/resultados_peten --demo /state/demo_sintetico --zip /state/lab11_registros_y_resultados.zip
docker compose cp mlflow:/state/lab11_registros_y_resultados.zip .entrega/lab11_registros_y_resultados.zip
```

Crear antes la carpeta `.entrega` si no existe. El paquete incluye una copia consistente de SQLite, artefactos MLflow, resultados, versiones y evidencia sintética; excluye los Excel originales. Mantenerlo en el medio institucional autorizado, fuera de Git. El paquete ya generado localmente está en `.entrega/`. Incluye registros Docker y, como `registros_adicionales_macOS.zip`, los registros de las ejecuciones locales, además de capturas y la comprobación de persistencia.

Restaurar el paquete en una carpeta nueva (reescribe las URI locales de artefactos):

```sh
python importar_entrega.py .entrega/lab11_registros_y_resultados.zip /tmp/lab11-revision
LAB_STATE=/tmp/lab11-revision python seguimiento.py
mlflow server --backend-store-uri sqlite:////tmp/lab11-revision/mlflow_data/mlflow.db --host 127.0.0.1 --port 5001 --no-serve-artifacts
```

La restauración del paquete no recalcula modelos. `LAB_OUTPUT=/tmp/lab11-revision/resultados_peten streamlit run app.py --server.port 8503` consulta el resultado real; para la demo usar `LAB_ENVIRONMENT=synthetic` y `LAB_OUTPUT=/tmp/lab11-revision/demo_sintetico/salidas`.

## Verificación y límites

Se probaron 26 casos localmente y en Docker, incluidos falla segura de MLflow, separación de entornos, alteración de archivos, restauración desde el tablero y ausencia de entrenamiento al filtrar. La construcción y el pipeline se ejecutaron desde un `git archive` limpio, montando únicamente las fuentes autorizadas. Se verificó persistencia al recrear servicios y recuperación del paquete exportado.

La candidata de Petén sigue rechazada. La validación por destino tiene solo tres meses (octubre-diciembre de 2025), con poca historia de calibración; no garantiza precisión futura. La escala nacional-destino no es una participación de mercado. Los ratios Tikal/movilidad no identifican compradores únicos. Pasajeros, vuelos, boletos y visitantes no se suman entre sí.

Dos ejecuciones con la misma configuración y plataforma producen resultados numéricos equivalentes. Las diferencias macOS/Linux del ajuste optimizado se cuantifican en el informe, sin afirmar identidad entre plataformas ni cambiar la decisión de aceptación.

Referencias de implementación: [MLflow Tracking](https://mlflow.org/docs/latest/ml/tracking/) y [pruebas de Streamlit](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest).
