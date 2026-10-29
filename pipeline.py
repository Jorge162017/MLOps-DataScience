"""Avance Lab 11: validación estricta, preparación y estimación fuera del tablero."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import uuid

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from statsmodels.tsa.holtwinters import SimpleExpSmoothing

ROOT = Path(__file__).resolve().parent
NUMERIC = ["Año", "Mes cod", "Viajero"]
DIMENSIONS = ["Vía", "Frontera", "País", "Región", "Región dos", "Regiones OMT",
              "MCEO", "Agrupación Residencia", "Tipo de Viajero"]


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    tmp.replace(path)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_config(cfg):
    source, proc, scope = cfg["source"], cfg["procedure"], cfg["scope"]
    dates = [source["coverage_start"], proc["training_start"], proc["evaluation_start"],
             proc["evaluation_end"], source["coverage_end"], proc["forecast_start"]]
    dates = [pd.Timestamp(d) for d in dates]
    if any(d.day != 1 for d in dates) or dates != sorted(dates):
        raise ValueError("Períodos fuera de orden o no mensuales")
    if dates[1] >= dates[2] or dates[3] > dates[4] or dates[5] != dates[4] + pd.offsets.MonthBegin(1):
        raise ValueError("Se requiere historia anterior a evaluación y pronóstico posterior a cobertura")
    if not isinstance(proc["forecast_months"], int) or proc["forecast_months"] < 1:
        raise ValueError("forecast_months debe ser entero positivo")
    factor = scope["allocation_factor"]
    if not isinstance(factor, (int, float)) or not np.isfinite(factor) or not 0 < factor <= 1:
        raise ValueError("Factor de reparto debe ser finito y estar en (0, 1]")
    threshold = cfg["acceptance"]["max_mae_ratio_to_baseline"]
    if not isinstance(threshold, (int, float)) or not np.isfinite(threshold) or threshold < 0:
        raise ValueError("Umbral MAE inválido")
    if not scope["traveler_types"] or not set(scope["traveler_types"]) <= {"Turista", "Excursionista"}:
        raise ValueError("Tipos de visitante incompatibles con definición del proyecto")
    if not source["key"] or not set(source["key"]) <= set(NUMERIC[:2] + DIMENSIONS):
        raise ValueError("Clave de fuente inválida")
    if not set(source["allowed_missing"]) <= set(DIMENSIONS) - set(source["key"]):
        raise ValueError("No se permiten faltantes en variables críticas ni en la clave")
    if proc["initialization_method"] != "estimated" or proc["optimized"] is not True:
        raise ValueError("Esta versión usa inicialización estimada y ajuste optimizado del Lab 1")


def validate_data(df, cfg):
    """No elimina ni imputa filas: todos los controles se reportan, incluso si falla esquema."""
    checks = []
    required = NUMERIC + DIMENSIONS

    def add(name, failures=0, warnings=0, detail=""):
        checks.append({"control": name, "estado": "FAIL" if failures else "WARN" if warnings else "PASS",
                       "errores": int(failures), "advertencias": int(warnings), "detalle": detail})

    missing = sorted(set(required) - set(df.columns))
    wrong = [c for c in NUMERIC if c in df and not is_numeric_dtype(df[c])]
    wrong_text = [c for c in DIMENSIONS if c in df and not df[c].dropna().map(lambda v: isinstance(v, str)).all()]
    add("columnas_tipos", len(missing) + len(wrong) + len(wrong_text),
        detail=f"Ausentes: {missing}; tipos numéricos incompatibles: {wrong}; dimensiones no textuales: {wrong_text}")

    dates = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    if all(c in df for c in ["Año", "Mes cod"]):
        years, months = pd.to_numeric(df["Año"], errors="coerce"), pd.to_numeric(df["Mes cod"], errors="coerce")
        valid = (years.notna() & months.notna() & years.mod(1).eq(0) & months.mod(1).eq(0)
                 & years.between(1900, 2200) & months.between(1, 12))
        dates.loc[valid] = pd.to_datetime(dict(year=years[valid].astype(int), month=months[valid].astype(int), day=1), errors="coerce")
    expected = pd.date_range(cfg["source"]["coverage_start"], cfg["source"]["coverage_end"], freq="MS")
    selected = df["Tipo de Viajero"].isin(cfg["scope"]["traveler_types"]) if "Tipo de Viajero" in df else pd.Series(False, index=df.index)
    absent = expected.difference(pd.DatetimeIndex(dates[selected].dropna().unique()))
    outside = dates.notna() & ~dates.isin(expected)
    add("fechas_cobertura", int(dates.isna().sum()) + len(absent), int(outside.sum()),
        f"Fechas inválidas: {int(dates.isna().sum())}; meses sin visitantes: {[d.strftime('%Y-%m') for d in absent]}; filas fuera de cobertura: {int(outside.sum())}")

    key = cfg["source"]["key"]
    duplicates = int(df.duplicated(key).sum()) if set(key) <= set(df.columns) else 1
    add("unicidad", duplicates, detail=f"Duplicados adicionales según clave: {duplicates}. Clave: {key}")

    allowed = set(cfg["source"]["allowed_missing"])
    nulls = {}
    for c in required:
        if c in df:
            blank = df[c].isna() | df[c].map(lambda x: isinstance(x, str) and not x.strip())
            nulls[c] = int(blank.sum())
    add("faltantes", sum(n for c, n in nulls.items() if c not in allowed),
        sum(n for c, n in nulls.items() if c in allowed), f"Ausencias por columna: {nulls}; permitidas: {sorted(allowed)}")

    values = pd.to_numeric(df["Viajero"], errors="coerce") if "Viajero" in df else pd.Series([np.nan])
    bad = ~np.isfinite(values) | values.lt(0)
    add("valores_denominadores", int(bad.sum()), detail="Conteos negativos/no finitos bloquean. La estimación no divide conteos; el cociente MAE se define solo si la referencia no es cero. Factor validado en (0,1].")

    # La identidad del libro no puede inferirse solo de sus cantidades: requiere procedencia documentada.
    monthly = cfg["source"]["frequency"] == "monthly" and not any(str(c).strip().lower() in {"día", "dia", "day", "fecha diaria"} for c in df)
    types = set(df["Tipo de Viajero"].dropna()) if "Tipo de Viajero" in df else set()
    known_types = {"Turista", "Excursionista", "Cruceristas", "Viajero"}
    add("regla_metodologica", int(not monthly) + len(types - known_types),
        detail=f"Fuente declarada mensual sin columna diaria: {monthly}; categorías desconocidas: {sorted(types - known_types)}. Se agregan solo Turista + Excursionista, nunca Viajero ni Cruceristas ni presencias diarias.")
    return checks, dates


def prepare(df, dates, cfg):
    mask = df["Tipo de Viajero"].isin(cfg["scope"]["traveler_types"])
    monthly = df.loc[mask, ["Viajero"]].assign(Fecha=dates[mask]).groupby("Fecha")["Viajero"].sum(min_count=1)
    expected = pd.date_range(cfg["source"]["coverage_start"], cfg["source"]["coverage_end"], freq="MS")
    monthly = monthly.reindex(expected) * cfg["scope"]["allocation_factor"]
    monthly.index.name = "periodo"
    if monthly.isna().any():
        raise ValueError("La serie preparada contiene meses ausentes; no se sustituyen por cero")
    return monthly


def fit(history):
    # Mismo algoritmo/configuración SES del Lab 1, reestimado en historia 2023+.
    return SimpleExpSmoothing(history.to_numpy(), initialization_method="estimated").fit(optimized=True)


def estimate(monthly, cfg):
    proc = cfg["procedure"]
    series = monthly.loc[proc["training_start"]:]
    rows = []
    for month in pd.date_range(proc["evaluation_start"], proc["evaluation_end"], freq="MS"):
        history = series.loc[series.index < month]
        if len(history) < 2:
            raise ValueError("Historia insuficiente para ajustar SES")
        fitted = fit(history)
        rows.append({"periodo": month.strftime("%Y-%m-%d"), "observado": float(series.loc[month]),
                     "estimado": float(fitted.forecast(1)[0]), "referencia": float(history.iloc[-1]),
                     "ajuste_hasta": history.index[-1].strftime("%Y-%m-%d"),
                     "alpha": float(fitted.params["smoothing_level"])})
    evaluation = pd.DataFrame(rows)
    metrics = {}
    for col in ["estimado", "referencia"]:
        errors = evaluation[col] - evaluation["observado"]
        metrics[col] = {"MAE": float(errors.abs().mean()), "RMSE": float(np.sqrt((errors ** 2).mean()))}
    baseline = metrics["referencia"]["MAE"]
    metrics["ratio_MAE"] = metrics["estimado"]["MAE"] / baseline if baseline > 0 else None
    metrics["meses"] = len(rows)
    model = fit(series)
    periods = pd.date_range(proc["forecast_start"], periods=proc["forecast_months"], freq="MS")
    forecast = pd.DataFrame({"periodo": periods.strftime("%Y-%m-%d"), "valor": model.forecast(len(periods))})
    parameters = {"alpha": float(model.params["smoothing_level"]), "nivel_inicial": float(model.params["initial_level"]),
                  "nivel_final": float(model.level[-1]), "formula": "l_t = alpha*y_t + (1-alpha)*l_(t-1); y_(T+h) = l_T",
                  "ajuste_desde": series.index[0].strftime("%Y-%m-%d"), "ajuste_hasta": series.index[-1].strftime("%Y-%m-%d")}
    return evaluation, metrics, forecast, parameters


def git_state():
    def call(*args):
        try:
            return subprocess.check_output(["/usr/bin/git", "-C", str(ROOT), *args], stderr=subprocess.DEVNULL, text=True).strip()
        except (OSError, subprocess.CalledProcessError):
            return None
    return {"commit": call("rev-parse", "HEAD"), "working_tree_status": call("status", "--porcelain"),
            "nota": "Un commit nulo o un árbol modificado no acredita una versión confirmada. Se guarda también la huella del pipeline."}


def run(config_path):
    cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
    validate_config(cfg)
    np.random.seed(cfg["procedure"]["seed"])
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
    output = ROOT / cfg["output_dir"]
    folder = output / "ejecuciones" / run_id
    folder.mkdir(parents=True, exist_ok=False)
    report = {"run_id": run_id, "inicio": now(), "estado": "RUNNING", "etapas": [], "controles": [],
              "config_sha256": sha256(config_path), "pipeline_sha256": sha256(__file__), "git": git_state(),
              "dependencias": {name: importlib.metadata.version(name) for name in ["pandas", "numpy", "openpyxl", "statsmodels"]}}
    write_json(folder / "config.json", cfg)

    def stage(name):
        report["etapas"].append({"etapa": name, "fin": now()})

    try:
        source = ROOT / cfg["source"]["path"]
        report["fuente"] = {"ruta": cfg["source"]["path"], "sha256": sha256(source), "hoja": cfg["source"]["sheet"]}
        df = pd.read_excel(source, sheet_name=cfg["source"]["sheet"])
        report["filas_fuente"] = len(df)
        stage("lectura")
        checks, dates = validate_data(df, cfg)
        report["controles"] = checks
        write_json(folder / "calidad.json", checks)
        if any(c["estado"] == "FAIL" for c in checks):
            raise ValueError("Control crítico fallido: " + ", ".join(c["control"] for c in checks if c["estado"] == "FAIL"))
        stage("validacion")
        monthly = prepare(df, dates, cfg)
        monthly.rename("visitantes").to_csv(folder / "serie_mensual.csv")
        stage("preparacion")
        evaluation, metrics, forecast, parameters = estimate(monthly, cfg)
        evaluation.to_csv(folder / "evaluacion.csv", index=False)
        write_json(folder / "metricas.json", metrics)
        write_json(folder / "parametros.json", parameters)
        stage("ajuste_evaluacion")
        forecast = forecast.assign(destino=cfg["scope"]["destination"], unidad=cfg["scope"]["unit"],
                                   run_id=run_id, fecha_generacion=now(), version=cfg["procedure"]["version"], tipo="estimado")
        integrity = (len(forecast) == cfg["procedure"]["forecast_months"] and not forecast.periodo.duplicated().any()
                     and np.isfinite(forecast.valor).all() and forecast.valor.ge(0).all()
                     and np.isfinite(evaluation[["observado", "estimado", "referencia"]]).all().all())
        forecast.to_csv(folder / "estimaciones.csv", index=False)
        stage("estimaciones")
        baseline, candidate = metrics["referencia"]["MAE"], metrics["estimado"]["MAE"]
        accepted = bool(integrity and candidate <= baseline * cfg["acceptance"]["max_mae_ratio_to_baseline"])
        report.update(metricas=metrics, integridad_salidas=bool(integrity), aprobado=accepted,
                      estado="APPROVED" if accepted else "REJECTED",
                      motivo="Regla de calidad, integridad y MAE aplicada sin alterar umbral")
        # Los archivos están completos antes de sustituir atómicamente el manifiesto.
        if accepted:
            manifest = {"run_id": run_id, "estimaciones": str((folder / "estimaciones.csv").relative_to(output)),
                        "metricas": str((folder / "metricas.json").relative_to(output)), "fecha": now()}
            write_json(output / "aprobada.json", manifest)
            report["publicacion"] = "Manifiesto de versión aprobada actualizado"
        else:
            report["publicacion"] = "Candidata rechazada; se conserva el manifiesto aprobado existente, si hay"
        stage("decision_publicacion")
    except Exception as exc:
        report.update(estado="FAILED", error=f"{type(exc).__name__}: {exc}",
                      publicacion="Sin reemplazo de versión aprobada")
    finally:
        report["fin"] = now()
        write_json(folder / "ejecucion.json", report)
    print(json.dumps({"run_id": run_id, "estado": report["estado"], "reporte": str(folder / "ejecucion.json"),
                      "error": report.get("error"), "metricas": report.get("metricas")}, ensure_ascii=False, indent=2))
    return 1 if report["estado"] == "FAILED" else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config.json")
    args = parser.parse_args()
    sys.exit(run(args.config))
