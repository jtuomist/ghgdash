from dataclasses import dataclass
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import plotly.graph_objs as go

from variables import get_variable
from calc.emissions import generate_emissions_forecast, SECTORS
from utils.colors import GHG_MAIN_SECTOR_COLORS
from pages.base import Page


@dataclass
class StickyBar:
    label: str
    value: float
    goal: float
    unit: str
    current_page: Page = None
    below_goal_good: bool = True

    def render_emissions_bar(self):
        df = generate_emissions_forecast()

        last_historical_year = df.loc[~df.Forecast].Year.max()
        start_s = df[df.Year == last_historical_year].groupby('Sector1')['Emissions'].sum()
        target_s = df[df.Year == df.Year.max()].groupby('Sector1')['Emissions'].sum()

        reductions = (start_s - target_s).sort_values(ascending=False)
        traces = []
        page = self.current_page
        for sector_name, emissions in reductions.iteritems():
            sector_metadata = SECTORS[sector_name]
            if page is not None and page.emission_sector is not None and \
                    page.emission_sector[0] == sector_name:
                active = True
            else:
                active = False

            bar = dict(
                type='bar',
                x=[emissions],
                name=sector_metadata['name'],
                orientation='h',
                hovertemplate='%{x: .0f}',
                marker=dict(
                    color=GHG_MAIN_SECTOR_COLORS[sector_name]
                )
            )
            if active:
                bar['marker'].update(dict(
                    line_color='#888',
                    line_width=4,
                ))
            traces.append(bar)

        sum_reductions = reductions.sum()

        fig = go.Figure(
            data=traces,
            layout=go.Layout(
                xaxis=dict(
                    showgrid=False,
                    showline=False,
                    showticklabels=False,
                    zeroline=False,
                    domain=[0.15, 1],
                    autorange=False,
                    range=[0, sum_reductions],
                ),
                yaxis=dict(
                    showgrid=False,
                    showline=False,
                    showticklabels=False,
                    zeroline=False,
                ),
                margin=dict(
                    l=0,
                    r=0,
                    b=0,
                    t=0
                ),
                barmode='stack',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                showlegend=False,
                width=None,
                autosize=True,
                clickmode='none',
                dragmode=False,
            )
        )

        graph = dcc.Graph(
            config={
                'displayModeBar': False,
                'responsive': True,
            },
            style={'height': 60, 'width': '100%'},
            figure=fig,
        )
        return graph

    def render(self):
        if (self.value <= self.goal and self.below_goal_good) or \
                (self.value >= self.goal and not self.below_goal_good):
            sticky_class = 'page-summary__total--good'
        else:
            sticky_class = 'page-summary__total--bad'

        target_year = get_variable('target_year')

        summary = dbc.Col([
            html.H6(f'{self.label} ({target_year})'),
            html.Div([
                html.Div([
                    "%.0f" % self.value,
                    html.Span(" %s" % self.unit, className="unit")
                ], className="page-summary__total " + sticky_class),
                html.Div([
                    "tavoite %.0f" % self.goal,
                    html.Span(" %s" % self.unit, className="unit")
                ], className="page-summary__target")
            ], className="page-summary__totals"),
        ], md=6)

        pötkylä = dbc.Col([
            html.H6('Päästövähennykset'),
            self.render_emissions_bar()
        ], md=6)
        return dbc.Alert([
            dbc.Row([pötkylä, summary])
        ], className="page-summary fixed-bottom")
