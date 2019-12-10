import dash_bootstrap_components as dbc
import dash_html_components as html
import dash_core_components as dcc

from utils import deepupdate


def make_graph_card(card_id: str, graph: dict = None, slider: dict = None, borders: dict = None) -> dbc.Card:
    els = []
    graph_attrs = {
        'config': dict(
            displayModeBar=False,
            responsive=True,
        )
    }
    if graph is not None:
        deepupdate(graph_attrs, graph)
    els.append(dcc.Graph(id='%s-graph' % card_id, className='slider-card__graph', **graph_attrs))
    if slider:
        slider_args = ['min', 'max', 'step', 'value', 'marks']
        assert set(slider.keys()).issubset(set(slider_args))
        slider_el = dcc.Slider(
            id='%s-slider' % card_id,
            vertical=True,
            className='mb-4',
            **slider,
        )
        els.append(html.Div(slider_el, className='slider-card__slider'))

    borders = borders or {}
    card_class_name = 'mb-4'
    if borders.get('bottom'):
        card_class_name += ' card-border-bottom'

    return dbc.Card(
        dbc.CardBody(
            html.Div(els, className="slider-card__content")
        ), className=card_class_name
    )
