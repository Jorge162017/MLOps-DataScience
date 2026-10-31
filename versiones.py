"""Versiones inmutables verificadas; publicación y restauración usan el mismo contrato."""
import argparse
import json
from pathlib import Path
import re
import shutil
import numpy as np
import pandas as pd
from utilidades import now,write_json,sha256,store_lock


def inside(root,relative):
    root=Path(root).resolve();path=(root/relative).resolve()
    if not path.is_relative_to(root):raise ValueError('Ruta fuera del almacén')
    return path


def validate_folder(folder,environment):
    folder=Path(folder)
    report=json.loads((folder/'ejecucion.json').read_text())
    cfg=json.loads((folder/'config.json').read_text())
    metrics=json.loads((folder/'metricas.json').read_text())
    if cfg.get('environment','production')!=environment:raise ValueError('Entorno de versión incompatible')
    if report['estado']!='APPROVED' or not report.get('aprobado') or not report.get('integridad_salidas'):
        raise ValueError('La ejecución no fue aprobada')
    if not report.get('mlflow_run_id'):raise ValueError('La versión requiere trazabilidad MLflow')
    if len(report.get('controles',[]))!=48 or any(c['estado']=='FAIL' for c in report['controles']):
        raise ValueError('Controles críticos incompletos o fallidos')
    if report.get('monitoreo',{}).get('critico',True):raise ValueError('Monitoreo crítico o ausente')
    if not metrics.get('destinos') or not all(m['aceptado'] for m in metrics['destinos'].values()):
        raise ValueError('Métricas de la versión no aceptadas')
    frame=pd.read_csv(folder/'estimaciones.csv')
    required=['destino','periodo','valor','unidad','run_id','fecha_generacion','version','tipo']
    if not set(required)<=set(frame) or frame[required].isna().any().any():raise ValueError('Metadatos incompletos')
    actual=set(zip(frame.destino,pd.to_datetime(frame.periodo).dt.strftime('%Y-%m-%d')))
    expected={(d,p) for d in cfg['scope']['destinations'] for p in cfg['procedure']['targets']}
    if actual!=expected or len(frame)!=len(expected):raise ValueError('Períodos/destinos incompletos o repetidos')
    if not np.isfinite(frame.valor).all() or frame.valor.lt(0).any() or not frame.run_id.eq(report['run_id']).all():
        raise ValueError('Valores o identificadores inválidos')
    return report,cfg,frame,metrics


def read_version(output,version,environment='production'):
    if not re.fullmatch(r'[A-Za-z0-9_-]+',version):raise ValueError('Identificador de versión inválido')
    folder=inside(output,'versiones/'+version)
    if (folder/'revocada.json').exists():raise ValueError('Versión revocada')
    manifest=json.loads((folder/'version.json').read_text())
    if not {'ejecucion.json','config.json','metricas.json','monitoreo.json','estimaciones.csv'}<=set(manifest['hashes']):
        raise ValueError('Manifiesto de integridad incompleto')
    if manifest['environment']!=environment:raise ValueError('No se mezclan versiones sintéticas y reales')
    for name,digest in manifest['hashes'].items():
        if sha256(inside(folder,name))!=digest:raise ValueError('Versión alterada: '+name)
    return folder,validate_folder(folder,environment)


def point_to(output,version,environment='production',action='restore'):
    output=Path(output)
    folder,(report,cfg,_,_)=read_version(output,version,environment)
    pointer=dict(version=version,run_id=report['run_id'],environment=environment,fecha=now(),
        estimaciones=f'versiones/{version}/estimaciones.csv',metricas=f'versiones/{version}/metricas.json')
    history=output/'historial';history.mkdir(parents=True,exist_ok=True)
    write_json(history/(str(pd.Timestamp.now().value)+'-'+action+'.json'),dict(action=action,**pointer))
    write_json(output/'aprobada.json',pointer)
    return pointer


def publish(folder,output,environment='production'):
    folder,output=Path(folder),Path(output)
    report,_,_,_=validate_folder(folder,environment)
    version=report['run_id'];target=inside(output,'versiones/'+version)
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():raise ValueError('La versión ya existe y no se sobrescribe')
    temp=target.with_name(version+'.tmp')
    try:
        shutil.copytree(folder,temp)
        hashes={p.name:sha256(p) for p in temp.iterdir() if p.is_file()}
        write_json(temp/'version.json',dict(version=version,environment=environment,hashes=hashes))
        temp.rename(target)
    except Exception:
        shutil.rmtree(temp,ignore_errors=True);raise
    return point_to(output,version,environment,'publish')


def load_approved(output,environment='production'):
    output=Path(output)
    if not (output/'aprobada.json').exists():return None
    pointer=json.loads((output/'aprobada.json').read_text())
    if pointer['environment']!=environment:raise ValueError('Manifiesto de otro entorno')
    folder,data=read_version(output,pointer['version'],environment)
    return dict(folder=folder,report=data[0],config=data[1],forecast=data[2],metrics=data[3],pointer=pointer)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--restore',required=True);parser.add_argument('--environment',default='production',choices=['production','synthetic'])
    args=parser.parse_args()
    with store_lock(args.output):print(json.dumps(point_to(args.output,args.restore,args.environment),indent=2))
