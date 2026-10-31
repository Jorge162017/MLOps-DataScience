"""Lectura, contratos de calidad y preparación de las fuentes del grupo 2."""
from pathlib import Path
import unicodedata

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype

from validacion_migracion import validate_data, prepare

MONTHS = {m: i + 1 for i, m in enumerate(['enero', 'febrero', 'marzo', 'abril', 'mayo',
    'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'])}


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value).strip().upper()) if not unicodedata.combining(c))


def periods(year, month):
    year, month = pd.to_numeric(year, errors='coerce'), pd.to_numeric(month, errors='coerce')
    valid = year.between(1900, 2200) & month.between(1, 12) & year.mod(1).eq(0) & month.mod(1).eq(0)
    result = pd.Series(pd.NaT, index=year.index, dtype='datetime64[ns]')
    result.loc[valid] = pd.to_datetime(dict(year=year[valid].astype(int), month=month[valid].astype(int), day=1))
    return result


def expected(spec):
    if 'coverage' in spec:
        return pd.DatetimeIndex(pd.to_datetime(spec['coverage'],format='%Y-%m'))
    if 'years' in spec:
        return pd.DatetimeIndex([pd.Timestamp(y, m, 1) for y in spec['years'] for m in range(1, 13)])
    return pd.date_range(spec['start'], spec['end'], freq='MS')


def read_sources(cfg, root):
    specs = {'migration': cfg['migration'], **cfg['sources']}
    tables = {}
    for name, spec in specs.items():
        path = root / spec['path']
        if path.suffix == '.csv':
            frame = pd.read_csv(path)
        else:
            frame = pd.read_excel(path, sheet_name=spec['sheet'], header=spec.get('header', 0))
        frame.columns = frame.columns.str.strip()
        for col in frame.select_dtypes(include=['object', 'string']):
            frame[col] = frame[col].map(lambda x: x.strip() if isinstance(x, str) else x)
        if name in ['capacity', 'occupancy'] and 'departamento' in frame:
            frame = frame.loc[frame.departamento.eq(spec['department'])].copy()
        tables[name] = frame
    return tables


def validate_table(name, df, required, numbers, key, dates, exp, *, optional=None,
                   errors=0, warnings=0, detail='', groups=None):
    """Siempre devuelve los seis controles; esquema inválido bloquea cálculos posteriores."""
    optional = optional or {}
    result = []

    def add(control, failures=0, warns=0, explanation=''):
        result.append({'fuente': name, 'control': control,
            'estado': 'FAIL' if failures else 'WARN' if warns else 'PASS',
            'errores': int(failures), 'advertencias': int(warns), 'detalle': explanation})

    absent = set(required) - set(df)
    incompatible = [c for c in numbers if c in df and not is_numeric_dtype(df[c])]
    texts = [c for c in set(required) - set(numbers) - {'fecha'} if c in df
             and not df[c].dropna().map(lambda x: isinstance(x, str)).all()]
    add('columnas_tipos', len(absent) + len(incompatible) + len(texts),
        explanation=f'Ausentes: {sorted(absent)}; numéricas incompatibles: {incompatible}; textuales incompatibles: {texts}')
    missing_periods = len(exp.difference(pd.DatetimeIndex(dates.dropna().unique())))
    if groups is not None:
        # Cada destino/flujo debe cubrir todos los períodos esperados, no solo el conjunto.
        missing_periods = sum(len(exp.difference(pd.DatetimeIndex(dates.loc[mask].dropna().unique()))) for mask in groups)
    add('fechas_cobertura', dates.isna().sum() + missing_periods, (~dates.isin(exp) & dates.notna()).sum(),
        f'Fechas inválidas: {int(dates.isna().sum())}; meses/grupos sin cobertura: {missing_periods}. Ausencias no se convierten en cero.')
    add('unicidad', df.duplicated(key).sum() if set(key) <= set(df) else 1,
        explanation=f'Clave: {key}; se comprueba antes de agregar')
    missing_errors, allowed = 0, 0
    for col in required:
        if col in df:
            null = df[col].isna() | df[col].map(lambda x: isinstance(x, str) and not x.strip())
            permitted = optional.get(col, pd.Series(False, index=df.index))
            allowed += int((null & permitted).sum())
            missing_errors += int((null & ~permitted).sum())
    add('faltantes', missing_errors, allowed, f'Faltantes permitidos según contrato: {allowed}; faltantes críticos: {missing_errors}')
    bad_values = 0
    for col in numbers:
        if col in df:
            values = pd.to_numeric(df[col], errors='coerce')
            allowed_null = optional.get(col, pd.Series(False, index=df.index)) & values.isna()
            bad_values += int(((~np.isfinite(values) | values.lt(0)) & ~allowed_null).sum())
    add('valores_denominadores', bad_values, explanation='Valores finitos no negativos; cocientes solo con denominador positivo. Ceros legítimos se conservan.')
    add('regla_metodologica', errors, warnings, detail)
    return result


