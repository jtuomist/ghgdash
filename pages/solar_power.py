import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from dash.dependencies import Input, Output

from calc.solar_power import generate_solar_power_forecast
from variables import set_variable, get_variable
from components.graphs import make_layout
from .base import Page


SOLAR_POWER_GOAL = 1009  # GWh
CITY_OWNED = 19.0  # %


def generate_solar_power_graph(df, label, col):
    hist_df = df.query('~Forecast')
    hist = go.Scatter(
        x=hist_df.index,
        y=hist_df[col],
        mode='lines',
        name='Aurinkosähkö (MWp)',
        line=dict(
            color='#9fc9eb',
        )
    )

    forecast_df = df.query('Forecast')
    forecast = go.Scatter(
        x=forecast_df.index,
        y=forecast_df[col],
        mode='lines',
        name='Aurinkosähkö (enn.)',
        line=dict(
            color='#9fc9eb',
            dash='dash'
        )
    )

    layout = make_layout(
        yaxis=dict(title='MWp'),
        showlegend=False,
        title=label + " rakennuskannan aurinkopaneelien piikkiteho"
    )
    return go.Figure(data=[hist, forecast], layout=layout)


def generate_solar_power_stacked(df):
    pv_kwh_wp = get_variable('yearly_pv_energy_production_kwh_wp')
    df.SolarPowerNew = df.SolarPowerNew * pv_kwh_wp
    df.SolarPowerExisting = df.SolarPowerExisting * pv_kwh_wp

    t1 = go.Scatter(
        x=df.index,
        y=df.SolarPowerExisting,
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
    t2 = go.Scatter(
        x=df.index,
        y=df.SolarPowerNew,
        mode='none',
        name='Uudet rakennukset',
        line=dict(
            color='red',
            shape='spline',
            smoothing=1,
        ),
        stackgroup='one'
    )

    forecast_df = df.query('Forecast')
    forecast_start_year, forecast_end_year = forecast_df.index.min(), forecast_df.index.max()

    layout = make_layout(
        yaxis=dict(
            title='GWh',
        ),
        title="Aurinkopaneelien sähköntuotanto",
        shapes=[
            dict(
                type='rect',
                x0=forecast_start_year-1,
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
    egwpa = (forecast_df.SolarPowerExisting.iloc[-1] - forecast_df.SolarPowerExisting.iloc[0]) / (forecast_end_year - forecast_start_year)

    return go.Figure(data=[t1, t2], layout=layout), egwpa/pv_kwh_wp


def generate_page():
    return html.Div([
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.Div([
                    html.Div(dcc.Graph(id='solar-power-existing-buildings'), className='slider-card__graph'),
                    html.Div(dcc.Slider(
                        id='solar-power-existing-buildings-percentage-slider',
                        vertical=True,
                        min=20,
                        max=100,
                        step=5,
                        value=get_variable('solar_power_existing_buildings_percentage'),
                        marks={x: '%d %%' % x for x in range(20, 100 + 1, 5)},
                        className='mb-4'
                    ), className='slider-card__slider'),
                ], className="slider-card__content"),

                html.Div([
                    html.Span("Kaupungin tulisi rakentaa aurinkopaneeleja "),
                    html.Span(id='solar-power-city-gwp'),
                    html.Span(" vuodessa skenaarion toteutumiseksi."),
                ])
            ]), className="mb-4"), md=6),

            dbc.Col(dbc.Card(dbc.CardBody(html.Div([
                html.Div(dcc.Graph(id='solar-power-new-buildings'), className='slider-card__graph'),
                html.Div(dcc.Slider(
                    id='solar-power-new-buildings-percentage-slider',
                    vertical=True,
                    min=20,
                    max=100,
                    step=5,
                    value=get_variable('solar_power_new_buildings_percentage'),
                    marks={x: '%d %%' % x for x in range(20, 100 + 1, 5)},
                    className='mb-4'
                ), className='slider-card__slider'),
            ], className="slider-card__content")), className="mb-4"), md=6),
        ]),

        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                dcc.Graph(id='solar-power-total'),
                #html.Div(id='solar-power-total-card'),
            ]), className="mb-4"), md=6, className='offset-md-3'),
        ]),

        html.Div(id='solar-power-sticky-page-summary-container'),
    ])


page = Page(id='pv-production', name='Aurinkosähkön tuotanto', path='/aurinkopaneelit', content=generate_page)


@page.callback(
    outputs=[
        Output('solar-power-existing-buildings', 'figure'),
        Output('solar-power-new-buildings', 'figure'),
        Output('solar-power-total', 'figure'),
        Output('solar-power-city-gwp', 'children'),
        Output('solar-power-sticky-page-summary-container', 'children'),
    ], inputs=[
        Input('solar-power-existing-buildings-percentage-slider', 'value'),
        Input('solar-power-new-buildings-percentage-slider', 'value'),
    ]
)
def solar_power_callback(existing_building_perc, new_building_perc):
    set_variable('solar_power_existing_buildings_percentage', existing_building_perc)
    set_variable('solar_power_new_buildings_percentage', new_building_perc)

    kwp_df = generate_solar_power_forecast()
    fig_old = generate_solar_power_graph(kwp_df, "Vanhan", "SolarPowerExisting")
    fig_new = generate_solar_power_graph(kwp_df, "Uuden", "SolarPowerNew")
    fig_tot, egwpa = generate_solar_power_stacked(kwp_df)

    s = kwp_df.SolarPowerAll
    forecast = s.iloc[-1] * get_variable('yearly_pv_energy_production_kwh_wp')
    if forecast >= SOLAR_POWER_GOAL:
        sticky_class = 'page-summary__total--good'
    else:
        sticky_class = 'page-summary__total--bad'

    city_gwp = html.Span("%d MWp" % (1000 * egwpa * CITY_OWNED / 100), className='summary-card__value')

    sticky = [dbc.Alert([
        html.H6("Aurinkosähkön tuotanto yhteensä (2035)"),
        html.Div([
            html.Div(["%.0f" % forecast, html.Span(" GWh / a", className="unit")], className="page-summary__total " + sticky_class),
            html.Div(["tavoite %s" % SOLAR_POWER_GOAL, html.Span(" GWh / a", className="unit")], className="page-summary__target")
        ], className="page-summary__totals"),
    ], className="page-summary fixed-bottom")]

    return [fig_old, fig_new, fig_tot, city_gwp, sticky]
