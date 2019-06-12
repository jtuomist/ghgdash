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
            l=40,
        ),
        showlegend=False,
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
            l=40,
        ),
        showlegend=False,
    )

    fig = go.Figure(data=[forecast], layout=layout)
    return fig


page_content = dbc.Row([
    dbc.Col([
        dcc.Slider(
            id='district-heating-existing-building-unit-heat-factor-slider',
            min=-40,
            max=20,
            step=1,
            value=0,
            marks={x: '%.1f %%' % (x / 10) for x in range(-40, 20 + 1, 5)},
            className='mb-4'
        ),
        dcc.Graph(id='district-heating-existing-building-unit-heat-factor'),
    ], md=6),
    dbc.Col([
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
    ], md=6),
])



@page_callback(
    [
        Output('district-heating-existing-building-unit-heat-factor', 'figure'),
        Output('district-heating-new-building-unit-heat-factor', 'figure')
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

    df1, df2 = calc_district_heating_unit_emissions_forecast()
    print(df1)
    print(df2)

    return [fig1, fig2]


page = Page('Kaukolämmön kulutus', page_content, [district_heating_consumption_callback])
