import pandas as pd
import dash_bootstrap_components as dbc
import dash_html_components as html
import plotly.graph_objs as go

from utils import deepupdate
from utils.data import find_consecutive_start
from utils.colors import GHG_MAIN_SECTOR_COLORS


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


class PredictionGraph:
    df: pd.DataFrame

    def __init__(
        self, df: pd.DataFrame, sector_name: str = None, title: str = None,
        trace_name: str = None, unit_name: str = None, column_name: str = None
    ):
        self.sector_name = sector_name
        self.trace_name = trace_name
        self.unit_name = unit_name
        self.title = title

        col_names = list(df.columns)
        assert 'Forecast' in df.columns
        col_names.remove('Forecast')
        if 'Year' in col_names:
            df = df.set_index('Year')
            col_names.remove('Year')

        if not column_name:
            # Make sure there is only one column for Y axis
            assert len(col_names) == 1
            self.column_name = col_names[0]
        else:
            assert isinstance(column_name, str)
            self.column_name = column_name
        self.df = df

    def get_figure(self):
        df = self.df

        start_year = find_consecutive_start(df.index)

        if self.sector_name:
            color = GHG_MAIN_SECTOR_COLORS[self.sector_name]
        else:
            color = None

        hist_df = df.loc[~df.Forecast & (df.index >= start_year)]
        hovertemplate = '%{x}: %{y}'
        if self.unit_name:
            hovertemplate += ' %s' % self.unit_name

        y_column = self.column_name

        hist_trace = go.Scatter(
            x=list(hist_df.index.astype(str)),
            y=hist_df[y_column],
            mode='lines',
            name=self.trace_name,
            hovertemplate=hovertemplate,
            line=dict(
                color=color,
            )
        )

        last_hist_year = hist_df.index.max()

        forecast_df = df[df.Forecast | (df.index == last_hist_year)]
        forecast_trace = go.Scatter(
            x=forecast_df.index.astype(str),
            y=forecast_df[y_column],
            mode='lines',
            name='%s (enn.)' % self.trace_name,
            hovertemplate=hovertemplate,
            line=dict(
                color=color,
                dash='dash'
            )
        )
        layout = make_layout(
            title=self.title,
            yaxis=dict(
                title=self.unit_name
            ),
            xaxis=dict(
                # type='linear',
                fixedrange=True,
            ),
        )

        fig = go.Figure(data=[hist_trace, forecast_trace], layout=layout)

        return fig


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
