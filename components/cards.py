from __future__ import annotations

from dataclasses import dataclass
from dash.development.base_component import Component
from dash_archer import DashArcherContainer, DashArcherElement
import dash_bootstrap_components as dbc
import dash_html_components as html
import dash_core_components as dcc

from utils import deepupdate
from utils.colors import ARCHER_STROKE


@dataclass
class GraphCard:
    id: str
    graph: dict = None
    slider: dict = None
    extra_content: Component = None
    link_to_page: Page = None

    def __post_init__(self):
        self.classes = []
        self.upstream_card = None
        self.downstream_card = None

    def connect_to(self, card: GraphCard):
        self.downstream_card = card
        card.upstream_card = self

    def render(self, is_top_row: bool = True) -> dbc.Card:
        els = []
        graph_attrs = {
            'config': dict(
                displayModeBar=False,
                responsive=True,
            )
        }
        if self.graph is not None:
            deepupdate(graph_attrs, self.graph)
        els.append(dcc.Graph(id='%s-graph' % self.id, className='slider-card__graph', **graph_attrs))
        if self.slider:
            slider_args = ['min', 'max', 'step', 'value', 'marks']
            assert set(self.slider.keys()).issubset(set(slider_args))
            slider_el = dcc.Slider(
                id='%s-slider' % self.id,
                vertical=True,
                className='mb-4',
                **self.slider,
            )
            els.append(html.Div(slider_el, className='slider-card__slider'))

        classes = ['mb-4']
        if self.downstream_card:
            classes.append('card-border-bottom')

        if self.upstream_card:
            classes.append('card-border-top')
            classes.append('grid-downstream-card')
        elif not is_top_row:
            classes.append('grid-unconnected-downstream-card')

        card = dbc.Card(
            dbc.CardBody(children=[
                html.Div(els, className="slider-card__content"),
                self.extra_content,
            ]), className=' '.join(classes),
        )
        if self.link_to_page:
            return html.A(card, href=self.link_to_page.path)
        else:
            return card


class ConnectedCardGridRow:
    width = 12

    def __init__(self):
        self.cards = []

    def add_card(self, card: GraphCard):
        self.cards.append(card)

    def set_width(self, width: int):
        self.width = width


class ConnectedCardGrid:
    def __init__(self):
        self.rows = []

    def make_new_row(self) -> ConnectedCardGridRow:
        row = ConnectedCardGridRow()
        self.rows.append(row)
        return row

    def add_card(self, card: GraphCard):
        """Helper method to add a card to the last row"""
        self.rows[-1].add_card(card)

    def render(self) -> Component:
        grid_has_archer = False
        # First check if this is an archered grid
        for row in self.rows:
            for card in row.cards:
                if card.downstream_card or card.upstream_card:
                    grid_has_archer = True
                    break
            if grid_has_archer:
                break

        rows = []
        for row_idx, row in enumerate(self.rows):
            grid_cols_per_card = 12 // len(row.cards)
            cols = []
            for card in row.cards:
                is_top_row = row_idx == 0
                card_el = card.render(is_top_row)
                if card.downstream_card or card.upstream_card:
                    relations = []
                    if card.downstream_card:
                        relations.append(dict(
                            targetId='%s-elem' % card.downstream_card.id,
                            targetAnchor='top',
                            sourceAnchor='bottom'
                        ))
                    card_el = DashArcherElement(
                        card_el,
                        id='%s-elem' % card.id,
                        relations=relations
                    )

                cols.append(dbc.Col(md=grid_cols_per_card, children=card_el))

            rows.append(dbc.Row(cols))

        if grid_has_archer:
            children = DashArcherContainer(
                rows,
                strokeColor=ARCHER_STROKE['default']['color'],
                strokeWidth=ARCHER_STROKE['default']['width'],
                arrowLength=0.001,
                arrowThickness=0.001,
            )
        else:
            children = rows

        return dbc.Row(dbc.Col(md=10, children=children))
