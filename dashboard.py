import pandas as pd
import plotly.express as px  # (version 4.7.0)
import plotly.graph_objects as go

import dash  # (version 1.12.0) pip install dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

import geopandas
import numpy as np
from shapely.geometry import Point

import datetime
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patheffects as mpe

import base64

from os.path import join
ruta = 'C:\Diplomado_IA_PUCP\Visualizacion_de_datos\proyecto'

app = dash.Dash(__name__,external_stylesheets=[dbc.themes.BOOTSTRAP])

# ---------- Import and clean data (importing csv into pandas)
# df = pd.read_csv("intro_bees.csv")
region_geojson = geopandas.read_file(join(ruta,'peru-geojson-master\peru_departamental_simple.geojson'))
region_geojson.head()

sinadef = pd.read_csv(join(ruta,'fallecidos_sinadef.csv'),sep=';',index_col=0,skiprows=2,encoding='latin1')
sinadef_keep = sinadef[['SEXO','EDAD','PAIS DOMICILIO','DEPARTAMENTO DOMICILIO','PROVINCIA DOMICILIO','FECHA', 'AÑO', 'MES','MUERTE VIOLENTA']]
sinadef_covid = sinadef_keep[(sinadef_keep['AÑO']*100+sinadef_keep['MES']>=202003) & (sinadef_keep['MUERTE VIOLENTA']=='SIN REGISTRO') & (sinadef_keep['FECHA']<='2021-05-20')]
sinadef_covid_total = sinadef_covid['DEPARTAMENTO DOMICILIO'].value_counts(dropna=False).to_frame().reset_index().rename(columns={'index': 'departamento','DEPARTAMENTO DOMICILIO':'Muertes_total'})

region_geojson_total = pd.merge(region_geojson,sinadef_covid_total,how='left',left_on='NOMBDEP', right_on='departamento')
##LEYENDO LA POBLACION DEL CENSO 2017 PROYECTADA AL 2020
region_poblacion = pd.read_csv(join(ruta,'poblacion_censo_2017_proy_2020.csv'),sep=';')

region_geojson_total_2 = pd.merge(region_geojson_total,region_poblacion,how='left',left_on='NOMBDEP', right_on='Departamento')
region_geojson_total_2['total_muerte_x_1000'] = 100000*region_geojson_total_2['Muertes_total'] / region_geojson_total_2['Poblacion']
#print(region_geojson_total_2.head())
##MACROREGIONES
macroregiones = pd.read_csv(join(ruta,'macroregiones.csv'),sep=';')
region_geojson_total_3 = pd.merge(region_geojson_total_2,macroregiones,how='left',left_on='NOMBDEP', right_on='Departamento')
print(region_geojson_total_3.head())


##AGREGANDO INFO DE LA ULTIMA SEMANA
sinadef_covid_last_week = sinadef_covid[sinadef_covid['FECHA']>='2021-05-14']
sinadef_covid_last_week_resume = sinadef_covid_last_week['DEPARTAMENTO DOMICILIO'].value_counts(dropna=False).to_frame().reset_index().rename(columns={'index': 'departamento','DEPARTAMENTO DOMICILIO':'Muertes_total_week'})
region_geojson_total_4 = pd.merge(region_geojson_total_3,sinadef_covid_last_week_resume,how='left',left_on='NOMBDEP', right_on='departamento')
region_geojson_total_4['total_muerte_week_x_1000'] = 100000*region_geojson_total_4['Muertes_total_week'] / region_geojson_total_4['Poblacion']
#region_geojson_total_3

##PARA LA GRAFICA LINEAL
sinadef_timeline = pd.read_csv(join(ruta,'sinadef_timeline.csv'),sep=',',encoding='latin1')
sinadef_timeline_2 = pd.merge(sinadef_timeline,macroregiones,how='left',left_on='DEPARTAMENTO', right_on='Departamento')
print(sinadef_timeline_2.head())
# ------------------------------------------------------------------------------
##ZONA DE ANALISIS DE LAS OCUPACIONES DE CAMAS UCI Y HOSPITALIZACIONES
camas_today_resume = pd.read_csv(join(ruta,'camas_today_resume.csv'),sep=',',encoding='latin1')
region_geojson_camas = pd.merge(region_geojson,camas_today_resume,how='left',left_on='NOMBDEP', right_on='REGION')

