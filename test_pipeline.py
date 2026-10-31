"""Contratos de Petén, aislamiento temporal y fallo seguro con fixtures sintéticos."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import os
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
import fuentes as f
import pipeline as p
from validacion_migracion import DIMENSIONS


def fixtures(cfg):
    dates=pd.date_range(cfg['migration']['coverage_start'],cfg['migration']['coverage_end'],freq='MS')
    migration=pd.DataFrame({'Año':dates.year,'Mes cod':dates.month,'Viajero':1000.0})
    for col in DIMENSIONS:migration[col]='prueba'
    migration['Tipo de Viajero']='Turista'
    tables={'migration':migration}
    for name,spec in cfg['sources'].items():
        dates=f.expected(spec) if name!='capacity' else [pd.Timestamp(y,q*3-2,1) for y,q in spec['cuts']]
        rows=[]
        for date in dates:
            y,m=date.year,date.month
            if name=='mobility':
                for dest in cfg['scope']['destinations']:
                    rows.append(dict(destino=dest,sub_grupo='Peten',anio=y,mes=m,pais='Guatemala',es_consecutivo='mayor a 1 dia',fecha=date,visitantes=100.,dias_persona=200.,permanencia_prom=2.))
            if name=='tikal':rows.append({'año':y,'mes':list(f.MONTHS)[m-1],'nacionales':20,'extranjeros':30,'otros':0,'total':50})
            if name=='airlines':
                for flow in ['Entrada','Salida']:rows.append({'Año':y,'mes_numero':m,'Aerolínea':'TAG','Tipo de Flujo':flow,'Pasajeros':10,'Total Mes Aerolínea':20})
            if name=='airport':
                for flow in ['Entrada','Salida']:
                    for segment in ['Doméstico','Internacional','Privado']:
                        rows.append({'Año':y,'N° Mes':m,'Tipo de Flujo':flow,'Tipo de Pasajero':segment,'Pasajeros':10})
            if name=='operations':
                for kind in ['Aterrizaje','Despegue']:rows.append({'Año':y,'N° Mes':m,'Operador':'TAG','Tipo de Operación':kind,'Operaciones':5})
            if name=='occupancy':rows.append(dict(anio=y,mes=m,departamento='Petén',indice_ocupacion=.5))
            if name=='capacity':rows.append(dict(anio=y,trimestre=(m+2)//3,departamento='Petén',tipo_alojamiento='Hotel',establecimientos=1,habitaciones=10,plazas_cama=20))
        tables[name]=pd.DataFrame(rows)
    return tables


class PetenTests(unittest.TestCase):
    def setUp(self):
        self.cfg=json.loads((p.ROOT/'config.json').read_text()); self.tables=fixtures(self.cfg)

    def statuses(self):
        checks,dates=f.check_sources(self.tables,self.cfg)
        return {(x['fuente'],x['control']):x['estado'] for x in checks}

    def prepared(self):
        _,dates=f.check_sources(self.tables,self.cfg)
        return f.prepare_sources(self.tables,dates,self.cfg)

    def test_all_eight_sources_valid(self):
        statuses=self.statuses();self.assertEqual(len(statuses),48);self.assertEqual(set(statuses.values()),{'PASS'})

    def test_missing_column_and_wrong_type(self):
        self.tables['mobility']=self.tables['mobility'].drop(columns='visitantes')
        self.assertEqual(self.statuses()['mobility','columnas_tipos'],'FAIL')
        self.tables=fixtures(self.cfg);self.tables['occupancy']['indice_ocupacion']='texto'
        # A type-incompatible source must fail without crashing the quality report.
        self.assertEqual(self.statuses()['occupancy','columnas_tipos'],'FAIL')

    def test_coverage_each_destination(self):
        m=self.tables['mobility']; self.tables['mobility']=m.drop(index=0)
        self.assertEqual(self.statuses()['mobility','fechas_cobertura'],'FAIL')

    def test_fractional_and_invalid_dates(self):
        self.tables['mobility']['mes']=self.tables['mobility'].mes.astype(float)
        self.tables['mobility'].loc[0,'mes']=1.5
        self.assertEqual(self.statuses()['mobility','fechas_cobertura'],'FAIL')

    def test_duplicate_key_even_different_count(self):
        m=self.tables['mobility']; duplicate=m.iloc[[0]].copy(); duplicate['visitantes']=90
        self.tables['mobility']=pd.concat([m,duplicate],ignore_index=True)
        self.assertEqual(self.statuses()['mobility','unicidad'],'FAIL')

    def test_zero_denominator_missing_permanence_permitted(self):
        m=self.tables['mobility'];m.loc[0,['visitantes','dias_persona']]=0;m.loc[0,'permanencia_prom']=np.nan;m.loc[0,'pais']=np.nan
        self.assertEqual(self.statuses()['mobility','faltantes'],'WARN')
        self.assertEqual(self.statuses()['mobility','regla_metodologica'],'PASS')
        m.loc[0,'dias_persona']=1
        self.assertEqual(self.statuses()['mobility','regla_metodologica'],'FAIL')

    def test_missing_critical_and_nonfinite_counts(self):
        self.tables['mobility'].loc[0,'destino']=None
        self.assertEqual(self.statuses()['mobility','faltantes'],'FAIL')
        self.tables['airlines']['Pasajeros']=self.tables['airlines'].Pasajeros.astype(float)
        for value in [-1,np.inf]:
            self.tables['airlines'].loc[0,'Pasajeros']=value
            self.assertEqual(self.statuses()['airlines','valores_denominadores'],'FAIL')

    def test_tikal_total_and_occupancy_range(self):
        self.tables['tikal'].loc[0,'total']=999
        self.tables['occupancy'].loc[0,'indice_ocupacion']=50
        s=self.statuses();self.assertEqual(s['tikal','regla_metodologica'],'FAIL');self.assertEqual(s['occupancy','regla_metodologica'],'FAIL')

    def test_no_daily_source_and_no_sum_destinations(self):
        self.tables['mobility']['Día']=1
        self.assertEqual(self.statuses()['mobility','regla_metodologica'],'FAIL')
        self.cfg['scope']['sum_destinations']=True
        with self.assertRaises(ValueError):p.validate_config(self.cfg)

    def test_reconstruction_2023_no_double_count_and_separate_units(self):
        d=self.prepared();a=d['aeropuerto']
        self.assertEqual(len(a),52*2)
        self.assertFalse(a.duplicated(['periodo','flujo']).any())
        self.assertEqual(a.loc[a.periodo.dt.year.eq(2023),'pasajeros'].sum(),240)
        self.assertEqual(d['operadores'].Operaciones.sum(),52*2*5)
        self.assertEqual(len(d['capacidad']),5)

    def test_allocation_ignores_future_and_zero_denominator_blocks(self):
        d=self.prepared();cutoff=pd.Timestamp('2025-12-01');dest=self.cfg['scope']['destinations'][0]
        factor,_=p.allocation(d['nacional'],d['movilidad'],dest,cutoff,self.cfg)
        d['movilidad'].loc[d['movilidad'].index>cutoff,dest]=1e12
        actual,_=p.allocation(d['nacional'],d['movilidad'],dest,cutoff,self.cfg)
        self.assertEqual(factor,actual)
        d['nacional'].loc['2025-09-01']=0
        with self.assertRaises(ValueError):p.allocation(d['nacional'],d['movilidad'],dest,cutoff,self.cfg)

    def test_forecast_no_future_leakage(self):
        d=self.prepared();n=d['nacional'];n[:]=1000+np.arange(len(n))*2+100*np.sin(np.arange(len(n))*2*np.pi/12)
        forecast,_,_=p.estimate(n,d['movilidad'],self.cfg)
        n.loc[n.index>pd.Timestamp('2025-12-01')]=1e15
        d['movilidad'].loc[d['movilidad'].index>pd.Timestamp('2025-12-01')]=1e15
        actual,_,_=p.estimate(n,d['movilidad'],self.cfg)
        np.testing.assert_allclose(forecast.valor,actual.valor,rtol=0,atol=1e-8)
        self.assertEqual(len(actual),6)

    def test_validation_cutoffs_and_hidden_two_month_block(self):
        d=self.prepared();n=d['nacional'];n[:]=1000+np.arange(len(n))*2+100*np.sin(np.arange(len(n))*2*np.pi/12)
        a,_,_,_=p.evaluate(n,d['movilidad'],self.cfg)
        self.assertTrue((a.corte<a.periodo).all())
        self.assertTrue((pd.to_datetime(a.calibracion_hasta)<=a.corte).all())
        d['movilidad'].loc['2025-10-01':'2025-11-01']*=100
        b,_,_,_=p.evaluate(n,d['movilidad'],self.cfg)
        mask=a.corte.eq(pd.Timestamp('2025-09-01'))
        np.testing.assert_array_equal(a.loc[mask,'estimado'],b.loc[mask,'estimado'])

    def test_baseline_zero_ratio_not_infinite(self):
        m=p.error_metrics(pd.DataFrame(dict(observado=[0,0],estimado=[0,1],referencia=[0,0])))
        self.assertIsNone(m['ratio_MAE']);self.assertEqual(m['estimado']['MAE'],.5)

    def test_failure_preserves_existing_manifest_no_metrics(self):
        with tempfile.TemporaryDirectory() as td:
            cfg=copy.deepcopy(self.cfg);cfg['output_dir']=td
            for spec in [cfg['migration'],*cfg['sources'].values()]:
                spec['path']=str(Path(td)/'fixture');Path(spec['path']).write_text('sintético')
            config=Path(td)/'config.json';p.write_json(config,cfg)
            pointer=Path(td)/'aprobada.json';p.write_json(pointer,dict(run_id='previa'));before=pointer.read_bytes()
            self.tables['mobility']=self.tables['mobility'].drop(columns='visitantes')
            cfg['environment']='synthetic';p.write_json(config,cfg)
            env={'LAB_STATE':td,'MLFLOW_TRACKING_URI':'sqlite:///'+str(Path(td)/'mlflow.db'),'MLFLOW_ARTIFACT_ROOT':str(Path(td)/'artifacts')}
            with patch.dict(os.environ,env),patch.object(p,'read_sources',return_value=self.tables),contextlib.redirect_stdout(io.StringIO()):status=p.run(config)
            self.assertEqual(status,1);self.assertEqual(pointer.read_bytes(),before)
            report=json.loads(next((Path(td)/'ejecuciones').glob('*/ejecucion.json')).read_text())
            self.assertEqual(report['estado'],'FAILED');self.assertNotIn('metricas',report)
            self.assertEqual(len(report['controles']),48)


if __name__=='__main__':unittest.main(verbosity=2)
