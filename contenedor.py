"""Entradas Docker: rutas montadas para pipeline y servidor MLflow local."""
import json
import os
from pathlib import Path
import sys
from utilidades import write_json

if __name__=='__main__':
    action=sys.argv[1] if len(sys.argv)>1 else 'pipeline'
    Path('/state/mlflow_data/artifacts').mkdir(parents=True,exist_ok=True)
    if action=='mlflow':
        os.execvp('mlflow',['mlflow','server','--host','0.0.0.0','--port','5000','--backend-store-uri',os.environ['MLFLOW_TRACKING_URI'],
            '--default-artifact-root','file:///state/mlflow_data/artifacts','--no-serve-artifacts'])
    elif action=='pipeline':
        from pipeline import run
        cfg=json.loads(Path('config.json').read_text())
        for spec in [cfg['migration'],*cfg['sources'].values()]:spec['path']=str(Path('/datos')/spec['path'])
        cfg['output_dir']='/state/resultados_peten'
        path=Path('/state/config_docker.json');write_json(path,cfg);sys.exit(run(path))
    elif action=='demo':
        from demo import main
        main(Path('/state/demo_sintetico'))
    else:raise SystemExit('Acción desconocida')
