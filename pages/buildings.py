import pandas as pd
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from dash.dependencies import Input, Output

from variables import get_variable, set_variable
from utils.quilt import load_datasets
from . import page_callback, Page


INPUT_DATASETS = [
    'jyrjola/aluesarjat/z02um_rakennukset_lammitys',
]

# Datasets
buildings_by_heating_method = None


def prepare_buildings_dataset(df):
    df = df[df.Alue == get_variable('municipality_name')].drop(columns='Alue')
    col = df['Käyttötarkoitus ja kerrosluku']
    # Drop all the rows that are just sums of other rows
    sum_labels = ['Kaikki rakennukset', 'Asuinrakennukset yhteensä', 'Muut rakennukset yhteensä']
    df = df[~col.isin(sum_labels)]
    df = df[~((df['Lämmitystapa'] == 'Yhteensä') | (df['Lämmitysaine'] == 'Yhteensä'))]

    col_list = list(df.columns)
    col_list.remove('value')
    df = df.set_index(col_list)['value'].unstack('Yksikkö').reset_index()
    df.Vuosi = df.Vuosi.astype(int)
    df = df.set_index('Vuosi')
    df.columns.name = None

    return df


def prepare_input_datasets():
    global buildings_by_heating_method

    buildings_in = load_datasets(INPUT_DATASETS)
    buildings_by_heating_method = prepare_buildings_dataset(buildings_in)


def generate_buildings_forecast_graph(buildings_df):
    # col_name = 'Käyttötarkoitus ja kerrosluku'
    col_name = 'Lämmitysaine'
    df = buildings_df.reset_index().groupby(['Vuosi', col_name])['Kerrosala'].sum()
    df = df.reset_index().set_index(['Vuosi', col_name])
    df = df.unstack(col_name)
    df.columns = pd.Index([x[1] for x in df.columns.to_flat_index()])
    df /= 1000
    traces = []
    last_year = df.loc[[df.index.max()]]
    columns = last_year.stack().sort_values(ascending=False).index.get_level_values(1).values
    for building_type in columns:
        trace = go.Bar(x=df.index, y=df[building_type], name=building_type)
        traces.append(trace)

    layout = go.Layout(
        barmode='stack',
        yaxis=dict(
            title='1 000 m²',
            hoverformat='.3r',
            separatethousands=True,
        ),
        xaxis=dict(title='Vuosi'),
        title='Kerrosala lämmitysaineen mukaan'
    )
    return go.Figure(data=traces, layout=layout)


buildings_page_content = dbc.Container([
    html.H5('Asuinrakennusalan korjausprosentti'),
    html.Div([
        dcc.Slider(
            id='residential-buildings-slider',
            min=-20,
            max=20,
            step=5,
            value=0,
            marks={x: '%d %%' % x for x in range(-20, 20 + 1, 5)},
        ),
    ], style={'marginBottom': 25}),
    html.Div([
        html.P(children=[
            'Asuinrakennuskerrosalaa vuonna %s: ' % get_variable('target_year'),
            html.Strong(id='residential-building-area-target-year')
        ]),
    ]),
    dcc.Graph(
        id='buildings-graph',
    ),
])


@page_callback(
    [Output('buildings-graph', 'figure'), Output('residential-building-area-target-year', 'children')],
    [Input('residential-buildings-slider', 'value')])
def buildings_callback(value):
    df = buildings_by_heating_method
    fig = generate_buildings_forecast_graph(df)

    return fig, None


prepare_input_datasets()

page = Page('Rakennukset', buildings_page_content, [buildings_callback])
