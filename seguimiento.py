"""MLflow local: parámetros, métricas y artefactos de ejecuciones reales o sintéticas."""
import json
import os
from pathlib import Path
os.environ.setdefault('GIT_PYTHON_REFRESH','quiet')
os.environ.setdefault('MLFLOW_DISABLE_AGENT_HINT','1')
import mlflow
from mlflow.tracking import MlflowClient
from utilidades import ROOT


def settings():
    home = Path(os.environ.get('LAB_STATE', ROOT)).resolve() / 'mlflow_data'
    home.mkdir(parents=True,exist_ok=True)
    uri = os.environ.get('MLFLOW_TRACKING_URI', 'sqlite:///'+str(home/'mlflow.db'))
    # El laboratorio conserva las fuentes/resultados en almacenamiento local.
    if not uri.startswith('sqlite:///'):
        raise ValueError('Se requiere MLflow SQLite local para este despliegue')
    artifacts = Path(os.environ.get('MLFLOW_ARTIFACT_ROOT',home/'artifacts')).resolve()
    artifacts.mkdir(parents=True,exist_ok=True)
    return uri,artifacts


class Tracker:
    def __init__(self,cfg,report):
        uri,artifacts=settings()
        self.client=MlflowClient(tracking_uri=uri)
        name='Peten-Grupo2' if cfg.get('environment','production')=='production' else 'Peten-Grupo2-SINTETICO'
        experiment=self.client.get_experiment_by_name(name)
        experiment_id=experiment.experiment_id if experiment else self.client.create_experiment(name,artifact_location=artifacts.as_uri()+'/'+name)
        run=self.client.create_run(experiment_id,tags={'mlflow.runName':report['run_id'],
            'pipeline.run_id':report['run_id'],'environment':cfg.get('environment','production'),
            'git.commit':report['git'].get('commit') or 'sin_commit', 'destination':cfg['destination']})
        self.id=run.info.run_id
        def flatten(prefix,value):
            if isinstance(value,dict):
                for key,item in value.items():flatten(prefix+'.'+key if prefix else key,item)
            else:self.client.log_param(self.id,prefix,json.dumps(value,ensure_ascii=False)[:5900])
        flatten('',cfg)

    def record(self,report,folder):
        self.client.set_tag(self.id,'pipeline.decision',report['estado'])
        self.client.set_tag(self.id,'pipeline.error',report.get('error',''))
        for name,spec in report.get('fuentes',{}).items():
            self.client.log_param(self.id,'source.'+name+'.sha256',spec['sha256'])
        for key,value in report.get('codigo_sha256',{}).items():
            self.client.log_param(self.id,'code.'+key+'.sha256',value)
        for status in ['PASS','WARN','FAIL']:
            self.client.log_metric(self.id,'quality.'+status,sum(c['estado']==status for c in report.get('controles',[])))
        # Una ejecución detenida antes de evaluar no registra errores predictivos.
        for destination,item in report.get('metricas',{}).get('destinos',{}).items():
            key=destination.replace(' ','_')
            for model in ['estimado','referencia']:
                for metric,value in item[model].items():self.client.log_metric(self.id,key+'.'+model+'.'+metric,value)
        for model,item in report.get('metricas',{}).get('nacional',{}).items():
            if isinstance(item,dict):
                for metric,value in item.items():self.client.log_metric(self.id,'nacional.'+model+'.'+metric,value)
        self.client.log_artifacts(self.id,str(folder),artifact_path='ejecucion')
        self.client.set_terminated(self.id,status='FAILED' if report['estado']=='FAILED' else 'FINISHED')


def query_runs():
    uri,_=settings(); client=MlflowClient(tracking_uri=uri)
    rows=[]
    for experiment in client.search_experiments():
        if not experiment.name.startswith('Peten-Grupo2'):continue
        for run in client.search_runs([experiment.experiment_id],max_results=1000):
            rows.append(dict(experiment=experiment.name,mlflow_id=run.info.run_id,status=run.info.status,
                pipeline_id=run.data.tags.get('pipeline.run_id'),decision=run.data.tags.get('pipeline.decision'),
                error=run.data.tags.get('pipeline.error'),metrics=run.data.metrics,params=run.data.params,
                artifact_uri=run.info.artifact_uri))
    return rows


if __name__=='__main__':
    print(json.dumps(query_runs(),ensure_ascii=False,indent=2))
