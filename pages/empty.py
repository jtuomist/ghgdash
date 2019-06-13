import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc

from . import page_callback, Page

components_page_content = html.Div(children=[
    dbc.Alert("Tämä sivu on vielä kesken", color="primary")
])

page = Page('', components_page_content, [])
