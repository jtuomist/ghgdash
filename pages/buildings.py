import pandas as pd
import dash_bootstrap_components as dbc
import plotly.graph_objs as go

from calc.buildings import generate_building_floor_area_forecast
from components.graphs import make_layout
from components.cards import make_graph_card
from utils.colors import HELSINKI_COLORS
from .base import Page


BUILDING_USES = {
    'Asuinkerrostalot': dict(types=['Asuinkerrostalot'], color='brick'),
    'Muut asuinrakennukset': dict(types=['Erilliset pientalot', 'Rivi- tai ketjutalot'], color='metro'),
    'Julkiset palvelurakennukset': dict(
        types=['Liikenteen rakennukset', 'Opetusrakennukset', 'Hoitoalan rakennukset', 'Kokoontumisrakennukset'],
        color='summer'),
    'Liikerakennukset': dict(types=['Liikerakennukset'], color='coat'),
    'Teollisuusrakennukset': dict(types=['Teollisuusrakennukset'], color='fog'),
    'Toimistorakennukset': dict(types=['Toimistorakennukset'], color='gold'),
    'Muut rakennukset': dict(types=['Varastorakennukset', 'Muu tai tuntematon käyttötarkoitus'], color='silver'),
}

for building_name, attrs in BUILDING_USES.items():
    attrs['color'] = HELSINKI_COLORS[attrs['color']]


def generate_buildings_forecast_graph():
    df = generate_building_floor_area_forecast()

    cdf = pd.DataFrame(index=df.index)
    for name, attrs in BUILDING_USES.items():
        cdf[name] = df[attrs['types']].sum(axis=1) / 1000000

    # Sort columns based on the amounts in the last measured year
    last_year = cdf.loc[cdf.index.max()]
    columns = list(last_year.sort_values(ascending=False).index.values)

    traces = []
    for name in columns:
        attrs = BUILDING_USES[name]
        val = df[attrs['types']].sum(axis=1) / 1000000
        trace = go.Bar(
            x=df.index,
            y=val,
            name=name,
            marker=dict(color=attrs['color']),
            hoverinfo='name',
            hovertemplate='%{x}: %{y} Mkem²'
        )
        traces.append(trace)

    last_hist_year = df[~df.Forecast].index.max()
    forecast_divider = dict(
        type='line',
        x0=last_hist_year + 0.5,
        x1=last_hist_year + 0.5,
        xref='x',
        y0=0,
        y1=1,
        yref='paper',
        line=dict(dash='dot', color='grey')
    )

    layout = make_layout(
        barmode='stack',
        yaxis=dict(
            title='1 000 000 kem²',
        ),
        xaxis=dict(title='Vuosi'),
        title='Kerrosala käyttötarkoituksen mukaan',
        shapes=[forecast_divider],
        showlegend=True,
        autosize=True,
    )
    return go.Figure(data=traces, layout=layout)


def render_page():
    fig = generate_buildings_forecast_graph()
    ret = dbc.Row([
        dbc.Col([
            make_graph_card(card_id='buildings', graph=dict(figure=fig))
        ])
    ])

    return ret


page = Page(id='rakennukset', path='/rakennukset', name='Rakennukset', content=render_page)


if __name__ == '__main__':
    generate_buildings_forecast_graph()