def check_sources(tables, cfg):
    checks = []
    migration_cfg = {'source': cfg['migration'], 'scope': {**cfg['scope'], 'allocation_factor': 1}}
    check, dates = validate_data(tables['migration'], migration_cfg)
    checks.extend(dict(c, fuente='migration') for c in check)
    dates_by_source = {'migration': dates}

    contracts = {
        'mobility': (['destino','sub_grupo','anio','mes','pais','es_consecutivo','fecha','visitantes','dias_persona','permanencia_prom'],
            ['anio','mes','visitantes','dias_persona','permanencia_prom'], ['destino','sub_grupo','anio','mes','pais','es_consecutivo']),
        'tikal': (['año','mes','nacionales','extranjeros','otros','total'], ['año','nacionales','extranjeros','otros','total'], ['año','mes']),
        'airlines': (['Año','mes_numero','Aerolínea','Tipo de Flujo','Pasajeros','Total Mes Aerolínea'],
            ['Año','mes_numero','Pasajeros','Total Mes Aerolínea'], ['Año','mes_numero','Aerolínea','Tipo de Flujo']),
        'airport': (['Año','N° Mes','Tipo de Flujo','Tipo de Pasajero','Pasajeros'], ['Año','N° Mes','Pasajeros'], ['Año','N° Mes','Tipo de Flujo','Tipo de Pasajero']),
        'operations': (['Año','N° Mes','Operador','Tipo de Operación','Operaciones'], ['Año','N° Mes','Operaciones'], ['Año','N° Mes','Operador','Tipo de Operación']),
        'occupancy': (['anio','mes','departamento','indice_ocupacion'], ['anio','mes','indice_ocupacion'], ['anio','mes','departamento']),
        'capacity': (['anio','trimestre','departamento','tipo_alojamiento','establecimientos','habitaciones','plazas_cama'],
            ['anio','trimestre','establecimientos','habitaciones','plazas_cama'], ['anio','trimestre','departamento','tipo_alojamiento'])}

    for name, (required, numbers, key) in contracts.items():
        df, spec = tables[name], cfg['sources'][name]
        dates = pd.Series(pd.NaT, index=df.index, dtype='datetime64[ns]')
        opts, err, warn, groups = {}, 0, 0, None
        detail = ''
        exp = expected(spec) if name != 'capacity' else pd.DatetimeIndex([pd.Timestamp(y, q * 3 - 2, 1) for y, q in spec['cuts']])
        if set(required) <= set(df) and all(is_numeric_dtype(df[c]) for c in numbers):
            if name == 'mobility':
                dates = periods(df.anio, df.mes)
                zero = df.visitantes.eq(0)
                # País es descriptivo para este total por sitio; no eliminar visitantes por falta de país.
                opts = {'pais': pd.Series(True, index=df.index), 'permanencia_prom': zero}
                err += int((pd.to_datetime(df.fecha, errors='coerce') != dates).sum())
                err += int((zero & df.dias_persona.ne(0)).sum())
                positive = df.visitantes.gt(0)
                err += int((~np.isclose(df.loc[positive,'permanencia_prom'], df.loc[positive,'dias_persona'] / df.loc[positive,'visitantes'], rtol=1e-6, atol=1e-6)).sum())
                err += int((~df.destino.isin(cfg['scope']['destinations'])).sum())
                err += int((~df.sub_grupo.eq('Peten')).sum())
                err += int((~df.es_consecutivo.isin(['mayor a 1 dia','menor a 1 dia'])).sum())
                err += int(cfg['scope']['sum_destinations'] is not False or spec['frequency'] != 'monthly')
                err += int(any(normalized(c) in ['DIA','DAY','FECHA DIARIA'] for c in df))
                targets = pd.DatetimeIndex(pd.to_datetime(cfg['procedure']['targets']))
                err += int(dates.isin(targets).sum())
                groups = [df.destino.eq(d) for d in cfg['scope']['destinations']]
                detail = 'Solo movilidad mensual; tres destinos separados, sin deduplicación entre sitios imposible ni suma regional. Enero-febrero ausentes por contrato. Permanencia = días-persona / visitantes solo si visitantes > 0.'
            elif name == 'tikal':
                dates = periods(df['año'], df.mes.str.lower().map(MONTHS))
                err = int((~np.isclose(df[['nacionales','extranjeros','otros']].sum(axis=1), df.total)).sum())
                warn = int(df.total.eq(0).sum())
                detail = 'Total = nacionales + extranjeros + otros; no sumar total con componentes. Ceros históricos se marcan para revisión; boletos no equivalen a personas únicas de Petén.'
            elif name in ['airlines', 'airport', 'operations']:
                dates = periods(df['Año'], df['mes_numero' if name == 'airlines' else 'N° Mes'])
                col = 'Tipo de Operación' if name == 'operations' else 'Tipo de Flujo'
                categories = ['Aterrizaje','Despegue'] if name == 'operations' else ['Entrada','Salida']
                err += int((~df[col].isin(categories)).sum())
                groups = [df[col].eq(c) for c in categories]
                detail = 'Operaciones se mantienen como movimientos de aeronaves, nunca pasajeros.' if name == 'operations' else 'Entrada y Salida separadas; no son turistas únicos.'
                if name == 'airlines':
                    by = df.groupby(['Año','mes_numero','Aerolínea'], dropna=False)
                    sums = by.Pasajeros.sum(); totals = by['Total Mes Aerolínea'].first()
                    err += int((~np.isclose(sums, totals)).sum())
                    err += int(by['Total Mes Aerolínea'].nunique().ne(1).sum())
                    detail += ' Agregar Pasajeros una vez por flujo, no Total Mes Aerolínea repetido. Usar solo 2023 para reconstrucción.'
                elif name == 'airport':
                    segments = ['Doméstico','Internacional','Privado']
                    err += int((~df['Tipo de Pasajero'].isin(segments)).sum())
                    groups = [df[col].eq(flow) & df['Tipo de Pasajero'].eq(segment)
                              for flow in categories for segment in segments]
            elif name == 'occupancy':
                dates = periods(df.anio, df.mes)
                err = int((~df.indice_ocupacion.between(0,1)).sum())
                detail = 'Índice en [0,1]; no confundir fracción con porcentaje ni con visitantes.'
            elif name == 'capacity':
                dates = periods(df.anio, df.trimestre * 3 - 2)
                err = int((~df.trimestre.isin([1,2,3,4])).sum())
                detail = 'Cortes trimestrales/anuales de capacidad; no se suman entre años ni se interpolan como observaciones mensuales.'
        else:
            err = 1
        checks.extend(validate_table(name, df, required, numbers, key, dates, exp,
            optional=opts, errors=err, warnings=warn, detail=detail, groups=groups))
        dates_by_source[name] = dates
    return checks, dates_by_source


