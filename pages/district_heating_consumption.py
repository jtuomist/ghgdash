import dash_table
import dash_daq as daq
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objs as go
from dash_table.Format import Format, Scheme
from dash.dependencies import Input, Output

from calc.district_heating import calc_district_heating_unit_emissions_forecast
from calc.district_heating_consumption import (
    generate_heat_consumption_forecast, generate_heat_use_per_net_area_forecast_existing_buildings,
    generate_heat_use_per_net_area_forecast_new_buildings
)
from variables import get_variable, set_variable
from . import page_callback, Page



def draw_existing_building_unit_heat_factor_graph(df):
    hist_df = df.query('~Forecast')
    hist = go.Scatter(
        x=hist_df.index,
        y=hist_df.HeatUsePerNetArea,
        mode='lines',
        name='Ominaislämmönkulutus',
        line=dict(
            color='#9fc9eb',
        )
    )

    forecast_df = df.query('Forecast')
    forecast = go.Scatter(
        x=forecast_df.index,
        y=forecast_df.HeatUsePerNetArea,
        mode='lines',
        name='Ominaislämmönkulutus (enn.)',
        line=dict(
            color='#9fc9eb',
            dash='dash'
        )
    )
    layout = go.Layout(
        margin=go.layout.Margin(
            t=30,
            r=15,
            l=60,
        ),
        yaxis=dict(
            title='kWh/k-m²',
            rangemode='tozero',
        ),
        showlegend=False,
        title="Olemassaolevan rakennuskannan ominaislämmönkulutus"
    )

    fig = go.Figure(data=[hist, forecast], layout=layout)
    return fig


def draw_new_building_unit_heat_factor_graph(df):
    # forecast_df = df.query('Forecast')
    forecast_df = df
    forecast = go.Scatter(
        x=forecast_df.index,
        y=forecast_df,
        mode='lines',
        name='Ominaislämmönkulutus (enn.)',
        line=dict(
            color='#9fc9eb',
            dash='dash'
        )
    )
    layout = go.Layout(
        margin=go.layout.Margin(
            t=30,
            r=15,
            l=60,
        ),
        yaxis=dict(
            title='kWh/k-m²',
            rangemode='tozero',
        ),
        showlegend=False,
        title="Uuden rakennuskannan ominaislämmönkulutus"
    )

    fig = go.Figure(data=[forecast], layout=layout)
    return fig


def draw_heat_consumption(df):
    t1 = go.Scatter(
        x=df.index,
        y=df.ExistingBuildingHeatUse,
        mode='none',
        fill='tonexty',
        name='Vanhat rakennukset',
        fillcolor='rgb(253, 79, 0)',
        line=dict(
            color='rgb(253, 79, 0)',
            shape='spline',
        ),
        stackgroup='one'
    )
    new_building_heat_use = df[df.Forecast].NewBuildingHeatUse
    t2 = go.Scatter(
        x=new_building_heat_use.index,
        y=new_building_heat_use,
        mode='none',
        name='Uudet rakennukset',
        line=dict(
            color='red',
            shape='spline',
            smoothing=1,
        ),
        stackgroup='one'
    )
    forecast_df = df[df.Forecast]
    forecast_start_year, forecast_end_year = forecast_df.index.min(), forecast_df.index.max()
    layout = go.Layout(
        margin=go.layout.Margin(
            t=30,
            r=15,
            l=60,
        ),
        yaxis=dict(
            title='GWh',
            rangemode='tozero',
            hoverformat='.3r',
            separatethousands=True,
            anchor='free',
            domain=[0.02, 1],
            tickfont=dict(
                family='HelsinkiGrotesk, Arial',
                size=14,
            ),
        ),
        xaxis=dict(
            showgrid=False,
            showline=False,
            anchor='free',
            domain=[0.01, 1],
            tickfont=dict(
                family='HelsinkiGrotesk, Arial',
                size=14,
            ),
        ),
        showlegend=False,
        title="Kaukolämmön kokonaiskulutus",
        separators=', ',
        shapes=[
            dict(
                type='rect',
                x0=forecast_start_year,
                x1=forecast_end_year,
                xref='x',
                y0=0,
                y1=1,
                yref='paper',
                opacity=0.2,
                fillcolor='white',
                line=dict(width=0)
            )
        ]
    )

    fig = go.Figure(data=[t1, t2], layout=layout)
    return fig


