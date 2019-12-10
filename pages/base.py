import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from components.emission_nav import make_emission_nav

from dash.dependencies import Output
from flask import session


class Page:
    def __init__(self, id, name, content, path=None, emission_sector=None):
        self.id = id
        self.name = name
        self.content = content
        self.callbacks = []
        self.path = path
        self.emission_sector = emission_sector

    def __str__(self):
        return self.name

    def make_id(self, name):
        return '%s-%s' % (self.id, name)

    def make_navbar(self):
        custom_setting_count = len([k for k in session.keys() if not k.startswith('_')])
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
                id="dropdown-nav"
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

    def make_page_contents(self):
        if callable(self.content):
            content = self.content()
        else:
            content = self.content

        page_content = html.Div([
            html.H2(self.name), content
        ])

        ret = html.Div([
            # represents the URL bar, doesn't render anything
            self.make_navbar(),
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
        return html.Div(self.make_page_contents(), id=self.make_id('page-content'))

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
