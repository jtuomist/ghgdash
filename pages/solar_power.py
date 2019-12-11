import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from dash.dependencies import Input, Output

from calc.solar_power import predict_solar_power_production
from variables import set_variable, get_variable
from components.graphs import make_layout, PredictionGraph
from components.cards import make_graph_card
from components.stickybar import StickyBar
from .base import Page


SOLAR_POWER_GOAL = 1009  # GWh
CITY_OWNED = 19.0  # %


def generate_solar_power_graph(df, label, col, ymax):
    graph = PredictionGraph(
        df=df, sector_name='ElectricityConsumption', unit_name='MWp',
        trace_name='Piikkiteho', title='%s rakennuskannan aurinkopaneelien piikkiteho' % label,
        column_name=col, y_max=ymax
    )
    return graph.get_figure()


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

    forecast_df = df[df.Forecast]
    forecast_start_year, forecast_end_year = forecast_df.index.min(), forecast_df.index.max()

    layout = make_layout(
        yaxis=dict(
            title='GWh',
        ),
        title="Aurinkopaneelien sähköntuotanto",
        shapes=[
            dict(
                type='rect',
                x0=forecast_start_year - 1,
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
    hist_df = df[~df.Forecast]
    years_left = forecast_df.index.max() - hist_df.index.max()
    ekwpa = (forecast_df.SolarPowerExisting.iloc[-1] - hist_df.SolarPowerExisting.iloc[-1]) / years_left
    nkwpa = forecast_df.SolarPowerNew.iloc[-1] / years_left

    return go.Figure(data=[t1, t2], layout=layout), ekwpa / pv_kwh_wp, nkwpa / pv_kwh_wp


def generate_page():
    rows = []
    card = make_graph_card(
        card_id='solar-power-existing-buildings',
        slider=dict(
            min=0,
            max=90,
            step=5,
            value=get_variable('solar_power_existing_buildings_percentage'),
            marks={x: '%d %%' % x for x in range(0, 90 + 1, 10)},
        ),
        extra_content=html.Div(id='solar-power-existing-kwpa'),
    )
    card2 = make_graph_card(
        card_id='solar-power-new-buildings',
        slider=dict(
            min=20,
            max=100,
            step=5,
            value=get_variable('solar_power_new_buildings_percentage'),
            marks={x: '%d %%' % x for x in range(20, 100 + 1, 10)},
        ),
        extra_content=html.Div(id='solar-power-new-kwpa'),
    )

    rows.append(dbc.Row([
        dbc.Col(card, md=6),
        dbc.Col(card2, md=6)
    ]))

    card = make_graph_card(card_id='solar-power-total')
    rows.append(dbc.Row(dbc.Col(card, md=6, className='offset-md-3')))

    return html.Div([*rows, html.Div(id='solar-power-sticky-page-summary-container')])


page = Page(
    id='pv-production',
    name='Aurinkosähkön tuotanto',
    path='/aurinkopaneelit',
    emission_sector=['ElectricityConsumption', None],
    content=generate_page
)


@page.callback(
    outputs=[
        Output('solar-power-existing-buildings-graph', 'figure'),
        Output('solar-power-new-buildings-graph', 'figure'),
        Output('solar-power-total-graph', 'figure'),
        Output('solar-power-existing-kwpa', 'children'),
        Output('solar-power-new-kwpa', 'children'),
        Output('solar-power-sticky-page-summary-container', 'children'),
    ], inputs=[
        Input('solar-power-existing-buildings-slider', 'value'),
        Input('solar-power-new-buildings-slider', 'value'),
    ]
)
def solar_power_callback(existing_building_perc, new_building_perc):
    set_variable('solar_power_existing_buildings_percentage', 100)
    set_variable('solar_power_new_buildings_percentage', 100)
    kwp_max = predict_solar_power_production()

    set_variable('solar_power_existing_buildings_percentage', existing_building_perc)
    set_variable('solar_power_new_buildings_percentage', new_building_perc)
    kwp_df = predict_solar_power_production()

    ymax = kwp_max.SolarPowerExisting.iloc[-1]
    fig_old = generate_solar_power_graph(kwp_df, "Vanhan", "SolarPowerExisting", ymax)
    ymax = kwp_max.SolarPowerNew.iloc[-1]
    fig_new = generate_solar_power_graph(kwp_df, "Uuden", "SolarPowerNew", ymax)
    fig_tot, ekwpa, nkwpa = generate_solar_power_stacked(kwp_df)

    s = kwp_df.SolarPowerAll
    forecast = s.iloc[-1] * get_variable('yearly_pv_energy_production_kwh_wp')

    existing_kwpa = html.Div([
        html.Span("Kun aurinkopaneeleita rakennetaan "),
        html.Span('%d %%' % existing_building_perc, className='summary-card__value'),
        html.Span(" kaikesta vanhan rakennuskannan kattopotentiaalista, Helsingin kaupunkikonsernin tulee rakentaa aurinkopaneeleja "),
        html.Span("%d kWp" % (1000 * ekwpa * CITY_OWNED / 100), className='summary-card__value'),
        html.Span(" vuodessa skenaarion toteutumiseksi. Muiden kuin Helsingin kaupungin tulee rakentaa "),
        html.Span("%d kWp" % (1000 * ekwpa * (100 - CITY_OWNED) / 100), className='summary-card__value'),
        html.Span(" vuodessa."),
    ])

    new_kwpa = html.Div([
        html.Span("Kun uuteen rakennuskantaan rakennetaan aurinkopaneeleja "),
        html.Span('%d %%' % new_building_perc, className='summary-card__value'),
        html.Span(" kaikesta kattopotentiaalista, Helsingin kaupunkikonsernin tulee rakentaa aurinkopaneeleja "),
        html.Span("%d kWp" % (1000 * nkwpa * CITY_OWNED / 100), className='summary-card__value'),
        html.Span(" vuodessa skenaarion toteutumiseksi. Muiden kuin Helsingin kaupungin tulee rakentaa "),
        html.Span("%d kWp" % (1000 * nkwpa * (100 - CITY_OWNED) / 100), className='summary-card__value'),
        html.Span(" vuodessa."),
    ])

    sticky = StickyBar(
        label='Aurinkosähkön tuotanto',
        value=forecast, goal=SOLAR_POWER_GOAL,
        unit='GWh', current_page=page, below_goal_good=False,
    )

    return [fig_old, fig_new, fig_tot, existing_kwpa, new_kwpa, sticky.render()]
