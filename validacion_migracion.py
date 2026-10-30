"""Controles de la fuente nacional mensual; no ajusta modelos."""
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
NUMERIC = ["Año", "Mes cod", "Viajero"]
DIMENSIONS = ["Vía", "Frontera", "País", "Región", "Región dos", "Regiones OMT", "MCEO", "Agrupación Residencia", "Tipo de Viajero"]

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
