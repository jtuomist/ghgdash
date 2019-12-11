from dash_archer import DashArcherContainer, DashArcherElement
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go
from dash.dependencies import Input, Output
from babel.numbers import format_decimal

from calc.district_heating import predict_district_heating_emissions
from calc.district_heating_consumption import predict_district_heat_consumption
from variables import set_variable, get_variable
from components.stickybar import StickyBar
from components.graphs import make_layout, PredictionGraph
from components.cards import make_graph_card
from utils.colors import ARCHER_STROKE, GHG_MAIN_SECTOR_COLORS
from .base import Page


DISTRICT_HEATING_GOAL = 251

EXISTING_BUILDINGS_HIST_COLOR = GHG_MAIN_SECTOR_COLORS['BuildingHeating']
EXISTING_BUILDINGS_FORECAST_COLOR = '#ff6c38'
NEW_BUILDINGS_COLOR = '#ffb59b'


def draw_existing_building_unit_heat_factor_graph(df):
    graph = PredictionGraph(
        df=df, sector_name='BuildingHeating', column_name='ExistingBuildingHeatUsePerNetArea',
        unit_name='kWh/k-m²', trace_name='Ominaislämmönkulutus',
        title='Olemassaolevan rakennuskannan ominaislämmönkulutus',
        historical_color=EXISTING_BUILDINGS_HIST_COLOR,
        forecast_color=EXISTING_BUILDINGS_FORECAST_COLOR
    )
    return graph.get_figure()


def draw_new_building_unit_heat_factor_graph(df):
    graph = PredictionGraph(
        df=df, sector_name='BuildingHeating', column_name='NewBuildingHeatUsePerNetArea',
        unit_name='kWh/k-m²', trace_name='Ominaislämmönkulutus',
        title='Uuden rakennuskannan ominaislämmönkulutus',
        forecast_color=NEW_BUILDINGS_COLOR
    )
    return graph.get_figure()


def draw_heat_consumption(df):
    hist_df = df[~df.Forecast]
    t1h = go.Scatter(
        x=hist_df.index,
        y=hist_df.ExistingBuildingHeatUse,
        mode='none',
        fill='tozeroy',
        name='Vanhat rakennukset',
        hovertemplate='%{x}: %{y:.0f} GWh',
        fillcolor=EXISTING_BUILDINGS_HIST_COLOR,
        line=dict(
            color=EXISTING_BUILDINGS_HIST_COLOR,
            shape='spline',
        ),
    )

    forecast_df = df.loc[df.Forecast | (df.index == hist_df.index.max())]
    t1f = go.Scatter(
        x=forecast_df.index,
        y=forecast_df.ExistingBuildingHeatUse,
        mode='none',
        fill='tonexty',
        name='Vanhat rakennukset (enn.)',
        hovertemplate='%{x}: %{y:.0f} GWh',
        fillcolor=EXISTING_BUILDINGS_FORECAST_COLOR,
        line=dict(
            color=EXISTING_BUILDINGS_FORECAST_COLOR,
            shape='spline',
        ),
        stackgroup='one'
    )

    new_building_heat_use = forecast_df.NewBuildingHeatUse
    t2 = go.Scatter(
        x=new_building_heat_use.index,
        y=new_building_heat_use,
        mode='none',
        name='Uudet rakennukset',
        hovertemplate='%{x}: %{y:.0f} GWh',
        fillcolor=NEW_BUILDINGS_COLOR,
        line=dict(
            color=NEW_BUILDINGS_COLOR,
            shape='spline',
            smoothing=1,
        ),
        stackgroup='one'
    )
    layout = make_layout(
        yaxis=dict(
            title='GWh',
        ),
        title="Kaukolämmön kokonaiskulutus",
    )

    fig = go.Figure(data=[t1h, t1f, t2], layout=layout)
    return fig


def draw_district_heat_consumption_emissions(df):
    graph = PredictionGraph(
        df=df, sector_name='BuildingHeating', column_name='District heat consumption emissions',
        unit_name='kt', trace_name='Päästöt', title='Kaukolämmön kulutuksen päästöt',
        smoothing=True,
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
    rows = []

    existing_card = DashArcherElement([
        make_graph_card(
            card_id='district-heating-existing-building-unit-heat-factor',
            slider=dict(
                min=-60,
                max=20,
                step=5,
                value=get_variable('district_heating_existing_building_efficiency_change') * 10,
                marks={x: '%.1f %%' % (x / 10) for x in range(-60, 20 + 1, 10)},
            ),
            borders=dict(bottom=True),
        )
    ], id='district-heating-existing-building-unit-heat-factor-elem', relations=[{
        'targetId': 'district-heating-consumption-elem',
        'targetAnchor': 'top',
        'sourceAnchor': 'bottom',
    }])

    new_card = DashArcherElement([
        make_graph_card(
            card_id='district-heating-new-building-unit-heat-factor',
            slider=dict(
                min=-60,
                max=20,
                step=5,
                value=get_variable('district_heating_new_building_efficiency_change') * 10,
                marks={x: '%.1f %%' % (x / 10) for x in range(-60, 20 + 1, 10)},
            ),
            borders=dict(bottom=True),
        )
    ], id='district-heating-new-building-unit-heat-factor-elem', relations=[{
        'targetId': 'district-heating-consumption-elem',
        'targetAnchor': 'top',
        'sourceAnchor': 'bottom',
    }])

    rows.append(dbc.Row([dbc.Col(md=10, children=[
        dbc.Row([
            dbc.Col(existing_card, md=6),
            dbc.Col(new_card, md=6),
        ])
    ])]))

    consumption_card = DashArcherElement([
        dbc.Card(dbc.CardBody([
            dcc.Graph(id='district-heating-consumption-graph'),
            html.Div(id='district-heating-unit-emissions-card'),
        ]), className="mb-4 card-border-top card-border-bottom")
    ], id='district-heating-consumption-elem', relations=[{
        'sourceAnchor': 'bottom',
        'targetId': 'district-heating-consumption-emissions-elem',
        'targetAnchor': 'top',
    }])
    rows.append(dbc.Row([
        dbc.Col(consumption_card, md=10),
    ]))

    emissions_card = DashArcherElement([
        dbc.Card(dbc.CardBody([
            dcc.Graph(id='district-heating-consumption-emissions'),
        ]), className="mb-4 card-border-top"),
    ], id='district-heating-consumption-emissions-elem')
    rows.append(dbc.Row([
        dbc.Col(md=10, children=emissions_card),
    ], className="page-content-wrapper"))
    rows.append(html.Div(id='district-heating-sticky-page-summary-container'))

    return DashArcherContainer(
        [html.Div(rows)],
        strokeColor=ARCHER_STROKE['default']['color'],
        strokeWidth=ARCHER_STROKE['default']['width'],
        arrowLength=0.001,
        arrowThickness=0.001,
    )


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
    Output('district-heating-consumption-emissions', 'figure'),
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
