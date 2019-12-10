import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from dash.dependencies import Input, Output

from variables import get_variable, set_variable
from calc.population import get_adjusted_population_forecast
from components.cards import make_graph_card
from components.graphs import make_layout
from .base import Page


def generate_population_forecast_graph(pop_df):
    hist_df = pop_df.query('~Forecast')
    hovertemplate = '%{x}: %{y:.0f} 000'
    hist = go.Scatter(
        x=hist_df.index,
        y=hist_df.Population / 1000,
        hovertemplate=hovertemplate,
        mode='lines',
        name='Väkiluku',
        line=dict(
            color='#9fc9eb',
        )
    )

    forecast_df = pop_df.query('Forecast')
    forecast = go.Scatter(
        x=forecast_df.index,
        y=forecast_df.Population / 1000,
        hovertemplate=hovertemplate,
        mode='lines',
        name='Väkiluku (enn.)',
        line=dict(
            color='#9fc9eb',
            dash='dash'
        )
    )
    layout = make_layout(
        yaxis=dict(
            title='1 000 asukasta',
            zeroline=True,
        ),
        showlegend=False,
        title="Helsingin asukasmäärä"
    )

    fig = go.Figure(data=[hist, forecast], layout=layout)
    return fig


def render_page():
    slider = dict(
        min=-20,
        max=20,
        step=5,
        value=get_variable('population_forecast_correction'),
        marks={x: '%d %%' % x for x in range(-20, 20 + 1, 5)},
    )
    pop_df = get_adjusted_population_forecast()
    card = make_graph_card(card_id='population', slider=slider)
    return dbc.Row(dbc.Col(card, md=6))

    cols = [
        dbc.Col([
            dcc.Graph(
                id='population-graph',
                config={
                    'displayModeBar': False,
                    'showLink': False,
                }
            ),
            html.Div([
                html.P(children=[
                    'Väestön määrä vuonna %s: ' % get_variable('target_year'),
                    html.Strong(id='population-count-target-year')
                ]),
            ]),
        ], md=8),
        dbc.Col([
            html.H5('Väestöennusteen korjausprosentti'),
            html.Div([
                dcc.Slider(
                    id='population-slider',
                    min=-20,
                    max=20,
                    step=5,
                    value=get_variable('population_forecast_correction'),
                    marks={x: '%d %%' % x for x in range(-20, 20 + 1, 5)},
                ),
            ]),
        ], md=4),
    ]

    return dbc.Row(cols)


page = Page(
    id='population',
    name='Väestö',
    content=render_page,
    path='/vaesto'
)


@page.callback(
    outputs=[Output('population-graph', 'figure')],
    inputs=[Input('population-slider', 'value')],
)
def population_callback(value):
    set_variable('population_forecast_correction', value)
    pop_df = get_adjusted_population_forecast()
    pop_in_target_year = pop_df.loc[[get_variable('target_year')]].Population
    fig = generate_population_forecast_graph(pop_df)

    # return fig, pop_in_target_year.round()
    return [fig]
