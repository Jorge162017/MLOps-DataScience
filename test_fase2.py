"""Integración MLflow, versiones verificadas, monitoreo y tablero sin entrenamiento."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from mlflow.tracking import MlflowClient
from streamlit.testing.v1 import AppTest
from demo import main
from monitoreo import monitor
from seguimiento import settings
from tablero import dashboard_state
from utilidades import ROOT,write_json,sha256
from versiones import load_approved,point_to,publish


class PhaseTwoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        cls.env=patch.dict(os.environ,{'LAB_STATE':str(cls.root),'MLFLOW_DISABLE_AGENT_HINT':'1',
            'MLFLOW_TRACKING_URI':'sqlite:///'+str(cls.root/'mlflow.db'),'MLFLOW_ARTIFACT_ROOT':str(cls.root/'artifacts')})
        cls.env.start()
        with contextlib.redirect_stdout(io.StringIO()):cls.evidence=main(cls.root/'demo')
        cls.output=Path(cls.evidence['output'])

    @classmethod
    def tearDownClass(cls):cls.env.stop();cls.temp.cleanup()

    def test_failed_run_has_cause_and_no_predictive_metrics(self):
        report=json.loads(Path(self.evidence['fallo']['reporte']).read_text())
        uri,_=settings();r=MlflowClient(tracking_uri=uri).get_run(report['mlflow_run_id'])
        self.assertEqual(r.info.status,'FAILED');self.assertIn('unicidad',r.data.tags['pipeline.error'])
        self.assertFalse(any('MAE' in key for key in r.data.metrics))
        self.assertTrue(self.evidence['manifiesto_intacto_ante_fallo'])

    def test_tracking_artifacts_and_parameters_persist(self):
        version=load_approved(self.output,'synthetic');r=version['report']
        uri,_=settings();client=MlflowClient(tracking_uri=uri);run=client.get_run(r['mlflow_run_id'])
        self.assertEqual(run.info.status,'FINISHED')
        self.assertEqual(run.data.tags['environment'],'synthetic')
        self.assertIn('source.mobility.sha256',run.data.params)
        self.assertIn('procedure.cutoff',run.data.params)
        names={x.path for x in client.list_artifacts(run.info.run_id,'ejecucion')}
        self.assertIn('ejecucion/parametros.json',names);self.assertIn('ejecucion/estimaciones.csv',names)

    def test_production_cannot_load_synthetic_version(self):
        with self.assertRaises(ValueError):load_approved(self.output,'production')

    def test_rejected_run_cannot_be_published(self):
        with tempfile.TemporaryDirectory() as td:
            version=load_approved(self.output,'synthetic');source=Path(td)/'run';shutil.copytree(version['folder'],source)
            report=json.loads((source/'ejecucion.json').read_text());report['estado']='REJECTED';write_json(source/'ejecucion.json',report)
            with self.assertRaises(ValueError):publish(source,Path(td)/'out','synthetic')

    def test_corrupted_version_is_not_restored(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'salidas';shutil.copytree(self.output,out)
            pointer=out/'aprobada.json';before=pointer.read_bytes()
            version=self.evidence['segunda'];(out/'versiones'/version/'estimaciones.csv').write_text('alterado')
            with self.assertRaises(ValueError):point_to(out,version,'synthetic')
            self.assertEqual(before,pointer.read_bytes())

    def test_no_approved_version_returns_none(self):
        with tempfile.TemporaryDirectory() as td:self.assertIsNone(load_approved(td))

    def test_tracking_failure_prevents_publication(self):
        from pipeline import run
        version=load_approved(self.output,'synthetic')
        cfg=copy.deepcopy(version['config'])
        with tempfile.TemporaryDirectory() as td:
            cfg['output_dir']=td;config=Path(td)/'config.json';write_json(config,cfg)
            pointer=Path(td)/'aprobada.json';write_json(pointer,dict(run_id='previa'));before=pointer.read_bytes()
            with patch.dict(os.environ,{'LAB_OUTPUT':td}),patch('pipeline.Tracker.record',side_effect=OSError('Seguimiento no disponible')),contextlib.redirect_stdout(io.StringIO()):
                result=run(config)
            self.assertEqual(result,1);self.assertEqual(before,pointer.read_bytes())
            self.assertFalse(list((Path(td)/'versiones').glob('*')))

    def test_monitoring_stale_quality_and_extreme_variation(self):
        version=load_approved(self.output,'synthetic');cfg=version['config']
        from fuentes import read_sources,check_sources
        tables=read_sources(cfg,ROOT);checks,dates=check_sources(tables,cfg)
        dates['mobility']=dates['mobility']-pd.DateOffset(years=1)
        forecast=version['forecast'].copy();forecast['valor']=1e9
        with tempfile.TemporaryDirectory() as td:
            write_json(Path(td)/'ultimo_monitoreo.json',dict(calidad={},cobertura={}))
            result=monitor(cfg,tables,dates,checks,forecast,td)
        kinds={a['tipo'] for a in result['alertas']}
        self.assertEqual(kinds,{'calidad','actualizacion','resultados'})
        self.assertFalse(result['critico'])

    def test_monitoring_negative_results_are_critical(self):
        version=load_approved(self.output,'synthetic');cfg=version['config']
        from fuentes import read_sources,check_sources
        tables=read_sources(cfg,ROOT);checks,dates=check_sources(tables,cfg)
        forecast=version['forecast'].copy();forecast.loc[0,'valor']=-1
        with tempfile.TemporaryDirectory() as td:result=monitor(cfg,tables,dates,checks,forecast,td)
        self.assertTrue(result['critico'])

    def test_board_reads_restored_version_and_filters_do_not_fit(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'salidas';shutil.copytree(self.output,out)
            with patch.dict(os.environ,{'LAB_OUTPUT':str(out),'LAB_ENVIRONMENT':'synthetic','LAB_ADMIN':'1'}):
                at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
                self.assertFalse(at.exception)
                at.radio[0].set_value('Estimaciones').run();self.assertFalse(at.exception)
                first=at.get('plotly_chart')[0].proto.spec
                at.selectbox[1].set_value(self.evidence['segunda']).run()
                at.button[0].click().run();self.assertFalse(at.exception)
                second=at.get('plotly_chart')[0].proto.spec
                self.assertNotEqual(first,second)
                self.assertEqual(load_approved(out,'synthetic')['pointer']['version'],self.evidence['segunda'])
                # Una selección solo consulta archivos. No se importa el pipeline en app.py.
                with patch('pipeline.national_forecast',side_effect=AssertionError('No se debe ajustar')):
                    at.selectbox[0].set_value('Isla De Flores').run()
                self.assertFalse(at.exception)

    def test_board_empty_and_observed_only_no_candidate_leak(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'salidas';shutil.copytree(self.output,out);(out/'aprobada.json').unlink()
            with patch.dict(os.environ,{'LAB_OUTPUT':str(out),'LAB_ENVIRONMENT':'synthetic','LAB_ADMIN':'0'}):
                at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
                self.assertFalse(at.exception)
                self.assertTrue(any('Estimaciones no disponibles' in w.value for w in at.warning))
                at.radio[0].set_value('Estimaciones').run();self.assertFalse(at.get('plotly_chart'))
                for section in ['Movilidad y Tikal','Conectividad aérea','Alojamiento']:
                    at.radio[0].set_value(section).run();self.assertFalse(at.exception)


if __name__=='__main__':unittest.main(verbosity=2)
