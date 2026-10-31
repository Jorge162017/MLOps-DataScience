FROM python:3.13-slim@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MLFLOW_DISABLE_AGENT_HINT=1 GIT_PYTHON_REFRESH=quiet STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY requirements.lock requirements.txt ./
RUN pip install --no-cache-dir -r requirements.lock
COPY pipeline.py fuentes.py validacion_migracion.py utilidades.py seguimiento.py monitoreo.py versiones.py tablero.py app.py contenedor.py demo.py exportar_entrega.py importar_entrega.py test_pipeline.py test_fase2.py config.json ./
ARG GIT_COMMIT=unknown
ENV LAB_GIT_COMMIT=$GIT_COMMIT LAB_STATE=/state LAB_OUTPUT=/state/resultados_peten MLFLOW_TRACKING_URI=sqlite:////state/mlflow_data/mlflow.db MLFLOW_ARTIFACT_ROOT=/state/mlflow_data/artifacts
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
