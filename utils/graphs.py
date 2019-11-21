import copy
import plotly.graph_objs as go
import dash_bootstrap_components as dbc
import dash_html_components as html


def deepupdate(target, src):
    for k, v in src.items():
        if type(v) == list:
            if k not in target:
                target[k] = copy.deepcopy(v)
            else:
                target[k].extend(v)
        elif type(v) == dict:
            if k not in target:
                target[k] = copy.deepcopy(v)
            else:
                deepupdate(target[k], v)
        elif type(v) == set:
            if k not in target:
                target[k] = v.copy()
            else:
                target[k].update(v.copy())
        else:
            target[k] = copy.copy(v)


def make_layout(**kwargs):
    params = dict(
        margin=go.layout.Margin(
            t=30,
            r=15,
            l=60,
        ),
        yaxis=dict(
            rangemode='tozero',
            hoverformat='.3r',
            separatethousands=True,
            anchor='free',
            domain=[0.02, 1],
            tickfont=dict(
                family='HelsinkiGrotesk, Arial',
                size=14,
            ),
            gridwidth=1,
            gridcolor='#ccc',
        ),
        xaxis=dict(
            showgrid=False,
            showline=False,
            anchor='free',
            domain=[0.01, 1],
            tickfont=dict(
                family='HelsinkiGrotesk, Arial',
                size=14,
            ),
            gridwidth=1,
            gridcolor='#ccc',
        ),
        font=dict(
            family='HelsinkiGrotesk, Open Sans, Arial'
        ),
        separators=', ',
        plot_bgcolor='#fff',
    )
    if 'legend' not in kwargs:
        params['showlegend'] = False

    deepupdate(params, kwargs)

    return go.Layout(**params)


def make_graph_card(graph, *args, **kwargs):
    class_name = getattr(graph, 'className', '')
    graph.className = ' '.join([class_name, 'slider-card__graph'])
    out = dbc.Card(
        dbc.CardBody(
            html.Div([
                graph
            ], className="slider-card__content"),
        ), className="mb-4"
    )
    return out
