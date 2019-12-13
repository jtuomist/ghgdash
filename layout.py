import flask
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

from utils.perf import PerfCounter
from pages import load_pages, all_pages


load_pages()


def generate_layout():
    pages = []
    if not flask.has_request_context():
        from utils.perf import PerfCounter

        pc = PerfCounter('pages')
        pc.display('Rendering all')
        # Generate all pages for checking input and output callbacks
        for page in all_pages.values():
            pages.append(page.render())
            pc.display(page.name)
        pc.display('done')

    return html.Div(children=[
        dcc.Location(id='url', refresh=False),
        html.Div(id='app-content'),
        *pages,
    ])


def display_page(current_path, href):
    pc = PerfCounter('Page %s' % current_path)
    pc.display('start')

    if current_path.endswith('/') and len(current_path) > 1:
        current_path = current_path.lstrip('/')

    current_page = None
    for page_path, page in all_pages.items():
        if current_path == page_path:
            current_page = page
            break

    if not current_page:
        return [html.Div()]

    ret = current_page.render()

    pc.display('finished')
    return [ret]


def register_callbacks(app):
    wrap_callback = app.callback(
        [Output('app-content', 'children')],
        [Input('url', 'pathname'), Input('url', 'href')]
    )
    wrap_callback(display_page)

    for page in all_pages.values():
        # Register the callbacks to Dash
        for callback in page.callbacks:
            wrap_callback = app.callback(callback.outputs, callback.inputs, callback.state)
            wrap_callback(callback)