region_geojson_camas_2 = pd.merge(region_geojson_camas,macroregiones,how='left',left_on='NOMBDEP', right_on='Departamento')
print(region_geojson_camas_2.head())
#-------------------------------------------------------------------------------
##VACUNACIONES
poblacion_etario_vacunas = pd.read_csv(join(ruta,'poblacion_etario_vacunas.csv'),sep=',',encoding='latin1')
poblacion_etario_vacunas.sort_values('grupo_etario',inplace=True)
fig_vacuna_etario = px.bar(poblacion_etario_vacunas, x="grupo_etario",
                            y=["ambas_dosis", "solo_dosis_1", "ninguna_dosis"], title="Vacunacion por grupo etario",
                            labels={
                                "grupo_etario" : "Rango de edad",
                                "y":"Poblacion"
                            })

vacunas_timeline = pd.read_csv(join(ruta,'vacunas_timeline.csv'),sep=',',encoding='latin1')
vacunas_timeline['DOSIS'] = vacunas_timeline['DOSIS'].apply(str)
fig_vacunas_timeline = px.bar(vacunas_timeline, x="FECHA_VACUNACION_dt", y="UUID", color="DOSIS",
                            title="Aplicacion de Vacunas por Dosis",
                            labels={
                                "FECHA_VACUNACION_dt": "Fecha de la vacunacion",
                                "UUID": "Dosis aplicadas"
                            })
#-------------------------------------------------------------------------------
##REPRODUCTION RATE
owid = pd.read_csv(join(ruta,'owid-covid-data.csv'),sep=',',encoding='latin1',index_col=0)
owid['date'] = pd.to_datetime(owid['date'])
#Lista de países
lista_paises = owid['location'].unique().tolist()
lista_paises.sort()

#-------------------------------------------------------------------------------
# App layout
app.layout = html.Div([
    ##El titulo
    dbc.Row(dbc.Col(html.H1("Visualizacion de Datos COVID 19 en el Peru"),
                        width={'size': 8, 'offset': 2},
                    )
            ),
    dbc.Row(dbc.Col(html.H2("Tasa de Reproduccion - R"),
                        width={'size': 6, 'offset': 3},
                    ),
            ),
    #El Dropdown
    dbc.Row(dbc.Col(html.P("Seleccion país(es) para comparar"),lg={'size': 2,  "offset": 1})),
    dbc.Row(
        [dbc.Col(dcc.Dropdown(id="pais_select",
                        placeholder='Seleccione país',
                        options=[{"label": i, "value": i} for i in lista_paises],
                        multi=True,
                        value=['Peru']),
            lg={'size': 2,  "offset": 1}),
        dbc.Col(dcc.Graph(id='time_serie_owid', figure={}),
            width=12, lg={'size': 8,  "offset": 0}
        )
        ]),
    dbc.Row(dbc.Col(html.H2("Fallecidos - Fuente SINADEF"),
                        width={'size': 6, 'offset': 3},
                    ),
            ),
    #El Dropdown
    dbc.Row(dbc.Col(dcc.Dropdown(id="slct_year",
                 options=[
                     {"label": "Peru", "value": "Peru"},
                     {"label": "Macro Region Norte", "value": "Norte"},
                     {"label": "Macro Region Sur", "value": "Sur"},
                     {"label": "Macro Region Oriente", "value": "Oriente"},
                     {"label": "Macro Region Centro", "value": "Centro"},
                     {"label": "Region Lima", "value": "Lima"}],
                 multi=False,
                 value="Peru",
                 style={'width': "40%"}
                 ),width={'size': 12})
            ),
    ##Los graficos
     dbc.Row(
            dbc.Col(dcc.Graph(id='timeline', figure={}),
                width=12, lg={'size': 10,  "offset": 1}
            )
      ),
    dbc.Row(
          [
              dbc.Col(dcc.Graph(id='fallecido_total', figure={}),
                      width=8, lg={'size': 6,  "offset": 0, 'order': 'first'}
                      ),
              dbc.Col(dcc.Graph(id='fallecido_last_week', figure={}),
                      width=4, lg={'size': 6,  "offset": 0, 'order': 'last'}
                      ),
          ]
      ),
    
    dbc.Row(dbc.Col(html.H2("Situacion Ocupacional Hospitalaria - Fuente SUSALUD"),
                        width={'size': 8, 'offset': 2},
                    ),
            ),
    #El Dropdown 2
    dbc.Row(dbc.Col(dcc.Dropdown(id="slct_year2",
                 options=[
                     {"label": "Peru", "value": "Peru"},
                     {"label": "Macro Region Norte", "value": "Norte"},
                     {"label": "Macro Region Sur", "value": "Sur"},
                     {"label": "Macro Region Oriente", "value": "Oriente"},
                     {"label": "Macro Region Centro", "value": "Centro"},
                     {"label": "Region Lima", "value": "Lima"}],
                 multi=False,
                 value="Peru",
                 style={'width': "40%"}
                 ),width={'size': 12})
            ),
    dbc.Row(
          [
              dbc.Col(dcc.Graph(id='ocupacion_UCI', figure={}),
                      width=8, lg={'size': 6,  "offset": 0, 'order': 'first'}
                      ),
            dbc.Col(dcc.Graph(id='gauge_ocupacion_UCI', figure={}),
                    lg={'size': 4,  "offset": 1, 'order': 'last'}
                      ),
          ]
      ),
    dbc.Row(
          [
            dbc.Col(dcc.Graph(id='ocupacion_HOSP', figure={}),
                      width=4, lg={'size': 6,  "offset": 0, 'order': 'first'}
                      ),
            dbc.Col(dcc.Graph(id='gauge_ocupacion_HOSP', figure={}),
                    lg={'size': 4,  "offset": 1, 'order': 'last'}
                      ),
          ]
      ),
    dbc.Row(dbc.Col(html.H2("Vacunacion"),
                        width={'size': 4, 'offset': 4},
                    ),
            ),
    dbc.Row(
          [
            dbc.Col(dcc.Graph(figure=fig_vacunas_timeline),width=8),
            dbc.Col(dcc.Graph(figure=fig_vacuna_etario),width=4)
          ]
      ),
])


