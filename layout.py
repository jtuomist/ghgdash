from collections import OrderedDict

import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

from flask import session

from pages import page_callback
from pages.district_heating_consumption import page as district_heating_consumption_page
from pages.district_heating import page as district_heating_page
from pages.population import page as population_page
from pages.buildings import page as buildings_page
from pages.emissions import page as emissions_page
from pages.components import page as components_page
from pages.empty import page as empty_page
from pages.electricity import page as electricity_page
# from pages.hel_buildings import page as hel_buildings_page
from pages.custom_settings import page as custom_settings_page


mock_sub_routes = OrderedDict([
    ('Kaukolämpö', 'kaukolammon-kulutus'),
    ('Sähkölämmitys', 'empty'),
    ('Öljylämpö', 'empty'),
    ('Maalämpö', 'empty'),
])


def make_navbar():
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


def generate_page(left_nav_children, page_content_children):
    els = [
        # represents the URL bar, doesn't render anything
        make_navbar(),
        dbc.Container(
            dbc.Row([
                dbc.Col(md=2, children=[
                    dbc.ListGroup(id='left-nav', children=left_nav_children)
                ]),
                dbc.Col(md=10, children=[
                    html.Div(id='page-content', children=page_content_children)
                ])
            ]),
            className="app-content",
            fluid=True
        )
    ]
    return html.Div(els)


routes = OrderedDict([
    ('', emissions_page),
    ('kaukolammon-kulutus', district_heating_consumption_page),
    ('vaesto', population_page),
    ('rakennukset', buildings_page),
    ('kaukolammon-tuotanto', district_heating_page),
    # ('helsingin-rakennukset', hel_buildings_page),
    ('omat-asetukset', custom_settings_page),
    ('empty', empty_page),
    ('electricity', electricity_page),
    ('components', components_page),
])


@page_callback(
    [Output('app-content', 'children')],
    [Input('url', 'pathname')]
)
def display_page(current_path):
    print('display_page called 1')
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

    ret = [generate_page(left_nav_items, page_content)]
    return ret


def generate_layout(app):
    for page in routes.values():
        # Register the callbacks to Dash
        for callback in page.callbacks:
            wrap_callback = app.callback(callback.output, callback.inputs, callback.state)
            wrap_callback(callback)

    callback = display_page
    wrap_callback = app.callback(callback.output, callback.inputs, callback.state)
    wrap_callback(callback)

    return html.Div(children=[
        dcc.Location(id='url', refresh=False),
        html.Div(id='app-content'),
    ])
