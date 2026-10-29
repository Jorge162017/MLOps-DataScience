"""Pruebas del avance; fixtures sintéticos sin datos institucionales."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

import pipeline as p


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads((p.ROOT / "config.json").read_text())
        self.cfg["source"].update(coverage_start="2023-01-01", coverage_end="2026-06-01")
        dates = pd.date_range("2023-01-01", "2026-06-01", freq="MS")
        self.df = pd.DataFrame({"Año": dates.year, "Mes cod": dates.month,
                                "Viajero": 100 + np.arange(len(dates)) * 2.0})
        for column in p.DIMENSIONS:
            self.df[column] = "prueba"
        self.df["Tipo de Viajero"] = "Turista"

    def statuses(self, df, cfg=None):
        checks, _ = p.validate_data(df, cfg or self.cfg)
        return {c["control"]: c["estado"] for c in checks}

    def test_valid_fixture_and_zero_preserved(self):
        self.df.loc[0, "Viajero"] = 0.0
        self.assertEqual(set(self.statuses(self.df).values()), {"PASS"})
        _, dates = p.validate_data(self.df, self.cfg)
        self.assertEqual(p.prepare(self.df, dates, self.cfg).iloc[0], 0)

    def test_missing_column_and_incompatible_numeric_type(self):
        self.assertEqual(self.statuses(self.df.drop(columns="Viajero"))["columnas_tipos"], "FAIL")
        self.df["Viajero"] = self.df.Viajero.astype(str)
        self.assertEqual(self.statuses(self.df)["columnas_tipos"], "FAIL")

    def test_invalid_date_fractional_month_and_missing_coverage(self):
        for value in [13, 1.5, np.inf]:
            broken = self.df.copy()
            broken["Mes cod"] = broken["Mes cod"].astype(float)
            broken.loc[0, "Mes cod"] = value
            self.assertEqual(self.statuses(broken)["fechas_cobertura"], "FAIL")
        self.assertEqual(self.statuses(self.df.iloc[1:])["fechas_cobertura"], "FAIL")

    def test_duplicate_key_with_different_count(self):
        duplicate = self.df.iloc[[0]].copy()
        duplicate["Viajero"] = 999.0
        broken = pd.concat([self.df, duplicate], ignore_index=True)
        self.assertEqual(self.statuses(broken)["unicidad"], "FAIL")

    def test_missing_required_value(self):
        self.df.loc[0, "País"] = "  "
        self.assertEqual(self.statuses(self.df)["faltantes"], "FAIL")

    def test_negative_nan_and_infinite_values(self):
        for value in [-1, np.inf, np.nan]:
            broken = self.df.copy()
            broken.loc[0, "Viajero"] = value
            self.assertEqual(self.statuses(broken)["valores_denominadores"], "FAIL")

    def test_daily_source_and_unknown_category(self):
        self.assertEqual(self.statuses(self.df.assign(Día=1))["regla_metodologica"], "FAIL")
        self.df.loc[0, "Tipo de Viajero"] = "Total"
        self.assertEqual(self.statuses(self.df)["regla_metodologica"], "FAIL")

    def test_nonvisitor_counts_excluded(self):
        extra = self.df.copy()
        extra["Tipo de Viajero"] = "Viajero"
        extra["Viajero"] = 1000000.0
        both = pd.concat([self.df, extra], ignore_index=True)
        _, dates = p.validate_data(both, self.cfg)
        actual = p.prepare(both, dates, self.cfg)
        np.testing.assert_array_equal(actual.to_numpy(), self.df.Viajero.to_numpy())

    def test_invalid_factor_and_period_configuration(self):
        for value in [0, -1, np.inf, 1.1]:
            bad = copy.deepcopy(self.cfg)
            bad["scope"]["allocation_factor"] = value
            with self.assertRaises(ValueError):
                p.validate_config(bad)
        bad = copy.deepcopy(self.cfg)
        bad["procedure"]["evaluation_start"] = "2022-01-01"
        with self.assertRaises(ValueError):
            p.validate_config(bad)

    def test_evaluation_only_uses_history_before_target(self):
        _, dates = p.validate_data(self.df, self.cfg)
        series = p.prepare(self.df, dates, self.cfg)
        original = p.fit
        calls = []

        def tracking(history):
            calls.append(history.index.max())
            return original(history)

        with patch.object(p, "fit", side_effect=tracking):
            evaluation, _, _, _ = p.estimate(series, self.cfg)
        for cutoff, target in zip(calls[:-1], pd.to_datetime(evaluation.periodo)):
            self.assertLess(cutoff, target)
        self.assertEqual(calls[-1], pd.Timestamp("2026-06-01"))

    def test_failed_pipeline_preserves_approved_and_records_no_metrics(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            cfg = copy.deepcopy(self.cfg)
            cfg["output_dir"] = str(folder / "out")
            cfg["source"]["path"] = str(folder / "input.xlsx")
            (folder / "input.xlsx").write_bytes(b"fixture: lectura simulada")
            config = folder / "config.json"
            config.write_text(json.dumps(cfg))
            pointer = folder / "out" / "aprobada.json"
            p.write_json(pointer, {"run_id": "version_previa"})
            before = pointer.read_bytes()
            broken = self.df.drop(columns="Viajero")
            with patch.object(p.pd, "read_excel", return_value=broken), contextlib.redirect_stdout(io.StringIO()):
                status = p.run(config)
            self.assertEqual(status, 1)
            self.assertEqual(pointer.read_bytes(), before)
            reports = list((folder / "out" / "ejecuciones").glob("*/ejecucion.json"))
            report = json.loads(reports[0].read_text())
            self.assertEqual(report["estado"], "FAILED")
            self.assertNotIn("metricas", report)
            self.assertEqual(len(report["controles"]), 6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
