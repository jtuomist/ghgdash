# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

from collections import OrderedDict

from pages.district_heating_consumption import page as district_heating_consumption_page
from pages.district_heating import page as district_heating_page
from pages.population import page as population_page
from pages.buildings import page as buildings_page
from pages.emissions import page as emissions_page
from pages.components import page as components_page
from pages.empty import page as empty_page
from pages.electricity import page as electricity_page
from pages.hel_buildings import page as hel_buildings_page

from flask_caching import Cache
from flask_session import Session
from flask_babel import Babel


app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True
)
app.css.config.serve_locally = True
app.scripts.config.serve_locally = True

server = app.server

cache = Cache(config={'CACHE_TYPE': 'simple'})
cache.init_app(server)

sess = Session()
sess.init_app(server)

babel = Babel(server)


navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("Lämmitys", active=True, href="kaukolammon-kulutus")),
        dbc.NavItem(dbc.NavLink("Liikenne", href="empty")),
        dbc.NavItem(dbc.NavLink("Sähkö", href="electricity")),
        dbc.NavItem(dbc.NavLink("Jätteet", href="empty")),
        dbc.NavItem(dbc.NavLink("Teollisuus", href="empty")),
        dbc.NavItem(dbc.NavLink("Maatalous", href="empty")),
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
    ],
    brand="Päästöskenaario 2035",
    brand_href="/",
    color="primary",
    dark=True,
    fluid=True,
)

left_nav = dbc.ListGroup(id='left-nav')

mock_sub_routes = OrderedDict([
    ('Kaukolämpö', 'kaukolammon-kulutus'),
    ('Sähkölämmitys', 'empty'),
    ('Öljylämpö', 'empty'),
    ('Maalämpö', 'empty'),
])

app.layout = html.Div([
    # represents the URL bar, doesn't render anything
    dcc.Location(id='url', refresh=False),
    navbar,
    dbc.Container(
        dbc.Row([
            dbc.Col(left_nav, md=2),
            dbc.Col([
                html.Div(id='page-content')
            ], md=10)
        ]),
        className="app-content",
        fluid=True
    )
])

routes = OrderedDict([
    ('', emissions_page),
    ('kaukolammon-kulutus', district_heating_consumption_page),
    ('vaesto', population_page),
    ('rakennukset', buildings_page),
    ('kaukolammon-tuotanto', district_heating_page),
    ('helsingin-rakennukset', hel_buildings_page),
    ('empty', empty_page),
    ('electricity', electricity_page),
    ('components', components_page),
])


#@app.callback([Output('left-nav', 'children'), Output('page-content', 'children')],
#              [Input('url', 'pathname')])
@app.callback([Output('page-content', 'children')],
              [Input('url', 'pathname')])
def display_page(current_path):
    print('display page for %s' % current_path)
    if current_path:
        current_path = current_path.strip('/')

    dropdownitems = []
    current_page = None
    for page_path, page in routes.items():
        attr = {}
        if current_path is not None and current_path == page_path:
            attr['active'] = True
            current_page = page
        item = dbc.DropdownMenuItem(page.name, href='/%s' % page_path)
        dropdownitems.append(item)

    left_nav_items = []
    for page_name, page_path in mock_sub_routes.items():
        attr = {}
        item = dbc.ListGroupItem(
            [
                html.Span(page_name),
                dbc.Badge("123 kt", color="light", className="ml-1 float-right")
            ],
            href='/%s' % page_path,
            **attr,
            disabled=page_path == "empty",
            action=True)
        left_nav_items.append(item)

    if current_page is not None:
        if callable(current_page.content):
            content = current_page.content()
        else:
            content = current_page.content

        page_content = html.Div([
            html.H2(current_page.name), content
        ])
    else:
        page_content = html.H2('Sivua ei löydy')

    #return [left_nav_items, page_content]
    return [page_content]


for page in routes.values():
    # Register the callbacks to Dash
    for callback in page.callbacks:
        wrap_callback = app.callback(callback.output, callback.inputs, callback.state)
        wrap_callback(callback)


if __name__ == '__main__':
    app.run_server(debug=True)
