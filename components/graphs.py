from dataclasses import dataclass
import pandas as pd
import plotly.graph_objs as go
from colour import Color

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
class PredictionGraphSeries:
    df: pd.DataFrame
    trace_name: str = None
    column_name: str = None
    historical_color: str = None
    forecast_color: str = None
    luminance_change: float = None

    def __post_init__(self):
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


@dataclass
class PredictionGraph:
    sector_name: str = None
    title: str = None
    unit_name: str = None
    y_max: float = None
    smoothing: bool = False

    def __post_init__(self):
        self.series_list = []

    def get_traces_for_series(self, series: PredictionGraphSeries, index: int, has_multiple_series: bool):
        df = series.df

        trace_attrs = {}
        if has_multiple_series:
            trace_attrs['mode'] = 'none'
            trace_attrs['fill'] = 'tozeroy' if index == 0 else 'tonexty'
        else:
            trace_attrs['mode'] = 'lines'

        start_year = find_consecutive_start(df.index)

        y_column = series.column_name
        hist_series = df.loc[~df.Forecast & (df.index >= start_year), y_column].dropna()

        hovertemplate = '%{x}: %{y}'
        if self.unit_name:
            hovertemplate += ' %s' % self.unit_name

        traces = []
        line_attrs = dict(width=4)
        if self.smoothing:
            line_attrs.update(dict(smoothing=1, shape='spline'))

        if len(hist_series):
            if not series.historical_color:
                color = Color(GHG_MAIN_SECTOR_COLORS[self.sector_name])
                if series.luminance_change:
                    color.set_luminance(color.get_luminance() * (1 + series.luminance_change))
            else:
                color = Color(series.historical_color)

            if has_multiple_series:
                trace_attrs['fillcolor'] = color.hex
                trace_attrs['stackgroup'] = 'history'

            hist_trace = dict(
                type='scatter',
                x=hist_series.index.astype(str),
                y=hist_series,
                name=series.trace_name,
                hovertemplate=hovertemplate,
                line=dict(
                    color=color.hex,
                    **line_attrs,
                ),
                **trace_attrs
            )

            traces.append(hist_trace)
            last_hist_year = hist_series.index.max()
            forecast_series = df.loc[df.Forecast | (df.index == last_hist_year), y_column]
        else:
            forecast_series = df.loc[df.Forecast, y_column]

        forecast_series = forecast_series.dropna()
        if len(forecast_series):
            if not series.forecast_color:
                color = Color(GHG_MAIN_SECTOR_COLORS[self.sector_name])
                if series.luminance_change:
                    color.set_luminance(color.get_luminance() * (1 + series.luminance_change))

                # Lighten forecast series by 30 %
                luminance = color.get_luminance()
                luminance = luminance + (1 - color.get_luminance()) * .3
                color.set_luminance(luminance)
            else:
                color = Color(series.forecast_color)

            if has_multiple_series:
                trace_attrs['fillcolor'] = color.hex
                trace_attrs['stackgroup'] = 'forecast'
            else:
                line_attrs['dash'] = 'dash'

            forecast_trace = go.Scatter(
                x=forecast_series.index.astype(str),
                y=forecast_series,
                name='%s (enn.)' % series.trace_name,
                hovertemplate=hovertemplate,
                line=dict(
                    color=color.hex,
                    **line_attrs,
                ),
                **trace_attrs
            )
            traces.insert(0, forecast_trace)

        return traces

    def add_series(self, *args, **kwargs):
        series = PredictionGraphSeries(*args, **kwargs)
        self.series_list.append(series)

    def get_figure(self):
        yattrs = {}
        if self.y_max:
            yattrs['fixedrange'] = True
            yattrs['range'] = [0, self.y_max]

        layout = make_layout(
            title=self.title,
            yaxis=dict(
                title=self.unit_name,
                **yattrs,
            ),
            xaxis=dict(
                # type='linear',
                fixedrange=True,
            ),
            hovermode='closest',
        )

        traces = []
        has_multiple = len(self.series_list) > 1
        for idx, series in enumerate(self.series_list):
            traces += self.get_traces_for_series(series, idx, has_multiple)

        fig = go.Figure(data=traces, layout=layout)

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
