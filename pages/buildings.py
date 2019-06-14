import pandas as pd
from matplotlib import cm
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from dash.dependencies import Input, Output

from variables import get_variable, set_variable
from utils.quilt import load_datasets
from calc.buildings import generate_building_floor_area_forecast
from . import page_callback, Page


def generate_buildings_forecast_graph(df):
    colors = [cm.colors.to_hex(x) for x in cm.Paired.colors]

    # Sort columns based on the amounts in the last measured year
    last_year = df.loc[df[~df.Forecast].index.max()]
    columns = list(last_year.sort_values(ascending=False).index.values)
    columns.remove('Forecast')

    traces = []
    for idx, building_type in enumerate(columns):
        trace = go.Bar(
            x=df.index,
            y=df[building_type] / 1000,  # convert to thousands
            name=building_type,
        )
        traces.append(trace)

    last_hist_year = df[~df.Forecast].index.max()
    forecast_divider = dict(
        type='line',
        x0=last_hist_year + 0.5,
        x1=last_hist_year + 0.5,
        xref='x',
        y0=0,
        y1=1,
        yref='paper',
        line=dict(dash='dot', color='grey')
    )

    layout = go.Layout(
        barmode='stack',
        yaxis=dict(
            title='1 000 kem²',
            hoverformat='.3r',
            separatethousands=True,
        ),
        xaxis=dict(title='Vuosi'),
        title='Kerrosala käyttötarkoituksen mukaan',
        shapes=[forecast_divider],
    )
    return go.Figure(data=traces, layout=layout)


buildings_page_content = dbc.Row([
    dbc.Col([
        dcc.Graph(
            id='buildings-graph',
        ),
    ])
])


def render_page():
    print('render_page()')
    df = generate_building_floor_area_forecast()
    fig = generate_buildings_forecast_graph(df)

    buildings_page_content['buildings-graph'].figure = fig
    return buildings_page_content


page = Page('Rakennukset', render_page)
