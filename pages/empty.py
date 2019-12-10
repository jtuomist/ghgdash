import dash_html_components as html
import dash_bootstrap_components as dbc

from .base import Page

components_page_content = html.Div(children=[
    dbc.Alert("Tämä sivu on vielä kesken", color="primary")
])

page = Page(id='empty', name='Kesken', path='/empty', content=components_page_content)
