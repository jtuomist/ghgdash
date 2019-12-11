import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

from variables import set_variable, get_variable
from calc.electricity import predict_electricity_consumption_emissions
from components.cards import make_graph_card
from components.graphs import PredictionGraph

from .base import Page


def render_page():
    rows = []

    card = make_graph_card(
        card_id='electricity-consumption-per-capita',
        slider=dict(
            min=-50,
            max=20,
            step=5,
            value=get_variable('electricity_consumption_per_capita_adjustment'),
            marks={x: '%d %%' % (x / 10) for x in range(-50, 20 + 1, 10)},
        )
    )
    rows.append(dbc.Row(dbc.Col(card, md=8)))

    card = make_graph_card(card_id='electricity-consumption')
    rows.append(dbc.Row(dbc.Col(card, md=8)))

    card = make_graph_card(card_id='electricity-consumption-emissions')
    rows.append(dbc.Row(dbc.Col(card, md=8)))

    return html.Div(rows)


page = Page(
    id='electricity-consumption', name='Kulutussähkö', content=render_page, path='/kulutussahko',
    emission_sector=('ElectricityConsumption', None)
)


@page.callback(
    outputs=[
        Output('electricity-consumption-per-capita-graph', 'figure'),
        Output('electricity-consumption-graph', 'figure'),
        Output('electricity-consumption-emissions-graph', 'figure'),
    ],
    inputs=[Input('electricity-consumption-per-capita-slider', 'value')]
)
def electricity_consumption_callback(value):
    set_variable('electricity_consumption_per_capita_adjustment', value / 10)

    df = predict_electricity_consumption_emissions()

    graph = PredictionGraph(
        df, sector_name='ElectricityConsumption', title='Sähkönkulutus asukasta kohti',
        trace_name='Sähkönkulutus/as.', unit_name='kWh/as.', column_name='ElectricityConsumptionPerCapita'
    )
    fig1 = graph.get_figure()

    graph = PredictionGraph(
        df, sector_name='ElectricityConsumption', title='Kulutussähkön kulutus',
        trace_name='Sähkönkulutus', unit_name='GWh', column_name='ElectricityConsumption'
    )
    fig2 = graph.get_figure()

    graph = PredictionGraph(
        df, sector_name='ElectricityConsumption', title='Kulutussähkön päästöt',
        trace_name='Päästöt', unit_name='kt (CO2e)', column_name='Emissions',
        smoothing=True,
    )
    fig3 = graph.get_figure()

    return [fig1, fig2, fig3]
