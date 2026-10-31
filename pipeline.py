"""Fase 1: estimación y triangulación de Tikal y Flores, grupo 2."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import uuid
import warnings
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from fuentes import read_sources, check_sources, prepare_sources
from utilidades import ROOT, now, write_json, sha256, git_state,store_lock
from seguimiento import Tracker
from monitoreo import monitor
from versiones import publish
from tablero import observed_pointer


def validate_config(cfg):
    p = cfg['procedure']
    start, cutoff = pd.Timestamp(p['training_start']), pd.Timestamp(p['cutoff'])
    targets = pd.DatetimeIndex(pd.to_datetime(p['targets']))
    expected = pd.date_range(cutoff + pd.offsets.MonthBegin(1), periods=p['horizon'], freq='MS')
    if start.day != 1 or cutoff.day != 1 or not targets.equals(expected):
        raise ValueError('Objetivos deben seguir al corte en meses consecutivos')
    if start >= cutoff or (cutoff.to_period('M')-start.to_period('M')).n+1 < 24:
        raise ValueError('Se requieren al menos dos ciclos mensuales')
    if p['horizon'] != 2 or p['seasonal_periods'] != 12:
        raise ValueError('Esta versión requiere horizonte 2 y ciclo 12')
    for prefix in ['', 'national_']:
        if not (pd.Timestamp(p[prefix+'validation_start']) <= pd.Timestamp(p[prefix+'validation_end']) <= cutoff):
            raise ValueError('Validación debe terminar antes de los objetivos')
    if cfg['scope']['sum_destinations'] is not False or len(set(cfg['scope']['destinations'])) != 3:
        raise ValueError('Se requieren tres destinos separados')
    if cfg['sources']['mobility']['frequency'] != 'monthly':
        raise ValueError('Se requiere fuente mensual')
    if set(cfg['scope']['traveler_types']) != {'Turista','Excursionista'}:
        raise ValueError('La serie nacional debe sumar solo Turista + Excursionista')
    ratio = cfg['acceptance']['max_mae_ratio_to_baseline']
    if not np.isfinite(ratio) or ratio < 0:
        raise ValueError('Umbral inválido')
    if p['minimum_calibration_months'] < 1 or cfg['acceptance']['minimum_validation_months'] < 1:
        raise ValueError('Se requiere historia de calibración y validación')
    if (p['trend'],p['damped_trend'],p['seasonal'],p['initialization_method']) != ('add',True,'add','estimated'):
        raise ValueError('Esta versión reutiliza Holt-Winters aditivo amortiguado')


def national_forecast(national, cutoff, horizon, cfg):
    history = national.loc[cfg['procedure']['training_start']:cutoff]
    if len(history)<24 or history.isna().any() or not history.index.equals(pd.date_range(history.index.min(),cutoff,freq='MS')):
        raise ValueError('Historia nacional insuficiente o incompleta hasta el corte')
    # Misma configuración del Lab 1. Escala numérica fija para estabilidad del optimizador.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        fitted = ExponentialSmoothing(history.to_numpy()/100000, trend='add', damped_trend=True,
            seasonal='add', seasonal_periods=12, initialization_method='estimated').fit(optimized=True,use_brute=True)
    if not fitted.mle_retvals.get('success',True):
        raise ValueError('El ajuste Holt-Winters no convergió')
    predictions = np.asarray(fitted.forecast(horizon))*100000
    if not np.isfinite(predictions).all() or (predictions<0).any():
        raise ValueError('Pronóstico nacional inválido')
    params = {k:float(fitted.params[k]) for k in ['smoothing_level','smoothing_trend','smoothing_seasonal','damping_trend','initial_level','initial_trend']}
    params.update(initial_seasons=fitted.params['initial_seasons'].tolist(),escala_numerica=100000,
        ajuste_desde=history.index.min().strftime('%Y-%m-%d'),ajuste_hasta=cutoff.strftime('%Y-%m-%d'),
        advertencias=[str(w.message) for w in caught])
    return predictions,params


def allocation(national,mobility,destination,cutoff,cfg):
    observed = mobility[destination].loc[:cutoff].dropna()
    if len(observed)<cfg['procedure']['minimum_calibration_months']:
        raise ValueError('Historia insuficiente para escala de '+destination)
    denominator = national.reindex(observed.index)
    if denominator.isna().any() or not np.isfinite(denominator).all() or denominator.le(0).any():
        raise ValueError('Denominador de calibración ausente, no finito o cero')
    factor = float(observed.sum()/denominator.sum())
    if not np.isfinite(factor) or factor<=0:
        raise ValueError('Escala no positiva o no finita')
    return factor,dict(destino=destination,factor=factor,meses=len(observed),periodos=observed.index.strftime('%Y-%m-%d').tolist(),
        numerador=float(observed.sum()),denominador=float(denominator.sum()),corte=cutoff.strftime('%Y-%m-%d'),
        interpretacion='Escala empírica entre poblaciones diferentes; no probabilidad ni participación de mercado')


def error_metrics(frame):
    result = {}
    for column in ['estimado','referencia']:
        error = frame[column]-frame.observado
        result[column] = dict(MAE=float(error.abs().mean()),RMSE=float(np.sqrt((error**2).mean())))
    baseline = result['referencia']['MAE']
    result.update(ratio_MAE=result['estimado']['MAE']/baseline if baseline>0 else None,meses=int(len(frame)))
    return result


def evaluate(national,mobility,cfg):
    p=cfg['procedure']; rows=[]; national_rows=[]; models=[]
    for kind,prefix in [('destino',''),('nacional','national_')]:
        months=pd.date_range(p[prefix+'validation_start'],p[prefix+'validation_end'],freq='MS')
        for i in range(0,len(months),p['horizon']):
            targets=months[i:i+p['horizon']]; cutoff=targets[0]-pd.offsets.MonthBegin(1)
            forecast,params=national_forecast(national,cutoff,len(targets),cfg)
            models.append(dict(tipo=kind,**params))
            if kind=='nacional':
                for month,prediction in zip(targets,forecast):
                    ref=month-pd.DateOffset(years=1)
                    national_rows.append(dict(periodo=month,corte=cutoff,observado=national.loc[month],estimado=prediction,
                        referencia=national.loc[ref],referencia_periodo=ref,horizonte=(month.to_period('M')-cutoff.to_period('M')).n))
            else:
                for destination in cfg['scope']['destinations']:
                    factor,info=allocation(national,mobility,destination,cutoff,cfg)
                    baseline=mobility[destination].loc[:cutoff].dropna().iloc[-1]
                    for month,prediction in zip(targets,forecast):
                        observed=mobility[destination].get(month,np.nan)
                        if pd.isna(observed): raise ValueError('Mes evaluado sin observado')
                        rows.append(dict(destino=destination,periodo=month,corte=cutoff,observado=observed,
                            estimado=prediction*factor,referencia=baseline,factor=factor,meses_calibracion=info['meses'],
                            calibracion_hasta=info['periodos'][-1],horizonte=(month.to_period('M')-cutoff.to_period('M')).n))
    evaluation=pd.DataFrame(rows); national_evaluation=pd.DataFrame(national_rows)
    metrics=dict(destinos={},nacional=error_metrics(national_evaluation))
    for destination,frame in evaluation.groupby('destino'):
        item=error_metrics(frame)
        item['aceptado']=bool(item['meses']>=cfg['acceptance']['minimum_validation_months'] and
            item['estimado']['MAE']<=item['referencia']['MAE']*cfg['acceptance']['max_mae_ratio_to_baseline'])
        metrics['destinos'][destination]=item
    return evaluation,national_evaluation,metrics,models


def estimate(national,mobility,cfg):
    cutoff=pd.Timestamp(cfg['procedure']['cutoff']); targets=pd.DatetimeIndex(pd.to_datetime(cfg['procedure']['targets']))
    predictions,params=national_forecast(national,cutoff,len(targets),cfg)
    rows=[]; factors=[]
    for destination in cfg['scope']['destinations']:
        factor,info=allocation(national,mobility,destination,cutoff,cfg); factors.append(info)
        for month,value in zip(targets,predictions):
            rows.append(dict(destino=destination,periodo=month,valor=float(value*factor),unidad=cfg['scope']['unit'],
                tipo='estimado',factor=factor,corte=cutoff,nacional_estimado=float(value)))
    return pd.DataFrame(rows),factors,params


def triangulate(prepared,forecast):
    observed=prepared['movilidad'].stack().rename('visitantes_movilidad').reset_index()
    observed.columns=['periodo','destino','visitantes_movilidad']; observed['tipo_denominador']='observado'
    estimated=forecast[['periodo','destino','valor']].rename(columns={'valor':'visitantes_movilidad'}).assign(tipo_denominador='estimado_candidato')
    combined=pd.concat([observed,estimated],ignore_index=True)
    combined=combined.merge(prepared['tikal'].reset_index()[['periodo','total']],on='periodo',how='left').rename(columns={'total':'boletos_tikal'})
    combined['ratio_boletos_a_movilidad_pct']=combined.boletos_tikal.div(combined.visitantes_movilidad.where(combined.visitantes_movilidad.gt(0)))*100
    combined['interpretacion']='Razón entre fuentes, no porcentaje de personas que compró boleto; poblaciones no enlazadas'
    combined=combined.merge(prepared['ocupacion'].reset_index(),on='periodo',how='left')
    entries=prepared['aeropuerto'].query("flujo == 'Entrada'")[['periodo','pasajeros']].rename(columns={'pasajeros':'pasajeros_entrada_AIMM'})
    return combined.merge(entries,on='periodo',how='left')


def _run(config_path):
    cfg=json.loads(Path(config_path).read_text()); validate_config(cfg); np.random.seed(cfg['procedure']['seed'])
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]
    output=Path(os.environ.get('LAB_OUTPUT',ROOT/cfg['output_dir'])); folder=output/'ejecuciones'/run_id; folder.mkdir(parents=True,exist_ok=False)
    report=dict(run_id=run_id,inicio=now(),estado='RUNNING',etapas=[],controles=[],grupo=cfg['group'],destino=cfg['destination'],
        git=git_state(),config_sha256=sha256(config_path),codigo_sha256={f:sha256(ROOT/f) for f in ['pipeline.py','fuentes.py','validacion_migracion.py','utilidades.py','seguimiento.py','monitoreo.py','versiones.py']},
        dependencias={n:importlib.metadata.version(n) for n in ['pandas','numpy','openpyxl','statsmodels','scipy','mlflow']})
    write_json(folder/'config.json',cfg)
    def stage(name): report['etapas'].append(dict(etapa=name,fin=now()))
    tracker=None;published=False
    pointer=output/'aprobada.json';previous_pointer=pointer.read_bytes() if pointer.exists() else None
    tables={};checks=[];dates={}
    try:
        tracker=Tracker(cfg,report);report['mlflow_run_id']=tracker.id;stage('inicio_mlflow')
        report['fuentes']={n:dict(ruta=s['path'],sha256=sha256(ROOT/s['path'])) for n,s in {'migration':cfg['migration'],**cfg['sources']}.items()}
        tables=read_sources(cfg,ROOT); report['filas']={n:len(d) for n,d in tables.items()}; stage('lectura')
        checks,dates=check_sources(tables,cfg); report['controles']=checks; write_json(folder/'calidad.json',checks)
        if any(c['estado']=='FAIL' for c in checks):
            report['monitoreo']=monitor(cfg,tables,dates,checks,None,output)
            write_json(folder/'monitoreo.json',report['monitoreo'])
            raise ValueError('Control crítico fallido: '+', '.join(c['fuente']+'/'+c['control'] for c in checks if c['estado']=='FAIL'))
        stage('validacion'); prepared=prepare_sources(tables,dates,cfg)
        for name,frame in prepared.items(): frame.to_csv(folder/(name+'.csv'),index=name in ['nacional','movilidad','tikal','ocupacion'])
        stage('preparacion_fuentes')
        evaluation,national_evaluation,metrics,models=evaluate(prepared['nacional'],prepared['movilidad'],cfg)
        evaluation.to_csv(folder/'evaluacion_destinos.csv',index=False); national_evaluation.to_csv(folder/'evaluacion_nacional.csv',index=False)
        write_json(folder/'metricas.json',metrics); report['metricas']=metrics
        write_json(folder/'ajustes_validacion.json',models); stage('validacion_temporal')
        forecast,factors,parameters=estimate(prepared['nacional'],prepared['movilidad'],cfg)
        forecast=forecast.assign(run_id=run_id,fecha_generacion=now(),version=cfg['procedure']['version'])
        write_json(folder/'factores.json',factors); write_json(folder/'parametros.json',parameters)
        forecast.to_csv(folder/'estimaciones.csv',index=False); triangulate(prepared,forecast).to_csv(folder/'triangulacion.csv',index=False)
        airline=prepared['aerolineas'].groupby(['periodo','Tipo de Flujo']).Pasajeros.sum().rename('pasajeros_aerolineas').reset_index().rename(columns={'Tipo de Flujo':'flujo'})
        comparison=prepared['aeropuerto'].merge(airline,on=['periodo','flujo'],how='inner'); comparison['diferencia']=comparison.pasajeros-comparison.pasajeros_aerolineas
        comparison.to_csv(folder/'conciliacion_aeropuerto.csv',index=False); stage('estimacion_y_triangulacion')
        integrity=bool(len(forecast)==len(cfg['scope']['destinations'])*len(cfg['procedure']['targets']) and
            not forecast.duplicated(['destino','periodo']).any() and np.isfinite(forecast.valor).all() and forecast.valor.ge(0).all())
        report['monitoreo']=monitor(cfg,tables,dates,checks,forecast,output)
        write_json(folder/'monitoreo.json',report['monitoreo'])
        write_json(output/'ultimo_monitoreo.json',report['monitoreo']);stage('monitoreo')
        accepted=bool(integrity and not report['monitoreo']['critico'] and all(m['aceptado'] for m in metrics['destinos'].values()))
        report.update(estado='APPROVED' if accepted else 'REJECTED',aprobado=accepted,integridad_salidas=integrity,metricas=metrics,
            limitaciones=['Solo tres meses de validación del destino; no hay enero-febrero observados de movilidad.',
            'Escala empírica con poblaciones diferentes, no participación de mercado.',
            'Destinos potencialmente solapados; no sumarlos como personas únicas.',
            'Ratios Tikal/movilidad no identifican compradores individuales.'])
        if accepted:
            report['fin']=now();report['publicacion']='Autorizada; persistencia MLflow previa al cambio'
            write_json(folder/'ejecucion.json',report);tracker.record(report,folder)
            publish(folder,output,cfg.get('environment','production'));published=True
            report['publicacion']='Manifiesto de Petén actualizado'
        else: report['publicacion']='Candidata rechazada; se conserva la versión aprobada previa, si existe'
        stage('decision_aceptacion')
    except Exception as exc:
        report.update(estado='FAILED',error=f'{type(exc).__name__}: {exc}',publicacion='Sin reemplazo de versión aprobada')
    finally:
        report['fin']=now(); write_json(folder/'ejecucion.json',report)
        if tracker:
            try:tracker.record(report,folder)
            except Exception as exc:
                if published:
                    if previous_pointer is None:pointer.unlink(missing_ok=True)
                    else:
                        tmp=pointer.with_suffix('.rollback');tmp.write_bytes(previous_pointer);tmp.replace(pointer)
                    write_json(output/'versiones'/run_id/'revocada.json',dict(motivo='Seguimiento final no confirmado',fecha=now()))
                report.update(estado='FAILED',error=f'MLflow: {exc}',publicacion='Sin publicación; seguimiento no confirmado')
                write_json(folder/'ejecucion.json',report)
        if report['estado'] in ['APPROVED','REJECTED']:
            observed_pointer(output,folder,report)
    print(json.dumps(dict(run_id=run_id,estado=report['estado'],reporte=str(folder/'ejecucion.json'),error=report.get('error'),metricas=report.get('metricas')),ensure_ascii=False,indent=2))
    return 1 if report['estado']=='FAILED' else 0


def run(config_path):
    cfg=json.loads(Path(config_path).read_text())
    output=Path(os.environ.get('LAB_OUTPUT',ROOT/cfg['output_dir']))
    with store_lock(output):return _run(config_path)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--config',type=Path,default=ROOT/'config.json')
    sys.exit(run(parser.parse_args().config))
