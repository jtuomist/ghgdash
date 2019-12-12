import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import plotly.graph_objs as go

from variables import set_variable, get_variable
from components.stickybar import StickyBar
from components.graphs import make_layout, PredictionGraph
from components.cards import GraphCard, ConnectedCardGrid
from .base import Page

from calc.cars import generate_cars_mileage_forecast, predict_cars_emissions

CARS_GOAL = 119  # kt CO2e


def draw_bev_chart():
    df = predict_cars_emissions()

    data = []
    for col in {'electric', 'gasoline', 'diesel'}:
        data.append(go.Scatter(
            x=df.index,
            y=df[col],
            hovertemplate='%{x}: %{y:.0f} %',
            mode='lines',
            name=col,
            line=dict(
                dash='dash'
            )
        ))

    layout = make_layout(
        yaxis=dict(
            title='%',
            range=[0, 100],
        ),
        showlegend=True,
        title="Sähköautojen ajosuoriteosuus"
    )
    return go.Figure(data=data, layout=layout)


def draw_mileage_chart():
    df = generate_cars_mileage_forecast()
    graph = PredictionGraph(
        sector_name='Transportation',
        unit_name='Mkm',
        title='Ajokilometrien kehitys',
    )
    graph.add_series(
        df=df, column_name='Mileage', trace_name='Ajosuorite',
    )
    return graph.get_figure()


def draw_emissions_chart():
    df = predict_cars_emissions()
    graph = PredictionGraph(
        sector_name='Transportation',
        unit_name='kt (CO₂e.)',
        title='Henkilöautoilun päästöt',
    )
    graph.add_series(
        df=df, column_name='Emissions', trace_name='Päästöt',
    )
    return graph.get_figure()


def make_bottom_bar(df):
    df = predict_cars_emissions()
    last_emissions = df.iloc[-1].loc['Emissions']

    bar = StickyBar(
        label="Henkilöautojen päästöt yhteensä",
        value=last_emissions,
        goal=CARS_GOAL,
        unit='kt (CO₂e.) / a',
        current_page=page
    )
    return bar.render()


def generate_page():
    grid = ConnectedCardGrid()
    bev_perc_card = GraphCard(
        id='cars-bev-percentage',
        slider=dict(
            min=0,
            max=100,
            step=5,
            value=get_variable('cars_bev_percentage'),
            marks={x: '%d %%' % x for x in range(0, 100 + 1, 10)},
        ),
    )
    mileage_card = GraphCard(
        id='cars-total-mileage',
        slider=dict(
            min=-40,
            max=40,
            step=5,
            value=get_variable('cars_mileage_adjustment'),
            marks={x: '%d %%' % (x) for x in range(-40, 40 + 1, 10)},
        ),
    )
    grid.make_new_row()
    grid.add_card(bev_perc_card)
    grid.add_card(mileage_card)

    grid.make_new_row()
    emissions_card = GraphCard(
        id='cars-emissions',
    )
    grid.add_card(emissions_card)
    bev_perc_card.connect_to(emissions_card)
    mileage_card.connect_to(emissions_card)

    return html.Div([
        grid.render(),
        html.Div(id='cars-sticky-page-summary-container')
    ])


page = Page(
    id='cars',
    name='Henkilöautoilun päästöt',
    content=generate_page,
    path='/autot',
    emission_sector=('Transportation', 'Cars')
)


@page.callback(inputs=[
    Input('cars-bev-percentage-slider', 'value'),
    Input('cars-total-mileage-slider', 'value'),
], outputs=[
    Output('cars-bev-percentage-graph', 'figure'),
    Output('cars-total-mileage-graph', 'figure'),
    Output('cars-emissions-graph', 'figure'),
    Output('cars-sticky-page-summary-container', 'children'),
])
def cars_callback(bev_percentage, mileage_adj):
    set_variable('cars_bev_percentage', bev_percentage)
    set_variable('cars_mileage_adjustment', mileage_adj)

    bev_chart = draw_bev_chart()
    mileage_chart = draw_mileage_chart()
    emissions_chart = draw_emissions_chart()
    sticky = make_bottom_bar(None)

    return [bev_chart, mileage_chart, emissions_chart, sticky]
