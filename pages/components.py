import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import plotly.graph_objs as go

from . import page_callback, Page
from dash.dependencies import Input, Output

def slider_card(title):
    return dbc.Card([
        dbc.CardBody(
            [
                html.H3("Card title", className="card-title"),
                html.Div([
                    html.Div([
                        dcc.Graph(
                            id = "plot_1",
                            config = {"displayModeBar": False},
                            style = {'height': 300},
                            figure=go.Figure(
                                layout = go.Layout(
                                    margin=go.layout.Margin(
                                        l=20,
                                        r=20,
                                        b=20,
                                        t=20
                                    ),
                                    paper_bgcolor='#efefef',
                                    plot_bgcolor='#eeeeee'
                                )))
                        ],
                        className = "slider-card__graph",),
                    html.Div([
                            html.Div([
                                dcc.Slider(
                                        id = "slider_1",
                                        updatemode = "drag",
                                        vertical = True,
                                        marks = {i: "{}".format(i) for i in [10, 20, 30, 40]},
                                        min = 10,
                                        max = 40,
                                        step = 10,
                                        value = 10)], style = {"height": "300px"}),
                        ],
                    className = "slider-card__slider",)],
                className = "slider-card__content",
            )
        ],
        className = "slider-card"
        )
    ])

components_page_content = html.Div(children=[
    slider_card('Hello Dash!')
])

@page_callback(
    [Output('slider-output-container', 'children')],
    [Input('slider_1', 'value')])
def update_output(value):
    return '"{}"'.format(value)

page = Page('Components', components_page_content, [])
