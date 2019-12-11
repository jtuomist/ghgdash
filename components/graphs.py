from dataclasses import dataclass
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
    if 'title' in params:
        params['title'] = '<b>%s</b>' % params['title']

    # ret = go.Layout(**params)
    return params


@dataclass
class PredictionGraph:
    df: pd.DataFrame
    sector_name: str = None
    title: str = None
    trace_name: str = None
    unit_name: str = None
    column_name: str = None
    historical_color: str = None
    forecast_color: str = None
    smoothing: bool = False

    def __post_init__(self,):
        df = self.df
        col_names = list(df.columns)
        assert 'Forecast' in df.columns
        col_names.remove('Forecast')
        if 'Year' in col_names:
            self.df = df = df.set_index('Year')
            col_names.remove('Year')

        if not self.column_name:
            # Make sure there is only one column for Y axis
            assert len(col_names) == 1
            self.column_name = col_names[0]
        else:
            assert isinstance(self.column_name, str)

        if not self.historical_color:
            self.historical_color = GHG_MAIN_SECTOR_COLORS[self.sector_name]
        if not self.forecast_color:
            self.forecast_color = GHG_MAIN_SECTOR_COLORS[self.sector_name]

    def get_figure(self):
        df = self.df

        start_year = find_consecutive_start(df.index)

        y_column = self.column_name
        hist_series = df.loc[~df.Forecast & (df.index >= start_year), y_column].dropna()

        hovertemplate = '%{x}: %{y}'
        if self.unit_name:
            hovertemplate += ' %s' % self.unit_name

        traces = []
        line_attrs = dict(width=4)
        if self.smoothing:
            line_attrs.update(dict(smoothing=1, shape='spline'))

        if len(hist_series):
            hist_trace = dict(
                type='scatter',
                x=hist_series.index.astype(str),
                y=hist_series,
                mode='lines',
                name=self.trace_name,
                hovertemplate=hovertemplate,
                line=dict(
                    color=self.historical_color,
                    **line_attrs,
                )
            )

            traces.append(hist_trace)
            last_hist_year = hist_series.index.max()
            forecast_series = df.loc[df.Forecast | (df.index == last_hist_year), y_column]
        else:
            forecast_series = df[df.Forecast, y_column]

        forecast_trace = go.Scatter(
            x=forecast_series.index.astype(str),
            y=forecast_series,
            mode='lines',
            name='%s (enn.)' % self.trace_name,
            hovertemplate=hovertemplate,
            line=dict(
                color=self.forecast_color,
                dash='dash',
                **line_attrs,
            )
        )
        traces.append(forecast_trace)

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
