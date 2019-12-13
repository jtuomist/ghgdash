import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import plotly.graph_objs as go

from .base import Page
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
        className = "slider-card",
        )
    ],
    className = "mb-5",)

def total_emissions_bar():
    return html.Div(
            dcc.Graph(
                id = "bigBar",
                config = {"displayModeBar": False},
                style = {'height': 100},
                figure=go.Figure(
                    data=[
                        go.Bar(
                            x=[2476],
                            name="Lämmitys",
                            orientation="h"
                        ),
                        go.Bar(
                            x=[1390],
                            name="Liikenne",
                            orientation="h"
                        ),
                        go.Bar(
                            x=[681],
                            name="Sähkö",
                            orientation="h"
                        ),
                        go.Bar(
                            x=[135],
                            name="Teollisuus",
                            orientation="h"
                        )
                    ],
                    layout = go.Layout(
                        xaxis=dict(
                            showgrid=False,
                            showline=False,
                            showticklabels=False,
                            zeroline=False,
                            domain=[0.15, 1]
                        ),
                        yaxis=dict(
                            showgrid=False,
                            showline=False,
                            showticklabels=False,
                            zeroline=False,
                        ),
                        margin=go.layout.Margin(
                            l=20,
                            r=20,
                            b=20,
                            t=20
                        ),
                        barmode='stack',
                        paper_bgcolor='#efefef',
                        plot_bgcolor='#eeeeee',
                        showlegend=False,
                    ))))


components_page_content = html.Div(children=[
    slider_card("Hello Sliders"),
    total_emissions_bar(),
])

page = Page(id='components', name='Komponentit', content=components_page_content, path='/komponentit')


@page.callback(
    outputs=[Output('slider-output-container', 'children')],
    inputs=[Input('slider_1', 'value')]
)
def update_output(value):
    return '"{}"'.format(value)
