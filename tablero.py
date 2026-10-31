"""Lectores del tablero: observados validados y estimaciones exclusivamente aprobadas."""
import json
from pathlib import Path
import pandas as pd
from utilidades import sha256
from versiones import inside,load_approved

OBSERVED_FILES=['movilidad.csv','tikal.csv','aeropuerto.csv','aerolineas.csv','operadores.csv','ocupacion.csv','capacidad.csv']


def observed_pointer(output,folder,report):
    from utilidades import write_json,now
    if report['estado'] not in ['APPROVED','REJECTED'] or any(c['estado']=='FAIL' for c in report['controles']):return
    write_json(Path(output)/'observados.json',dict(run_id=report['run_id'],folder=str(Path(folder).relative_to(output)),
        fecha=now(),hashes={f:sha256(Path(folder)/f) for f in OBSERVED_FILES}))


def load_observed(output):
    pointer=Path(output)/'observados.json'
    if not pointer.exists():return None
    meta=json.loads(pointer.read_text());folder=inside(output,meta['folder'])
    report=json.loads((folder/'ejecucion.json').read_text())
    if report['estado'] not in ['APPROVED','REJECTED']:raise ValueError('Observados no validados')
    tables={}
    for name in OBSERVED_FILES:
        path=inside(folder,name)
        if sha256(path)!=meta['hashes'][name]:raise ValueError('Observados alterados')
        tables[name[:-4]]=pd.read_csv(path)
    return dict(tables=tables,meta=meta)


def dashboard_state(output,environment='production'):
    return dict(observed=load_observed(output),approved=load_approved(output,environment))