# ------------------------------------------------------------------------------
# Connect the Plotly graphs with Dash Components
@app.callback(
    [Output(component_id='fallecido_total', component_property='figure'),
     Output(component_id='fallecido_last_week', component_property='figure'),
     Output(component_id='timeline', component_property='figure')],
    [Input(component_id='slct_year', component_property='value')]
)
def update_graph(option_slctd):
    print(option_slctd)
    print(type(option_slctd))
    ##FILTRADO DE LA DATA##
    dff = region_geojson_total_4.copy()
    dff_line = sinadef_timeline_2.copy()
    if(option_slctd!="Peru" and option_slctd!=None):
      dff = dff[dff["MacroRegion"] == option_slctd]
      dff_line = dff_line[dff_line["MacroRegion"] == option_slctd]
    #MUERTES HASTA LA FECHA
    dff = dff.set_index("NOMBDEP")
    fig_total = px.choropleth(dff,
                   geojson=dff.geometry,
                   locations=dff.index,
                   color="total_muerte_x_1000",
                   projection="mercator",
                   color_continuous_scale=[(0, "white"), (0.5, "yellow"), (1, "red")],
                   range_color=(200, 1200),
                   labels={'total_muerte_x_1000':'Mortalidad por 100 mil hab.'})
    fig_total.update_geos(fitbounds="locations", visible=False)

    fig_total.update_layout(
         title_text="Exceso de Fallecidos desde la aparicion del COVID en el Peru (Marzo 2020)"
     )
    ##MUERTES DE LA ULTIMA SEMANA
    fig_week = px.choropleth(dff,
              geojson=dff.geometry,
              locations=dff.index,
              color="total_muerte_week_x_1000",
              projection="mercator",
              color_continuous_scale=[(0, "white"), (0.5, "yellow"), (1, "red")],
              range_color=(4,25),
              labels={'total_muerte_week_x_1000':'Mortalidad por 100 mil hab.'})
    fig_week.update_geos(fitbounds="locations", visible=False)

    fig_week.update_layout(
         title_text="Exceso de Fallecidos en la ultima semana (14/05/2021 - 20/05/2021)"
     )
    ##TIMELINE DE MUERTES
    dff_line_2 = dff_line[['FECHA','tmp']].groupby(['FECHA']).sum().reset_index().sort_values(by=['FECHA'])
    dff_line_2['avg_7'] = dff_line_2.tmp.rolling(7).mean()
    
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=dff_line_2['FECHA'], y=dff_line_2['tmp'],
                        mode='lines',
                        name='N° excedido de fallecidos diarios',
                        line = dict(color='red', width=0.25, dash='dash'),
                        hoverinfo='none'
                        ))
    fig_line.add_trace(go.Scatter(x=dff_line_2['FECHA'], y=dff_line_2['avg_7'],
                        mode='lines',
                        name='N° excedido de fallecidos diarios (media movil)',
                        line = dict(color='red', width=4)))

    
    fig_line.update_layout(legend=dict(
        yanchor="top",
        y=1,
        xanchor="left",
        x=0
    ))

    return fig_total,fig_week,fig_line

