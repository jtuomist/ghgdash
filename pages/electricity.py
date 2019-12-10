import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from dash.dependencies import Input, Output

from variables import set_variable, get_variable
from calc.electricity import generate_electricity_consumption_forecast
from components.cards import make_graph_card
from components.graphs import make_layout
from utils.colors import GHG_MAIN_SECTOR_COLORS
from utils.data import find_consecutive_start

from .base import Page


def generate_electricity_consumption_forecast_graph(el_df):
    start_year = find_consecutive_start(el_df.index)

    hist_df = el_df.loc[~el_df.Forecast & (el_df.index >= start_year)]
    hist = go.Scatter(
        x=hist_df.index,
        y=hist_df.ElectricityConsumption,
        mode='lines',
        name='Sähkönkulutus',
        hovertemplate='%{x}: %{y} GWh',
        line=dict(
            color=GHG_MAIN_SECTOR_COLORS['ElectricityConsumption'],
        )
    )

    forecast_df = el_df.query('Forecast')
    forecast = go.Scatter(
        x=forecast_df.index,
        y=forecast_df.ElectricityConsumption,
        mode='lines',
        name='Sähkönkulutus (enn.)',
        hovertemplate='%{x}: %{y} GWh',
        line=dict(
            color=GHG_MAIN_SECTOR_COLORS['ElectricityConsumption'],
            dash='dash'
        )
    )
    layout = make_layout(
        title='Kulutussähkön kulutus',
        yaxis=dict(
            title='GWh'
        ),
    )

    fig = go.Figure(data=[hist, forecast], layout=layout)
    return fig


def render_page():
    card = make_graph_card(
        card_id='electricity-consumption',
        slider=dict(
            min=-50,
            max=20,
            step=5,
            value=get_variable('electricity_consumption_per_capita_adjustment'),
            marks={x: '%d %%' % (x / 10) for x in range(-50, 20 + 1, 10)},
        )
    )
    rows = dbc.Row(dbc.Col(card, md=8))
    return rows


page = Page(
    id='electricity-consumption', name='Kulutussähkö', content=render_page, path='/kulutussahko',
    emission_sector=('ElectricityConsumption', '')
)


@page.callback(
    outputs=[Output('electricity-consumption-graph', 'figure')],
    inputs=[Input('electricity-consumption-slider', 'value')]
)
def electricity_consumption_callback(value):
    set_variable('electricity_consumption_per_capita_adjustment', value / 10)

    df = generate_electricity_consumption_forecast()
    fig = generate_electricity_consumption_forecast_graph(df)

    return [fig]
