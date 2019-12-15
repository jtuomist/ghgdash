from dataclasses import dataclass
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import plotly.graph_objs as go

from variables import get_variable
from calc.emissions import predict_emissions, get_sector_by_path


@dataclass
class StickyBar:
    label: str = None
    value: float = None
    unit: str = None
    goal: float = None
    current_page: object = None
    below_goal_good: bool = True

    def _calc_emissions(self):
        df = predict_emissions()
        forecast = df.pop('Forecast')
        self.emissions_df = df

        df = df.sum(axis=1)
        self.last_historical_year = df.loc[~forecast].index.max()
        self.target_year = get_variable('target_year')
        ref_year = get_variable('ghg_reductions_reference_year')
        perc = get_variable('ghg_reductions_percentage_in_target_year')
        ref_emissions = df.loc[ref_year]
        last_emissions = df.loc[self.last_historical_year]
        target_emissions = ref_emissions * (1 - perc / 100)
        self.target_emissions = target_emissions
        self.needed_reductions = last_emissions - target_emissions
        self.scenario_emissions = df.loc[self.target_year]
        self.scenario_reductions = last_emissions - self.scenario_emissions

    def _render_emissions_bar(self):
        df = self.emissions_df

        df = df.sum(axis=1, level=0)
        start_s = df.loc[self.last_historical_year]
        target_s = df.iloc[-1]
        reductions = (start_s - target_s).sort_values(ascending=False)
        traces = []
        page = self.current_page
        for sector_name, emissions in reductions.iteritems():
            sector_metadata = get_sector_by_path(sector_name)
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
                hovertemplate='%{x: .0f} kt',
                marker=dict(
                    color=sector_metadata['color']
                )
            )
            if active:
                bar['marker'].update(dict(
                    line_color='#888',
                    line_width=4,
                ))
            traces.append(bar)

        if self.scenario_reductions >= self.needed_reductions:
            range_max = self.scenario_reductions
        else:
            bar = dict(
                type='bar',
                x=[self.needed_reductions - self.scenario_reductions],
                name='Tavoitteesta puuttuu',
                orientation='h',
                hovertemplate='%{x: .0f} kt',
                marker=dict(
                    color='#888'
                ),
                opacity=0.5,
            )
            traces.append(bar)
            range_max = self.needed_reductions

        fig = dict(
            data=traces,
            layout=dict(
                xaxis=dict(
                    showgrid=False,
                    showline=False,
                    showticklabels=False,
                    zeroline=False,
                    domain=[0.15, 1],
                    autorange=False,
                    range=[0, range_max],
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
                transition={'duration': 500},
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

    def _render_value_summary(self, value, goal, label, unit, below_goal_good):
        classes = []
        if goal is not None:
            if (value <= goal and below_goal_good) or \
                    (value >= goal and not below_goal_good):
                classes.append('page-summary__total--good')
            else:
                classes.append('page-summary__total--bad')

            target_el = html.Div([
                "tavoite %.0f" % goal,
                html.Span(" %s" % unit, className="unit")
            ], className="page-summary__target")
        else:
            target_el = None

        classes.append('page-summary__total')

        summary = [
            html.H6(f'{label} ({self.target_year})'),
            html.Div([
                html.Div([
                    "%.0f" % value,
                    html.Span(" %s" % unit, className="unit")
                ], className=' '.join(classes)),
                target_el,
            ], className="page-summary__totals"),
        ]
        return summary

    def render(self):
        self._calc_emissions()
        pötkylä = dbc.Col([
            html.H6('Skenaarion mukaiset päästövähennykset %s–%s' % (self.last_historical_year, self.target_year)),
            self._render_emissions_bar()
        ], md=6)

        emissions_summary = self._render_value_summary(
            self.scenario_emissions, self.target_emissions, 'Kaikki päästöt yhteensä',
            'kt/vuosi', True
        )
        emissions_summary = dbc.Col(emissions_summary, md=3)

        if self.value is not None:
            summary = self._render_value_summary(
                self.value, self.goal, self.label, self.unit, self.below_goal_good
            )
            summary = dbc.Col(summary, md=3)
        else:
            summary = dbc.Col(md=3)

        return dbc.Alert([
            dbc.Row([pötkylä, summary, emissions_summary])
        ], className="page-summary fixed-bottom")
