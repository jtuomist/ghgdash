import dash_html_components as html
import dash_bootstrap_components as dbc
import numpy as np
from dash.dependencies import Input, Output
from babel.numbers import format_decimal

from calc.district_heating import predict_district_heating_emissions
from calc.district_heating_consumption import predict_district_heat_consumption
from variables import set_variable, get_variable
from components.stickybar import StickyBar
from components.graphs import PredictionGraph
from components.cards import GraphCard, ConnectedCardGrid
from .base import Page


DISTRICT_HEATING_GOAL = 251


def draw_existing_building_unit_heat_factor_graph(df):
    graph = PredictionGraph(
        sector_name='BuildingHeating',
        unit_name='kWh/k-m²',
        title='Olemassaolevan rakennuskannan ominaislämmönkulutus',
    )
    graph.add_series(
        df=df, column_name='ExistingBuildingHeatUsePerNetArea', trace_name='Ominaislämmönkulutus',
    )
    return graph.get_figure()


def draw_new_building_unit_heat_factor_graph(df):
    graph = PredictionGraph(
        sector_name='BuildingHeating',
        unit_name='kWh/k-m²',
        title='Uuden rakennuskannan ominaislämmönkulutus',
    )
    graph.add_series(
        df=df, column_name='NewBuildingHeatUsePerNetArea', trace_name='Ominaislämmönkulutus',
        luminance_change=0.2
    )
    return graph.get_figure()


def draw_heat_consumption(df):
    df.loc[~df.Forecast, 'NewBuildingHeatUse'] = np.nan
    graph = PredictionGraph(
        title='Kaukolämmön kokonaiskulutus',
        unit_name='GWh',
        sector_name='BuildingHeating',
        smoothing=True,
        stacked=True,
        fill=True,
    )
    graph.add_series(
        df=df, column_name='ExistingBuildingHeatUse', trace_name='Vanhat rakennukset',
    )
    graph.add_series(
        df=df, column_name='NewBuildingHeatUse', trace_name='Uudet rakennukset',
        luminance_change=0.2
    )

    return graph.get_figure()


def draw_district_heat_consumption_emissions(df):
    graph = PredictionGraph(
        sector_name='BuildingHeating',
        unit_name='kt', title='Kaukolämmön kulutuksen päästöt',
        smoothing=True, allow_nonconsecutive_years=True
    )
    graph.add_series(
        df=df, column_name='District heat consumption emissions', trace_name='Päästöt'
    )
    return graph.get_figure()


def make_unit_emissions_card(df):
    last_emission_factor = df['Emission factor'].iloc[-1]
    last_year = df.index.max()

    return dbc.Card([
        html.A(dbc.CardBody([
            html.H4('Kaukolämmön päästökerroin', className='card-title'),
            html.Div([
                html.Span(
                    '%s g (CO₂e) / kWh' % (format_decimal(last_emission_factor, format='@@@', locale='fi_FI')),
                    className='summary-card__value'
                ),
                html.Span(' (%s)' % last_year, className='summary-card__year')
            ])
        ]), href='/kaukolammon-tuotanto')
    ], className='summary-card')


def make_bottom_bar(df):
    s = df['District heat consumption emissions']
    last_emissions = s.iloc[-1]
    target_emissions = DISTRICT_HEATING_GOAL

    bar = StickyBar(
        label="Kaukolämmön kulutuksen päästöt",
        value=last_emissions,
        goal=target_emissions,
        unit='kt (CO₂e.)',
        current_page=page
    )
    return bar.render()


def generate_page():
    grid = ConnectedCardGrid()

    existing_card = GraphCard(
        id='district-heating-existing-building-unit-heat-factor',
        slider=dict(
            min=-60,
            max=20,
            step=5,
            value=get_variable('district_heating_existing_building_efficiency_change') * 10,
            marks={x: '%.1f %%' % (x / 10) for x in range(-60, 20 + 1, 10)},
        )
    )
    new_card = GraphCard(
        id='district-heating-new-building-unit-heat-factor',
        slider=dict(
            min=-60,
            max=20,
            step=5,
            value=get_variable('district_heating_new_building_efficiency_change') * 10,
            marks={x: '%.1f %%' % (x / 10) for x in range(-60, 20 + 1, 10)},
        ),
    )
    row = grid.make_new_row()
    row.add_card(existing_card)
    row.add_card(new_card)

    consumption_card = GraphCard(
        id='district-heating-consumption',
        extra_content=html.Div(id='district-heating-unit-emissions-card')
    )
    existing_card.connect_to(consumption_card)
    new_card.connect_to(consumption_card)
    row = grid.make_new_row()
    row.add_card(consumption_card)

    emissions_card = GraphCard(id='district-heating-consumption-emissions')
    consumption_card.connect_to(emissions_card)
    row = grid.make_new_row()
    row.add_card(emissions_card)

    return html.Div([
        grid.render(),
        html.Div(id='district-heating-sticky-page-summary-container')
    ])


page = Page(
    id='district-heating',
    name='Kaukolämmön kulutus',
    content=generate_page,
    path='/kaukolampo',
    emission_sector=('BuildingHeating', 'DistrictHeat')
)


@page.callback(inputs=[
    Input('district-heating-existing-building-unit-heat-factor-slider', 'value'),
    Input('district-heating-new-building-unit-heat-factor-slider', 'value'),
], outputs=[
    Output('district-heating-existing-building-unit-heat-factor-graph', 'figure'),
    Output('district-heating-new-building-unit-heat-factor-graph', 'figure'),
    Output('district-heating-consumption-graph', 'figure'),
    Output('district-heating-unit-emissions-card', 'children'),
    Output('district-heating-consumption-emissions-graph', 'figure'),
    Output('district-heating-sticky-page-summary-container', 'children'),
])
def district_heating_consumption_callback(existing_building_perc, new_building_perc):
    set_variable('district_heating_existing_building_efficiency_change', existing_building_perc / 10)
    set_variable('district_heating_new_building_efficiency_change', new_building_perc / 10)

    df = predict_district_heat_consumption()
    fig1 = draw_existing_building_unit_heat_factor_graph(df)
    fig2 = draw_new_building_unit_heat_factor_graph(df)
    fig3 = draw_heat_consumption(df)

    df = predict_district_heating_emissions()
    unit_emissions_card = make_unit_emissions_card(df)
    fig4 = draw_district_heat_consumption_emissions(df)
    sticky = make_bottom_bar(df)

    return [fig1, fig2, fig3, unit_emissions_card, fig4, sticky]
