import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

from variables import set_variable, get_variable
from calc.electricity import predict_electricity_consumption_emissions
from components.cards import GraphCard, ConnectedCardGrid
from components.graphs import PredictionFigure
from components.card_description import CardDescription
from components.stickybar import StickyBar

from .base import Page


def render_page():
    grid = ConnectedCardGrid()

    per_capita_card = GraphCard(
        id='electricity-consumption-per-capita',
        slider=dict(
            min=-50,
            max=20,
            step=5,
            value=int(get_variable('electricity_consumption_per_capita_adjustment') * 10),
            marks={x: '%d %%' % (x / 10) for x in range(-50, 20 + 1, 10)},
        )
    )
    solar_card = GraphCard(
        id='electricity-consumption-solar-production',
        link_to_page=('ElectricityConsumption', 'SolarProduction')
    )
    grid.make_new_row()
    grid.add_card(per_capita_card)
    grid.add_card(solar_card)

    consumption_card = GraphCard(id='electricity-consumption')
    emission_factor_card = GraphCard(id='electricity-consumption-emission-factor')
    per_capita_card.connect_to(consumption_card)
    solar_card.connect_to(consumption_card)

    grid.make_new_row()
    grid.add_card(consumption_card)
    grid.add_card(emission_factor_card)

    emission_card = GraphCard(id='electricity-consumption-emissions')
    consumption_card.connect_to(emission_card)
    emission_factor_card.connect_to(emission_card)

    grid.make_new_row()
    grid.add_card(emission_card)

    return html.Div(children=[grid.render(), html.Div(id='electricity-consumption-summary-bar')])


page = Page(
    id='electricity-consumption', name='Kulutussähkö', content=render_page, path='/kulutussahko',
    emission_sector='ElectricityConsumption'
)


@page.callback(
    outputs=[
        Output('electricity-consumption-per-capita-graph', 'figure'),
        Output('electricity-consumption-per-capita-description', 'children'),
        Output('electricity-consumption-solar-production-graph', 'figure'),
        Output('electricity-consumption-solar-production-description', 'children'),
        Output('electricity-consumption-graph', 'figure'),
        Output('electricity-consumption-emission-factor-graph', 'figure'),
        Output('electricity-consumption-emissions-graph', 'figure'),
        Output('electricity-consumption-summary-bar', 'children'),
    ],
    inputs=[Input('electricity-consumption-per-capita-slider', 'value')]
)
def electricity_consumption_callback(value):
    set_variable('electricity_consumption_per_capita_adjustment', value / 10)

    df = predict_electricity_consumption_emissions()

    graph = PredictionFigure(
        sector_name='ElectricityConsumption', title='Sähkönkulutus asukasta kohti',
        unit_name='kWh/as.'
    )
    graph.add_series(df=df, trace_name='Sähkönkulutus/as.', column_name='ElectricityConsumptionPerCapita')
    per_capita_fig = graph.get_figure()

    graph = PredictionFigure(
        sector_name='ElectricityConsumption', title='Kulutussähkön kulutus',
        unit_name='GWh', fill=True,
    )
    graph.add_series(df=df, trace_name='Sähkönkulutus', column_name='NetConsumption')
    consumption_fig = graph.get_figure()

    graph = PredictionFigure(
        sector_name='ElectricityConsumption', title='Sähköntuotannon päästökerroin',
        unit_name='g/kWh',
        smoothing=True,
    )
    graph.add_series(df=df, trace_name='Päästökerroin', column_name='EmissionFactor')
    factor_fig = graph.get_figure()

    graph = PredictionFigure(
        sector_name='ElectricityConsumption', title='Kulutussähkön päästöt',
        unit_name='kt', smoothing=True, fill=True,
    )
    graph.add_series(df=df, trace_name='Päästöt', column_name='Emissions')
    emission_fig = graph.get_figure()

    graph = PredictionFigure(
        sector_name='ElectricityConsumption', title='Paikallinen aurinkosähkötuotanto',
        unit_name='GWh', smoothing=True, fill=True,
    )
    graph.add_series(df=df, trace_name='Tuotanto', column_name='SolarProduction')
    solar_fig = graph.get_figure()

    first_forecast = df[df.Forecast].iloc[0]
    last_forecast = df[df.Forecast].iloc[-1]
    last_history = df[~df.Forecast].iloc[-1]
    last_history_year = df[~df.Forecast].index.max()

    cd = CardDescription()
    cd.set_values(
        per_resident_adj=get_variable('electricity_consumption_per_capita_adjustment'),
        per_resident_change=((last_forecast.ElectricityConsumption / last_history.ElectricityConsumption) - 1) * 100,
        last_history_year=last_history.name,
        solar_production_target=last_forecast.SolarProduction,
        solar_production_hist=last_history.SolarProduction,
    )
    per_resident_desc = cd.render("""
        Skenaariossa asukaskohtainen sähkönkulutus pienenee {per_resident_adj:noround} % vuodessa.
        Vuonna {target_year} asukaskohtainen kulutus on muuttunut {per_resident_change} % nykyhetkestä.
    """)
    solar_desc = cd.render("""
        Vuonna {target_year} {municipality_locative} sijaitsevilla aurinkopaneeleilla
        tuotetaan {solar_production_target} GWh vuodessa.
    """)

    bar = StickyBar(
        label='Kulutussähkön päästöt',
        value=last_forecast.NetEmissions,
        unit='kt',
        current_page=page
    )

    return [
        per_capita_fig, dbc.Col(per_resident_desc, style=dict(minHeight='6rem')),
        solar_fig, dbc.Col(solar_desc, style=dict(minHeight='6rem')),
        consumption_fig, factor_fig, emission_fig, bar.render()
    ]
