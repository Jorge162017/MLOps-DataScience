"""Demostración aislada: dos versiones sintéticas aprobadas, fallo y restauración."""
import contextlib
import io
import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
from pipeline import run
from test_pipeline import fixtures
from utilidades import ROOT,write_json,sha256
from versiones import load_approved,point_to


def synthetic_config(folder,scale=1.0):
    folder=Path(folder).resolve();inputs=folder/'fuentes';inputs.mkdir(parents=True,exist_ok=True)
    cfg=json.loads((ROOT/'config.json').read_text());cfg.update(environment='synthetic',output_dir=str(folder/'salidas'))
    tables=fixtures(cfg)
    def seasonal(month):return 100000+20000*np.cos((month-1)*2*np.pi/12)
    n=tables['migration'];n['Viajero']=seasonal(n['Mes cod'])
    m=tables['mobility']
    m['visitantes']=[seasonal(month)*scale*(.2+.05*cfg['scope']['destinations'].index(dest)) for month,dest in zip(m.mes,m.destino)]
    m['dias_persona']=m.visitantes*2;m['permanencia_prom']=2.
    a=tables['airport'];a['Pasajeros']=np.where(a['Tipo de Pasajero'].eq('Doméstico'),10,0)
    for name,spec in {'migration':cfg['migration'],**cfg['sources']}.items():
        frame=tables[name];spec['path']=str(inputs/(name+('.csv' if name in ['capacity','occupancy'] else '.xlsx')))
        if name in ['capacity','occupancy']:frame.to_csv(spec['path'],index=False)
        else:frame.to_excel(spec['path'],sheet_name=spec['sheet'],index=False,startrow=spec.get('header',0))
    write_json(folder/'config.json',cfg)
    return folder/'config.json'


def execute(config):
    with contextlib.redirect_stdout(io.StringIO()) as capture:code=run(config)
    result=json.loads(capture.getvalue());return code,result


def main(folder):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=True)
    # LAB_OUTPUT de Compose no debe mezclar la raíz de la demo con sus salidas.
    old=os.environ.pop('LAB_OUTPUT',None)
    try:
        first=synthetic_config(folder/'version1',1.0)
        cfg=json.loads(first.read_text());output=folder/'salidas';cfg['output_dir']=str(output);write_json(first,cfg)
        code,a=execute(first);assert code==0 and a['estado']=='APPROVED',a
        first_version=load_approved(output,'synthetic')['pointer']['version']
        second=synthetic_config(folder/'version2',1.02)
        cfg2=json.loads(second.read_text());cfg2['output_dir']=str(output);write_json(second,cfg2)
        code,b=execute(second);assert code==0 and b['estado']=='APPROVED',b
        second_version=load_approved(output,'synthetic')['pointer']['version']
        pointer=output/'aprobada.json';before=sha256(pointer)
        mobility=pd.read_excel(cfg2['sources']['mobility']['path'],sheet_name='Peten')
        pd.concat([mobility,mobility.iloc[[0]]],ignore_index=True).to_excel(cfg2['sources']['mobility']['path'],sheet_name='Peten',index=False)
        code,failed=execute(second);assert code==1 and failed['estado']=='FAILED'
        assert sha256(pointer)==before
        # Corrige la fuente, manteniendo el conjunto publicado hasta la restauración explícita.
        mobility.to_excel(cfg2['sources']['mobility']['path'],sheet_name='Peten',index=False)
        code,recovered=execute(second);assert code==0 and recovered['estado']=='APPROVED'
        point_to(output,first_version,'synthetic')
        restored=load_approved(output,'synthetic');assert restored['pointer']['version']==first_version
        evidence=dict(environment='synthetic',output=str(output),primera=first_version,segunda=second_version,
            fallo=failed,recuperacion=recovered,manifiesto_intacto_ante_fallo=True,restaurada=first_version)
        write_json(folder/'evidencia_demo.json',evidence)
        print(json.dumps(evidence,ensure_ascii=False,indent=2))
        return evidence
    finally:
        if old is not None:os.environ['LAB_OUTPUT']=old


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'demo_sintetico')
    main(parser.parse_args().output)