##Probando otro callback
@app.callback(
    [Output(component_id='ocupacion_UCI', component_property='figure'),
    Output(component_id='gauge_ocupacion_UCI', component_property='figure'),
    Output(component_id='gauge_ocupacion_HOSP', component_property='figure'),
    Output(component_id='ocupacion_HOSP', component_property='figure')],
    [Input(component_id='slct_year2', component_property='value')]
)
def update_graph2(option_slctd):
    print(option_slctd)
    print(type(option_slctd))
    ##FILTRADO DE LA DATA##
    dff = region_geojson_camas_2.copy()
    if(option_slctd!="Peru" and option_slctd!=None):
      dff = dff[dff["MacroRegion"] == option_slctd]
    
    #OCUPACION UCI
    dff = dff.set_index("NOMBDEP")
    fig_UCI = px.choropleth(dff,
                   geojson=dff.geometry,
                   locations=dff.index,
                   color="pct_uso_UCI",
                   projection="mercator",
                   color_continuous_scale=[(0, "white"), (0.5, "yellow"), (1, "red")],
                   range_color=(0, 1),
                   labels={'pct_uso_UCI':'Pct uso camas UCI'})
    fig_UCI.update_geos(fitbounds="locations", visible=False)

    fig_UCI.update_layout(
         title_text="Utilizacion de camas UCI por region"
     )
    ##MUERTES DE LA ULTIMA SEMANA
    fig_hosp = px.choropleth(dff,
              geojson=dff.geometry,
              locations=dff.index,
              color="pct_uso_HOSP",
              projection="mercator",
              color_continuous_scale=[(0, "white"), (0.5, "yellow"), (1, "red")],
              range_color=(0,1),
              labels={'pct_uso_HOSP':'Pct uso cama HOSP'})
    fig_hosp.update_geos(fitbounds="locations", visible=False)

    fig_hosp.update_layout(
         title_text="Utilizacion de camas de Hospitalizaciones por region"
     )

    #Velocimetros
    dff['TOTAL']=1
    dff = dff.groupby('TOTAL').sum().reset_index()

    ocupado_uci = dff['ZC_UCI_ADUL_CAM_TOT_OCUP'][0]
    total_operativo_uci = dff['ZC_UCI_ADUL_CAM_TOT_OPER'][0]

    ocupado_hosp = dff['ZC_HOSP_ADUL_CAM_TOT_OCUP'][0]
    total_operativo_hosp = dff['ZC_HOSP_ADUL_CAM_TOT_OPER'][0]

    fig_gauge_uci = go.Figure(go.Indicator(
            domain = {'x': [0, 1], 'y': [0, 1]},
            value = ocupado_uci,
            mode = "gauge+number+delta",
            title = {'text': "Capacidad Camas UCI"},
            delta = {'reference': total_operativo_uci},
            gauge = {'axis': {'range': [None, total_operativo_uci]}}
            ))

    fig_gauge_hosp = go.Figure(go.Indicator(
            domain = {'x': [0, 1], 'y': [0, 1]},
            value = ocupado_hosp,
            mode = "gauge+number+delta",
            title = {'text': "Capacidad Camas Hospitalizaciones"},
            delta = {'reference': total_operativo_hosp},
            gauge = {'axis': {'range': [None, total_operativo_hosp]}}
            ))

    return fig_UCI,fig_gauge_uci,fig_gauge_hosp,fig_hosp

@app.callback(
    Output("time_serie_owid", "figure"),
    [Input('pais_select','value')]
)
def update_owid(paises_selected):
    if(len(paises_selected)==0):
        paises_selected.append('Peru')
    owid_filter = owid[owid['location'].isin(paises_selected)]
    fig = px.line(owid_filter,
                  x="date", 
                  y='reproduction_rate',
                  color='location',
                  labels={'reproduction_rate':'Tasa de Reproduccion - R','date':'fecha'}
                  )
    return fig
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    app.run_server(debug=True)

    
# https://youtu.be/hSPmj7mK6ng