def prepare_sources(tables, dates, cfg):
    national = prepare(tables['migration'], dates['migration'],
        {'source': cfg['migration'], 'scope': {**cfg['scope'], 'allocation_factor': 1}})
    mobility = tables['mobility'].assign(periodo=dates['mobility']).groupby(['periodo','destino']).visitantes.sum(min_count=1).unstack('destino')
    tikal = tables['tikal'].assign(periodo=dates['tikal']).set_index('periodo')[['nacionales','extranjeros','otros','total']]
    airport = tables['airport'].assign(periodo=dates['airport']).groupby(['periodo','Tipo de Flujo']).Pasajeros.sum().reset_index().rename(columns={'Tipo de Flujo':'flujo','Pasajeros':'pasajeros'})
    airport['fuente'] = 'AIMM_Consolidado'
    airline = tables['airlines'].assign(periodo=dates['airlines'])
    reconstructed = airline.loc[airline['Año'].eq(2023)].groupby(['periodo','Tipo de Flujo']).Pasajeros.sum().reset_index().rename(columns={'Tipo de Flujo':'flujo','Pasajeros':'pasajeros'})
    reconstructed['fuente'] = 'AIMM_Aerolineas_reconstruccion_2023'
    extension = airline.loc[airline['Año'].eq(2026)].groupby(['periodo','Tipo de Flujo']).Pasajeros.sum().reset_index().rename(columns={'Tipo de Flujo':'flujo','Pasajeros':'pasajeros'})
    extension['fuente'] = 'AIMM_Aerolineas_2026_parcial'
    airport = pd.concat([airport,reconstructed,extension],ignore_index=True).sort_values(['periodo','flujo'])
    if airport.duplicated(['periodo','flujo']).any():
        raise ValueError('Reconstrucción de aeropuerto solapa períodos existentes')
    operator = tables['operations'].assign(periodo=dates['operations']).copy()
    aliases = {'TAG':'T.A.G.','T.A.G.':'T.A.G.','AERORUTAMAYA':'AERO RUTA MAYA','AERO RUTA MAYA':'AERO RUTA MAYA','AVIANCA':'AVIATECA','AVIATECA':'AVIATECA'}
    operator['operador_normalizado'] = operator.Operador.map(lambda s: aliases.get(normalized(s),normalized(s)))
    operator = operator.groupby(['periodo','operador_normalizado','Tipo de Operación']).Operaciones.sum().reset_index()
    airlines = airline.groupby(['periodo','Aerolínea','Tipo de Flujo']).Pasajeros.sum().reset_index()
    occupancy = tables['occupancy'].assign(periodo=dates['occupancy']).set_index('periodo')[['indice_ocupacion']]
    capacity = tables['capacity'].copy()
    return dict(nacional=national, movilidad=mobility, tikal=tikal, aeropuerto=airport,
        operadores=operator, aerolineas=airlines, ocupacion=occupancy, capacidad=capacity)
