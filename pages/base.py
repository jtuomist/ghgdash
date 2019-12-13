import flask
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from components.emission_nav import make_emission_nav

from dash.dependencies import Output
from flask import session

from calc.emissions import SECTORS


class Page:
    id: str
    name: str
    path: str
    emission_sector: tuple = None

    def __init__(self, id=None, name=None, content=None, path=None, emission_sector=None):
        if id:
            self.id = id
        if name:
            self.name = name
        if content:
            self.content = content
        if path:
            self.path = path
        if emission_sector:
            assert isinstance(emission_sector, (tuple, list, str))
            self.emission_sector = emission_sector
        if self.emission_sector and isinstance(self.emission_sector, str):
            self.emission_sector = (self.emission_sector,)
        if self.emission_sector:
            subsectors = SECTORS
            sector = None
            for sector_name in self.emission_sector:
                sector = subsectors[sector_name]
                subsectors = sector.get('subsectors', {})
            assert sector is not None
            self.sector_metadata = sector
            if not hasattr(self, 'name') or not self.name:
                self.name = sector['name']

        self.callbacks = []

    def __str__(self):
        return self.name

    def make_id(self, name):
        return '%s-%s' % (self.id, name)

    def _make_navbar(self):
        if flask.has_request_context():
            custom_setting_count = len([k for k in session.keys() if not k.startswith('_')])
        else:
            custom_setting_count = 0
        badge_el = None
        if custom_setting_count:
            badge_el = dbc.Badge(f'{custom_setting_count} ', className='badge-danger')

        els = [
            # dbc.NavItem(dbc.NavLink("Lämmitys", active=True, href="kaukolammon-kulutus")),
            # dbc.NavItem(dbc.NavLink("Liikenne", href="empty")),
            # dbc.NavItem(dbc.NavLink("Sähkö", href="electricity")),
            # dbc.NavItem(dbc.NavLink("Jätteet", href="empty")),
            # dbc.NavItem(dbc.NavLink("Teollisuus", href="empty")),
            # dbc.NavItem(dbc.NavLink("Maatalous", href="empty")),
            dbc.DropdownMenu(
                [
                    dbc.DropdownMenuItem("Väestö", href='/vaesto'),
                    dbc.DropdownMenuItem("Rakennukset", href='/rakennukset')
                ],
                nav=True,
                in_navbar=True,
                label="Oletukset",
                # id="dropdown-nav"
            ),
            dbc.NavItem(dbc.NavLink(href='/omat-asetukset', children=[
                "Omat asetukset",
                badge_el,
            ])),
        ]
        return dbc.NavbarSimple(
            brand="Päästöskenaario 2035",
            brand_href="/",
            color="primary",
            dark=True,
            fluid=True,
            children=els
        )

    def _make_page_contents(self):
        content = self.get_content()

        page_content = html.Div([
            html.H2(self.name), content
        ])

        ret = html.Div([
            # represents the URL bar, doesn't render anything
            self._make_navbar(),
            dbc.Container(
                dbc.Row([
                    dbc.Col(id=self.make_id('left-nav'), md=2, children=make_emission_nav(self)),
                    dbc.Col(md=10, children=page_content)
                ]),
                className="app-content",
                fluid=True
            )
        ])
        return ret

    def render(self):
        return html.Div(self._make_page_contents(), id=self.make_id('page-content'))

    def get_content(self):
        if callable(self.content):
            content = self.content()
        else:
            content = self.content
        return content

    def callback(self, inputs, outputs):
        assert isinstance(inputs, list)
        assert isinstance(outputs, list)

        def wrap_func(func):
            def call_func(*args):
                ret = func(*args)
                assert isinstance(ret, list)
                return ret + [make_emission_nav(self)]

            self.callbacks.append(call_func)

            call_func.outputs = outputs + [Output(self.make_id('left-nav'), 'children')]
            call_func.inputs = inputs
            call_func.state = []

            return call_func

        return wrap_func
