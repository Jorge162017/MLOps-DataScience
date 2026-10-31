"""Observatorio de Tikal y Flores. La interfaz nunca ajusta modelos."""
import json
import os
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from tablero import dashboard_state
from versiones import point_to,read_version
from utilidades import store_lock

st.set_page_config(page_title='Tikal y Flores · Observatorio',page_icon='🌿',layout='wide')
output=Path(os.environ.get('LAB_OUTPUT','resultados_peten'))
environment=os.environ.get('LAB_ENVIRONMENT','production')
st.title('Tikal y Flores · Observatorio turístico')
st.caption('Movilidad, Tikal, conectividad aérea y alojamiento · Grupo 2')
if environment=='synthetic':st.warning('DEMOSTRACIÓN CON DATOS SINTÉTICOS · No son cifras de Petén')
try:state=dashboard_state(output,environment)
except Exception as exc:
    st.error('Los archivos disponibles no superan la verificación de integridad. Revisa la actualización antes de consultarlos.')
    st.stop()
observed,approved=state['observed'],state['approved']
if observed is None and approved is None:
    st.info('Todavía no hay datos validados disponibles. Ejecuta el pipeline para iniciar el observatorio.')
    st.stop()
if observed:
    st.caption('Datos preparados: '+pd.Timestamp(observed['meta']['fecha']).tz_convert('America/Guatemala').strftime('%d/%m/%Y %H:%M')+' · Guatemala')
if approved is None:
    st.warning('Estimaciones no disponibles: todavía no hay una versión que cumpla la regla de aceptación para los tres destinos.')
else:
    report=approved['report'];forecast=approved['forecast']
    st.success('Se consulta una versión aprobada. Las estimaciones se distinguen de los valores observados.')
    st.caption('Estimaciones actualizadas: '+pd.Timestamp(report['fin']).tz_convert('America/Guatemala').strftime('%d/%m/%Y %H:%M'))
st.info('Los sitios pueden compartir visitantes. Sus cantidades no se suman como personas únicas de Petén. Boletos, pasajeros y vuelos miden actividades diferentes.')

if observed:
    t=observed['tables'];m=t['movilidad'];destinations=[c for c in m if c!='periodo']
    m=m.set_index(pd.to_datetime(m.periodo)).drop(columns='periodo')
    m=m.reindex(pd.date_range(m.index.min(),m.index.max(),freq='MS')).rename_axis('periodo').reset_index()
else:
    destinations=sorted(approved['forecast'].destino.unique());t={};m=pd.DataFrame()
destination=st.selectbox('Destino de movilidad',destinations)
section=st.radio('Consulta',['Movilidad y Tikal','Conectividad aérea','Alojamiento','Estimaciones'],horizontal=True)

def chart(fig,key):
    fig.update_layout(template='plotly_white',font=dict(size=14),margin=dict(l=20,r=20,t=30,b=20),legend_title_text='')
    st.plotly_chart(fig,width='stretch',key=key)

if section=='Estimaciones':
    st.subheader('Enero y febrero de 2026')
    if approved is None:
        st.write('Las candidatas rechazadas se conservan para revisión técnica y no se presentan como estimaciones aprobadas.')
    else:
        f=approved['forecast'].query('destino == @destination');fig=go.Figure()
        if not m.empty:
            fig.add_scatter(x=m.periodo,y=m[destination],name='Observado',mode='lines+markers',line=dict(color='#20735F'))
        fig.add_scatter(x=f.periodo,y=f.valor,name='Estimado aprobado',mode='lines+markers',line=dict(dash='dash',color='#B26A16'))
        fig.update_yaxes(title='Visitantes mensuales por sitio');chart(fig,'aprobadas')
        item=approved['metrics']['destinos'][destination]
        st.metric('Error absoluto medio de validación',f'{item["estimado"]["MAE"]:,.0f} visitantes')
        st.caption('MAE: distancia absoluta promedio respecto a lo observado en octubre–diciembre de 2025 (3 meses). No mide el error de enero–febrero de 2026, cuyos observados comparables no están disponibles.')
        errors=pd.DataFrame({'Procedimiento':['Candidato','Último observado'],'MAE':[item['estimado']['MAE'],item['referencia']['MAE']]})
        chart(px.bar(errors,x='Procedimiento',y='MAE',color='Procedimiento'),'errores')
        st.warning('La escala se estimó con solo cuatro meses. La muestra de validación es pequeña y no garantiza precisión futura. No es una participación de mercado.')
