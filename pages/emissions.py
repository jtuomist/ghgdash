import pandas as pd
import dash_bootstrap_components as dbc
import dash_html_components as html

from components.cards import GraphCard
from components.graphs import PredictionFigure
from components.stickybar import StickyBar
from variables import get_variable
from calc.emissions import predict_emissions, SECTORS
from pages import get_page_for_emission_sector
from .base import Page


def make_sector_fig(df, name, metadata):
    fig = PredictionFigure(
        sector_name=name,
        unit_name='kt',
        title=metadata['name'],
        smoothing=True,
        # allow_nonconsecutive_years=True,
        fill=True,
        stacked=True,
    )
    if len(df.columns) == 2:
        fig.add_series(df=df, trace_name='Päästöt', column_name='')
    else:
        fig.legend = True
        fig.legend_x = 0.8
        luminance_change = -0.3
        for idx, col_name in enumerate(df.columns):
            if col_name == 'Forecast':
                continue
            subsector = metadata['subsectors'][col_name]
            fig.add_series(
                df=df, trace_name=subsector['name'], column_name=col_name,
                luminance_change=luminance_change + 0.3 * idx
            )
    return fig.get_figure()


def render_page():
    cols = []
    edf = predict_emissions().dropna(axis=1, how='all')
    forecast = edf.pop('Forecast')
    graph = PredictionFigure(
        sector_name=None,
        unit_name='kt',
        title='Päästöt yhteensä',
        smoothing=True,
        fill=True,
        stacked=True,
        legend=True,
        legend_x=0.8
    )
    for sector_name, sector_metadata in SECTORS.items():
        df = pd.DataFrame(edf[sector_name])
        df['Forecast'] = forecast

        fig = make_sector_fig(df, sector_name, sector_metadata)
        sector_page = get_page_for_emission_sector(sector_name, None)
        card = GraphCard(id='emissions-%s' % sector_name, graph=dict(figure=fig), link_to_page=sector_page)
        cols.append(dbc.Col(card.render(), md=6))

        # Add the summed sector to the all emissions graph
        df = df.drop(columns=['Forecast'])
        s = df.sum(axis=1)
        s.name = 'Emissions'
        df = pd.DataFrame(s)
        df['Forecast'] = forecast
        graph.add_series(
            df=df, trace_name=sector_metadata['name'], column_name='Emissions',
            historical_color=sector_metadata['color']
        )

    target_year = get_variable('target_year')
    ref_year = get_variable('ghg_reductions_reference_year')
    perc_off = get_variable('ghg_reductions_percentage_in_target_year')

    ref_emissions = edf.loc[ref_year].sum()
    target_emissions = ref_emissions * (1 - perc_off / 100)

    target_year_emissions = edf.loc[target_year].sum()
    sticky = StickyBar(
        label='Päästöt yhteensä',
        goal=target_emissions,
        value=target_year_emissions,
        unit='kt',
        below_goal_good=True,
    )

    card = GraphCard(id='emissions-total', graph=dict(figure=graph.get_figure()))

    return html.Div([
        dbc.Row(dbc.Col(card.render())),
        dbc.Row(cols),
        sticky.render()
    ])


page = Page(
    id='emissions',
    name='Helsingin kasvihuonekaasupäästöt',
    content=render_page,
    path='/',
)


if __name__ == '__main__':
    render_page()
