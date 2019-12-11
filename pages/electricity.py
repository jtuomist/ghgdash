import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

from variables import set_variable, get_variable
from calc.electricity import predict_electricity_consumption_emissions
from components.cards import GraphCard, ConnectedCardGrid
from components.graphs import PredictionGraph

from .base import Page


def render_page():
    grid = ConnectedCardGrid()

    per_capita_card = GraphCard(
        id='electricity-consumption-per-capita',
        slider=dict(
            min=-50,
            max=20,
            step=5,
            value=get_variable('electricity_consumption_per_capita_adjustment'),
            marks={x: '%d %%' % (x / 10) for x in range(-50, 20 + 1, 10)},
        )
    )
    grid.make_new_row()
    grid.add_card(per_capita_card)

    consumption_card = GraphCard(id='electricity-consumption')
    emission_factor_card = GraphCard(id='electricity-consumption-emission-factor')
    per_capita_card.connect_to(consumption_card)

    grid.make_new_row()
    grid.add_card(consumption_card)
    grid.add_card(emission_factor_card)

    emission_card = GraphCard(id='electricity-consumption-emissions')
    consumption_card.connect_to(emission_card)
    emission_factor_card.connect_to(emission_card)

    grid.make_new_row()
    grid.add_card(emission_card)

    return grid.render()


page = Page(
    id='electricity-consumption', name='Kulutussähkö', content=render_page, path='/kulutussahko',
    emission_sector=('ElectricityConsumption', None)
)


@page.callback(
    outputs=[
        Output('electricity-consumption-per-capita-graph', 'figure'),
        Output('electricity-consumption-graph', 'figure'),
        Output('electricity-consumption-emission-factor-graph', 'figure'),
        Output('electricity-consumption-emissions-graph', 'figure'),
    ],
    inputs=[Input('electricity-consumption-per-capita-slider', 'value')]
)
def electricity_consumption_callback(value):
    set_variable('electricity_consumption_per_capita_adjustment', value / 10)

    df = predict_electricity_consumption_emissions()

    graph = PredictionGraph(
        sector_name='ElectricityConsumption', title='Sähkönkulutus asukasta kohti',
        unit_name='kWh/as.'
    )
    graph.add_series(df=df, trace_name='Sähkönkulutus/as.', column_name='ElectricityConsumptionPerCapita')
    per_capita_fig = graph.get_figure()

    graph = PredictionGraph(
        sector_name='ElectricityConsumption', title='Kulutussähkön kulutus',
        unit_name='GWh',
    )
    graph.add_series(df=df, trace_name='Sähkönkulutus', column_name='ElectricityConsumption')
    consumption_fig = graph.get_figure()

    graph = PredictionGraph(
        sector_name='ElectricityConsumption', title='Sähköntuotannon päästökerroin',
        unit_name='g/kWh',
        smoothing=True,
    )
    graph.add_series(df=df, trace_name='Päästökerroin', column_name='EmissionFactor')
    factor_fig = graph.get_figure()
    print(factor_fig)

    graph = PredictionGraph(
        sector_name='ElectricityConsumption', title='Kulutussähkön päästöt',
        unit_name='kt (CO2e)', smoothing=True,
    )
    graph.add_series(df=df, trace_name='Päästöt', column_name='Emissions')
    emission_fig = graph.get_figure()

    return [per_capita_fig, consumption_fig, factor_fig, emission_fig]
