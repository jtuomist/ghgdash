import dash_bootstrap_components as dbc
import dash_html_components as html

from utils import deepupdate


def make_layout(**kwargs):
    params = dict(
        margin=dict(
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

    # ret = go.Layout(**params)
    return params


class ConnectedGraphGridRow:
    def add_graph(self):
        pass


class ConnectedGraphGrid:
    def __init__(self):
        self.rows = []

    def add_row(self):
        row = ConnectedGraphGridRow()
        self.rows.append(row)
        return row
