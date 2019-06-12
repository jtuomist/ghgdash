import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from dash.dependencies import Input, Output

from variables import set_variable
from calc.electricity import generate_electricity_consumption_forecast
from . import page_callback, Page
from flask_babel import gettext as _


def generate_electricity_consumption_forecast_graph(el_df):
    hist_df = el_df.query('~Forecast')
    hist = go.Scatter(
        x=hist_df.index,
        y=hist_df.ElectricityConsumption,
        mode='lines',
        name=_('Electricity consumption'),
        line=dict(
            color='#9fc9eb',
        )
    )

    forecast_df = el_df.query('Forecast')
    forecast = go.Scatter(
        x=forecast_df.index,
        y=forecast_df.ElectricityConsumption,
        mode='lines',
        name=_('Electricity consumption (forecast)'),
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
    )

    fig = go.Figure(data=[hist, forecast], layout=layout)
    return fig


electricity_page_content = dbc.Row([
    dbc.Col([
        dcc.Graph(
            id='electricity-consumption-graph',
            config={
                'displayModeBar': False,
                'showLink': False,
            }
        ),
    ], md=8),
    dbc.Col([
        html.H5(_('Electricity consumption adjustment')),
        html.Div([
            dcc.Slider(
                id='electricity-consumption-slider',
                min=-80,
                max=80,
                step=5,
                value=0,
                marks={x: '%d %%' % x for x in range(-80, 80 + 1, 20)},
            ),
        ]),
    ], md=4),
])


@page_callback(
    Output('electricity-consumption-graph', 'figure'),
    [Input('electricity-consumption-slider', 'value')])
def electricity_consumption_callback(value):
    set_variable('electricity_consumption_forecast_adjustment', value)
    df = generate_electricity_consumption_forecast()
    fig = generate_electricity_consumption_forecast_graph(df)

    return fig


page = Page(_('Electricity'), electricity_page_content, [electricity_consumption_callback])
