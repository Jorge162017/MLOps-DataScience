"""Actualización según cobertura, cambios de calidad y variación de resultados."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from versiones import load_approved


def monitor(cfg,tables,dates,checks,forecast,output):
    alerts=[];coverage={}
    def alert(kind,text,critical=False):alerts.append(dict(tipo=kind,mensaje=text,critico=critical))
    for name,values in dates.items():
        coverage[name]=None if values.dropna().empty else values.max().strftime('%Y-%m-%d')
    expected=cfg['monitoring']['expected_latest']
    for name,month in expected.items():
        if coverage.get(name) is None or pd.Timestamp(coverage[name])<pd.Timestamp(month):
            alert('actualizacion',f'{name}: última cobertura {coverage.get(name)}; esperada {month}')
    # Meses objetivo y cobertura configurada, no la fecha del reloj como cobertura inventada.
    if forecast is not None:
        if set(pd.to_datetime(forecast.periodo).dt.strftime('%Y-%m-%d'))!=set(cfg['procedure']['targets']):
            alert('actualizacion','Períodos de las estimaciones no corresponden a los objetivos',True)
        if not np.isfinite(forecast.valor).all() or forecast.valor.lt(0).any():
            alert('resultados','Estimaciones negativas o no finitas',True)
        for dest,group in forecast.groupby('destino'):
            history=tables['mobility'].copy()
            past=history.loc[(history.destino==dest)&(pd.to_datetime(history.fecha)<=pd.Timestamp(cfg['procedure']['cutoff']))]
            monthly=past.groupby('fecha').visitantes.sum().sort_index()
            if not monthly.empty:
                reference=float(monthly.iloc[-1])
                variation=(group.valor-reference).abs()/reference if reference>0 else pd.Series(np.inf,index=group.index)
                if variation.gt(cfg['monitoring']['max_relative_change']).any():
                    alert('resultados',f'{dest}: variación > {cfg["monitoring"]["max_relative_change"]:.0%} frente al último observado; revisar, sin inferir pérdida de precisión')
        try:
            approved=load_approved(output,cfg.get('environment','production'))
            if approved:
                old=approved['forecast'][['destino','periodo','valor']].copy()
                old['periodo']=pd.to_datetime(old.periodo)
                current=forecast[['destino','periodo','valor']].copy();current['periodo']=pd.to_datetime(current.periodo)
                compared=current.merge(old,on=['destino','periodo'],suffixes=('_nueva','_previa'))
                change=(compared.valor_nueva-compared.valor_previa).abs()/compared.valor_previa.where(compared.valor_previa.gt(0))
                zero_change=compared.valor_previa.eq(0)&compared.valor_nueva.ne(0)
                if change.gt(cfg['monitoring']['max_relative_change']).any() or zero_change.any():
                    alert('resultados','Cambio elevado frente a la versión aprobada previa; requiere revisión, no demuestra pérdida de precisión')
        except (ValueError,OSError,KeyError):alert('integridad','Versión aprobada anterior no verificable',True)
    summary={f'{c["fuente"]}/{c["control"]}':dict(errores=c['errores'],advertencias=c['advertencias']) for c in checks}
    previous=Path(output)/'ultimo_monitoreo.json'
    if previous.exists():
        old=json.loads(previous.read_text())
        for key,value in summary.items():
            if value!=old.get('calidad',{}).get(key):alert('calidad',f'Cambio de faltantes/duplicados/cobertura: {key}')
        for name,value in coverage.items():
            if name in old.get('cobertura',{}) and value!=old['cobertura'][name]:alert('actualizacion',f'Cambio en cobertura de {name}: {old["cobertura"][name]} → {value}')
    for c in checks:
        if c['estado']=='FAIL':alert('calidad',c['fuente']+'/'+c['control'],True)
        elif c['estado']=='WARN':alert('calidad',c['fuente']+'/'+c['control']+': '+c['detalle'])
    return dict(cobertura=coverage,calidad=summary,alertas=alerts,critico=any(a['critico'] for a in alerts),
        criterio='Cobertura fijada en configuración; variación no equivale a error predictivo')