def draw_district_heat_consumption_emissions(df):
    hist_df = df.query('~Forecast')
    hist = go.Scatter(
        x=hist_df.index,
        y=hist_df['District heat consumption emissions'],
        mode='lines',
        name='Päästöt',
        line=dict(
            color='#9fc9eb',
        )
    )

    forecast_df = df.query('Forecast')
    forecast = go.Scatter(
        x=forecast_df.index,
        y=forecast_df['District heat consumption emissions'],
        mode='lines',
        name='Päästöt (enn.)',
        line=dict(
            color='#9fc9eb',
            dash='dash'
        )
    )
    layout = go.Layout(
        margin=go.layout.Margin(
            t=30,
            r=15,
            l=60,
        ),
        yaxis=dict(
            title='kt (CO₂e.)',
            rangemode='tozero',
            hoverformat='.3r',
            separatethousands=True,
        ),
        separators=', ',
        showlegend=False,
        title="Kaukolämmön kulutuksen päästöt"
    )

    fig = go.Figure(data=[hist, forecast], layout=layout)
    return fig


page_content = html.Div([
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody(html.Div([
            html.Div(dcc.Graph(id='district-heating-existing-building-unit-heat-factor'), className='slider-card__graph'),
            html.Div(dcc.Slider(
                id='district-heating-existing-building-unit-heat-factor-slider',
                vertical = True,
                min=-40,
                max=20,
                step=1,
                value=0,
                marks={x: '%.1f %%' % (x / 10) for x in range(-40, 20 + 1, 5)},
                className='mb-4'
            ), className='slider-card__slider'),
        ], className=" slider-card__content")), className="mb-4"), md=6),
        dbc.Col(dbc.Card(dbc.CardBody([
            dcc.Slider(
                id='district-heating-new-building-unit-heat-factor-slider',
                min=-40,
                max=20,
                step=1,
                value=0,
                marks={x: '%.1f %%' % (x / 10) for x in range(-40, 20 + 1, 5)},
                className='mb-4'
            ),
            dcc.Graph(id='district-heating-new-building-unit-heat-factor'),
        ]), className="mb-4"), md=6),
    ]),
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            dcc.Graph(id='district-heating-consumption', config=dict(showLink=True)),
        ]), className="mb-4"), md=6, className='offset-md-3'),
    ]),
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            dcc.Graph(id='district-heating-consumption-emissions'),
        ]), className="mb-4"), md=8, className='offset-md-2'),
    ])
])


@page_callback(
    [
        Output('district-heating-existing-building-unit-heat-factor', 'figure'),
        Output('district-heating-new-building-unit-heat-factor', 'figure'),
        Output('district-heating-consumption', 'figure'),
        Output('district-heating-consumption-emissions', 'figure'),
    ], [
        Input('district-heating-existing-building-unit-heat-factor-slider', 'value'),
        Input('district-heating-new-building-unit-heat-factor-slider', 'value'),
    ]
)
def district_heating_consumption_callback(existing_building_perc, new_building_perc):
    set_variable('district_heating_existing_building_efficiency_change', existing_building_perc / 10)
    set_variable('district_heating_new_building_efficiency_change', new_building_perc / 10)

    df = generate_heat_use_per_net_area_forecast_existing_buildings()
    fig1 = draw_existing_building_unit_heat_factor_graph(df)

    df = generate_heat_use_per_net_area_forecast_new_buildings()
    fig2 = draw_new_building_unit_heat_factor_graph(df)

    df = generate_heat_consumption_forecast()
    fig3 = draw_heat_consumption(df)

    df1, df2 = calc_district_heating_unit_emissions_forecast()

    fig4 = draw_district_heat_consumption_emissions(df1)

    return [fig1, fig2, fig3, fig4]


page = Page('Kaukolämmön kulutus', page_content, [district_heating_consumption_callback])