elif not observed:
    st.info('Esta versión contiene estimaciones; aún no hay un conjunto de fuentes observadas disponible.')
elif section=='Movilidad y Tikal':
    st.subheader('¿Cómo cambia la movilidad de cada sitio?')
    chart(px.line(m,x='periodo',y=destination,markers=True,labels={destination:'Visitantes mensuales','periodo':'Mes'}),'movilidad')
    st.caption('Enero–febrero de 2026 están ausentes en la fuente; las líneas no deben interpretarse como observaciones de esos meses.')
    # Inserta huecos explícitos para que Plotly no dibuje una continuidad inventada.
    st.subheader('¿Cómo se distribuyen los boletos de Tikal?')
    d=t['tikal'];chart(px.bar(d,x='periodo',y=['nacionales','extranjeros','otros'],labels={'value':'Boletos','periodo':'Mes'}),'tikal')
    st.caption('Los boletos no identifican compradores únicos ni son equivalentes a visitantes de los otros sitios. Los ceros históricos requieren revisión de cobertura.')
elif section=='Conectividad aérea':
    st.subheader('¿Cómo cambia el tráfico de pasajeros?')
    a=t['aeropuerto'];chart(px.line(a,x='periodo',y='pasajeros',color='flujo',markers=True),'aeropuerto')
    st.caption('2023 reconstruido con aerolíneas; 2026 cubre enero–abril. Entrada y salida no equivalen a turistas únicos.')
    years=sorted(pd.to_datetime(t['aerolineas'].periodo).dt.year.unique())
    year=st.selectbox('Año aéreo',years,index=len(years)-1)
    flow=st.selectbox('Flujo de pasajeros',['Entrada','Salida'])
    a=t['aerolineas'];a=a.loc[pd.to_datetime(a.periodo).dt.year.eq(year)&a['Tipo de Flujo'].eq(flow)].groupby('Aerolínea',as_index=False).Pasajeros.sum()
    chart(px.bar(a,x='Aerolínea',y='Pasajeros'),'aerolineas')
    o=t['operadores'];o=o.loc[pd.to_datetime(o.periodo).dt.year.eq(year)].groupby(['operador_normalizado','Tipo de Operación'],as_index=False).Operaciones.sum()
    chart(px.bar(o,x='operador_normalizado',y='Operaciones',color='Tipo de Operación',barmode='group'),'operaciones')
    st.caption('Una operación es un movimiento de aeronave. No se suma con pasajeros.')
elif section=='Alojamiento':
    st.subheader('¿Cómo cambia la ocupación hotelera?')
    o=t['ocupacion'];chart(px.line(o,x='periodo',y='indice_ocupacion',markers=True),'ocupacion')
    st.caption('Fracción ocupada entre 0 y 1; cobertura 2023–2025. No representa número de visitantes.')
    c=t['capacidad'].copy();c['corte']=c.anio.astype(str)+' T'+c.trimestre.astype(str)
    measure=st.selectbox('Medida de capacidad',['habitaciones','plazas_cama','establecimientos'])
    chart(px.bar(c,x='corte',y=measure,color='tipo_alojamiento',barmode='group'),'capacidad')
    chart(px.bar(c,x='tipo_alojamiento',y=measure,color='corte',barmode='group'),'composicion_capacidad')
    st.caption('Cada barra corresponde a un corte. No son capacidades acumulables entre años.')

if os.environ.get('LAB_ADMIN')=='1':
    with st.expander('Administración local · restaurar versión'):
        versions=[]
        for folder in sorted((output/'versiones').glob('*')):
            try:read_version(output,folder.name,environment);versions.append(folder.name)
            except Exception:pass
        if versions:
            selected=st.selectbox('Versión aprobada a restaurar',versions)
            if st.button('Restaurar versión'):
                with store_lock(output):point_to(output,selected,environment)
                st.rerun()
        else:st.write('No hay versiones aprobadas para restaurar.')
