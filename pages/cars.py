import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objs as go

from variables import set_variable, get_variable
from components.stickybar import StickyBar
from components.graphs import make_layout, PredictionGraph
from components.cards import GraphCard, ConnectedCardGrid
from .base import Page

from calc.cars import predict_cars_mileage, predict_cars_emissions
from utils.colors import GHG_MAIN_SECTOR_COLORS

CARS_GOAL = 119  # kt CO2e


ENGINE_TYPES = {
    'electric': dict(name='Sähkömoottori', color=GHG_MAIN_SECTOR_COLORS['ElectricityConsumption']),
    'gasoline': dict(name='Bensiinimoottori', color='#ffc61e'),
    'diesel': dict(name='Dieselmoottori', color='#bd2719'),
}


def draw_bev_chart(df):
    df = df.dropna()
    graph = PredictionGraph(
        sector_name='Transportation',
        unit_name='%',
        title='Sähköautojen ajosuoriteosuus',
        legend=True,
        legend_x=0.6,
        y_max=100,
    )
    for col in {'electric', 'gasoline', 'diesel'}:
        et = ENGINE_TYPES[col]
        df[col] *= 100
        graph.add_series(
            df=df, column_name=col, trace_name=et['name'], historical_color=et['color']
        )

    return graph.get_figure()


def make_bottom_bar(df):
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
    per_resident_card = GraphCard(
        id='cars-mileage-per-resident',
        slider=dict(
            min=-60,
            max=20,
            step=5,
            value=get_variable('cars_mileage_per_resident_adjustment'),
            marks={x: '%d %%' % (x) for x in range(-60, 20 + 1, 10)},
        ),
    )
    mileage_card = GraphCard(
        id='cars-total-mileage',
    )
    emission_factor_card = GraphCard(
        id='cars-emission-factor',
    )
    emissions_card = GraphCard(
        id='cars-emissions',
    )
    biofuel_card = GraphCard(
        id='cars-biofuel-percentage',
    )

    grid.make_new_row()
    grid.add_card(bev_perc_card)
    grid.add_card(biofuel_card)
    grid.add_card(per_resident_card)
    grid.make_new_row()
    grid.add_card(emission_factor_card)
    grid.add_card(mileage_card)
    grid.make_new_row()
    grid.add_card(emissions_card)

    bev_perc_card.connect_to(emission_factor_card)
    biofuel_card.connect_to(emission_factor_card)
    emission_factor_card.connect_to(emissions_card)

    per_resident_card.connect_to(mileage_card)
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
    Input('cars-mileage-per-resident-slider', 'value'),
], outputs=[
    Output('cars-bev-percentage-graph', 'figure'),
    Output('cars-biofuel-percentage-graph', 'figure'),
    Output('cars-emission-factor-graph', 'figure'),
    Output('cars-mileage-per-resident-graph', 'figure'),
    Output('cars-total-mileage-graph', 'figure'),
    Output('cars-emissions-graph', 'figure'),
    Output('cars-sticky-page-summary-container', 'children'),
])
def cars_callback(bev_percentage, mileage_adj):
    set_variable('cars_bev_percentage', bev_percentage)
    set_variable('cars_mileage_per_resident_adjustment', mileage_adj)

    df = predict_cars_emissions()
    df['Mileage'] /= 1000000

    bev_chart = draw_bev_chart(df)
    graph = PredictionGraph(
        sector_name='Transportation',
        unit_name='%',
        title='Biopolttoaineiden osuus myydyissä polttoaineissa',
    )
    graph.add_series(
        df=df, column_name='electric', trace_name='Bion osuus'
    )
    biofuel_chart = graph.get_figure()

    graph = PredictionGraph(
        sector_name='Transportation',
        unit_name='km/as.',
        title='Ajokilometrit asukasta kohti',
    )
    graph.add_series(
        df=df, column_name='PerResident', trace_name='Suorite/as.',
    )
    per_resident_chart = graph.get_figure()

    # Total mileage
    graph = PredictionGraph(
        sector_name='Transportation',
        unit_name='Mkm',
        title='Ajokilometrien kehitys',
    )
    graph.add_series(
        df=df, column_name='Mileage', trace_name='Ajosuorite',
    )
    mileage_chart = graph.get_figure()

    # Total emissions
    graph = PredictionGraph(
        sector_name='Transportation',
        unit_name='g/km',
        title='Henkilöautojen päästökerroin',
    )
    graph.add_series(
        df=df, column_name='EmissionFactor', trace_name='Päästökerroin',
    )
    emission_factor_chart = graph.get_figure()

    # Total emissions
    graph = PredictionGraph(
        sector_name='Transportation',
        unit_name='kt (CO₂e.)',
        title='Henkilöautoilun päästöt',
    )
    graph.add_series(
        df=df, column_name='Emissions', trace_name='Päästöt',
    )
    emissions_chart = graph.get_figure()

    sticky = make_bottom_bar(df)

    return [
        bev_chart, biofuel_chart, emission_factor_chart,
        per_resident_chart, mileage_chart,
        emissions_chart, sticky
    ]


if __name__ == '__main__':
    generate_page()
    draw_bev_chart()
