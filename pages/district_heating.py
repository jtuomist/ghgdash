from dataclasses import dataclass
from functools import reduce

import dash_table
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objs as go
from dash_table.Format import Format, Scheme
from dash.dependencies import Input, Output

from calc.district_heating import (
    calc_district_heating_unit_emissions_forecast, prepare_fuel_classification_dataset
)
from components.cards import GraphCard
from components.card_description import CardDescription
from components.graphs import PredictionFigure
from components.stickybar import StickyBar
from variables import get_variable, set_variable
from .base import Page


def generate_district_heating_forecast_graph(df):
    graph = PredictionFigure(
        sector_name='BuildingHeating',
        unit_name='kt/vuosi',
        title='Kaukolämmön kulutuksen päästöt',
        smoothing=True,
        allow_nonconsecutive_years=True,
        fill=True,
    )
    graph.add_series(
        df=df, column_name='District heat consumption emissions', trace_name='Päästöt',
    )

    return graph.get_figure()


def generate_district_heating_emission_factor_graph(df):
    graph = PredictionFigure(
        sector_name='BuildingHeating',
        unit_name='g/kWh',
        title='Kaukolämmön päästökerroin',
        smoothing=True,
        allow_nonconsecutive_years=True,
    )
    graph.add_series(
        df=df, column_name='Emission factor', trace_name='Päästökerroin',
    )

    return graph.get_figure()


def generate_production_mix_graph(df):
    last_year = df.loc[df.index.max()]
    last_year = last_year.map(lambda x: np.nan if x < 1 else x).round()
    trace = go.Pie(
        labels=last_year.index,
        values=last_year,
        hole=0.6,
        sort=False,
        hovertemplate='%{label}<br />%{value} GWh<br />%{percent}'
    )
    layout = go.Layout(
        title=str(last_year.name),
        margin=go.layout.Margin(
            t=0,
            r=15,
            l=40,
        ),
    )

    return go.Figure(
        data=[trace],
        layout=layout
    )


def generate_district_heating_forecast_table(df):
    last_hist_year = df[~df.Forecast].index.max()
    df.index.name = 'Vuosi'

    data_columns = list(df.columns)
    data_columns.remove('Forecast')
    data_columns.insert(0, 'Vuosi')

    last_forecast_year = df[df.Forecast].index.max()
    table_df = df.loc[df.index.isin([last_hist_year, last_forecast_year - 5, last_forecast_year - 10, last_forecast_year])]
    table_data = table_df.reset_index().to_dict('rows')
    table_cols = []
    for col_name in data_columns:
        col = dict(id=col_name, name=col_name)
        if col_name == 'Year':
            pass
        else:
            col['type'] = 'numeric'
            col['format'] = Format(precision=0, scheme=Scheme.fixed)
        table_cols.append(col)
    table = dash_table.DataTable(
        data=table_data,
        columns=table_cols,
        style_cell={
            'minWidth': '0px', 'maxWidth': '70px',
            'whiteSpace': 'normal'
        },
        css=[{
            'selector': '.dash-cell div.dash-cell-value',
            'rule': 'display: inline; white-space: inherit; overflow: inherit; text-overflow: inherit;'
        }],
        style_header={
            'fontWeight': 'bold'
        },
        style_cell_conditional=[
            {
                'if': {'column_id': 'Year'},
                'fontWeight': 'bold',
            }
        ]
    )
    return table


@dataclass
class ProductionMethod:
    id: str
    name: str
    ratio_name: str = None

    def make_id(self, s):
        return 'district-heating-%s-%s' % (self.id, s)

    def get_ratio(self):
        key = self.ratio_name or self.name
        ratios = get_variable('district_heating_target_production_ratios')
        return ratios[key]

    def set_ratio(self, val):
        key = self.ratio_name or self.name
        ratios = get_variable('district_heating_target_production_ratios')
        assert key in ratios
        ratios[key] = val

    def get_ratio_input(self):
        return Input(self.make_id('ratio-slider'), 'value')

    def get_extra_inputs(self):
        return []

    def get_outputs(self):
        return [
            Output(self.make_id('ratio-value'), 'children'),
            Output(self.make_id('description'), 'children'),
        ]

    def get_output_values(self, production_stats, production_fuels):
        card_desc = self.generate_card_description(production_stats, production_fuels)
        if card_desc is not None:
            card_desc = html.Div(card_desc, className='mt-4')
        return ['%d %%' % self.get_ratio(), card_desc]

    def generate_card_description(self, production_stats, production_fuels):
        return None

    def get_extra_content(self):
        return None

    def render(self):
        header = html.H5(self.name, className='mt-4')
        slider = html.Div(children=dcc.Slider(
            id=self.make_id('ratio-slider'),
            max=100,
            min=0,
            step=5,
            value=self.get_ratio(),
        ), style=dict(marginLeft='-25px'))
        slider_val = html.Div(id=self.make_id('ratio-value'), style=dict(marginTop='-6px'))
        slider_row = dbc.Row([
            dbc.Col(slider, sm=10),
            dbc.Col(slider_val, sm=2),
        ])
        description = html.Div(id=self.make_id('description'))
        return dbc.Card(dbc.CardBody([header, slider_row, self.get_extra_content(), description]))


class CoalMethod(ProductionMethod):
    def generate_card_description(self, production_stats, production_fuels):
        target_year = production_fuels.iloc[-1]
        fuel_df = prepare_fuel_classification_dataset()
        ef = fuel_df[fuel_df.name == self.name].co2e_emission_factor.iloc[0]
        cd = CardDescription()
        cd.set_values(
            generated_heat=target_year.loc[self.ratio_name],
            ef=ef,
        )
        return cd.render("""
        Kivihiiltä polttamalla tuotetaan {generated_heat} GWh lämpöä.
        Kivihiilen päästökerroin on {ef} t/TJ.
        """)


class NaturalGasMethod(ProductionMethod):
    def generate_card_description(self, production_stats, production_fuels):
        target_year = production_fuels.iloc[-1]
        fuel_df = prepare_fuel_classification_dataset()
        ef = fuel_df[fuel_df.name == self.name].co2e_emission_factor.iloc[0]
        cd = CardDescription()
        cd.set_values(
            generated_heat=target_year.loc[self.name],
            ef=ef,
        )
        return cd.render("""
        Maakaasua polttamalla tuotetaan {generated_heat} GWh lämpöä.
        Maakaasun päästökerroin on {ef} t/TJ.
        """)


class PelletsMethod(ProductionMethod):
    def get_extra_content(self):
        return dbc.Row(dbc.Col([
            html.H6('Biopolttoaineen päästökerroin'),
            html.Div(dcc.Slider(
                id=self.make_id('emission-factor-slider'),
                value=get_variable('bio_emission_factor'),
                min=0,
                max=150,
                step=10,
                marks={x: '%d %%' % x for x in range(0, 150 + 1, 25)}
            ), style=dict(marginLeft='-12px')),
        ]))

    def get_extra_inputs(self):
        return [Input(self.make_id('emission-factor-slider'), 'value')]

    def set_extra_input_values(self, args):
        bio = args[0]
        set_variable('bio_emission_factor', bio)

    def generate_card_description(self, production_stats, production_fuels):
        target_year = production_fuels.iloc[-1]
        fuel_df = prepare_fuel_classification_dataset()
        bio_ef = fuel_df[fuel_df.name == self.name].co2e_emission_factor.iloc[0]
        bio_ef_perc = get_variable('bio_emission_factor')
        cd = CardDescription()
        cd.set_values(
            generated_heat=target_year.loc[self.name],
            bio_ef=bio_ef * bio_ef_perc / 100,
            bio_ef_perc=bio_ef_perc,
            bio_ef_real=bio_ef,
        )
        return cd.render("""
        Biomassaa polttamalla tuotetaan {generated_heat} GWh lämpöä.
        Biomassalle käytetään laskennallista päästökerrointa {bio_ef} t/TJ,
        joka on {bio_ef_perc:noround}\u00a0% biomassan fysikaalisesta
        päästökertoimesta ({bio_ef_real} t/TJ).
        """)


class HeatPumpMethod(ProductionMethod):
    def get_extra_content(self):
        return dbc.Row(dbc.Col([
            html.H6('Lämpöpumppujen COP-luku'),
            html.Div(dcc.Slider(
                id=self.make_id('cop-slider'),
                value=int(get_variable('district_heating_heat_pump_cop') * 10),
                min=30,
                max=100,
                step=1,
                marks={x: '%.1f' % (x / 10) for x in range(30, 100 + 1, 10)}
            ), style=dict(marginLeft='-12px'))
        ]))

    def get_extra_inputs(self):
        return [Input(self.make_id('cop-slider'), 'value')]

    def set_extra_input_values(self, args):
        cop = args[0]
        set_variable('district_heating_heat_pump_cop', float(cop / 10))

    def generate_card_description(self, production_stats, production_fuels):
        df = production_stats.iloc[-1]
        cd = CardDescription()
        cd.set_values(
            generated_heat=df.loc['Production with heat pumps'],
            cop=get_variable('district_heating_heat_pump_cop'),
            el_use=df.loc['Heat pump electricity consumption'],
        )
        return cd.render("""
        Vuonna {target_year} {municipality_locative} tuotetaan lämpöpumpuilla
        {generated_heat} GWh lämpöä. Lämpöpumppujen COP-luku on keskimäärin {cop:noround},
        jolloin lämpöpumput tarvitsevat {el_use} GWh sähköä.
        """)


production_methods = [
    HeatPumpMethod('heatpumps', 'Lämpöpumput'),
    PelletsMethod('pellets', 'Puupelletit ja -briketit'),
    CoalMethod('coal', 'Kivihiili', ratio_name='Kivihiili ja antrasiitti'),
    NaturalGasMethod('natural_gas', 'Maakaasu'),
]


def generate_ratio_sliders():
    eles = []
    for method in production_methods:
        eles.append(dbc.Col(method.render(), md=6))
    return eles


def render_page():
    els = []
    els.append(dbc.Row([
        dbc.Col([
            dbc.Row(children=[dbc.Col(m.render(), md=6, className='mb-4') for m in production_methods]),
            dbc.Row(dbc.Col(GraphCard(id='district-heating-emission-factor').render())),
            dbc.Row(dbc.Col(GraphCard(id='district-heating-production').render())),
            dbc.Row(dbc.Col(html.Div(id='district-heating-table-container'))),
        ], md=8),
    ]))
    els.append(html.Div(id='district-heating-prod-sticky-page-summary-container'))
    return html.Div(els)


page = Page(
    id='district-heat-production',
    name='Kaukolämmön tuotanto',
    content=render_page,
    path='/kaukolammon-tuotanto',
    emission_sector=('BuildingHeating', 'DistrictHeat', 'DistrictHeatProduction')
)


method_inputs = [m.get_ratio_input() for m in production_methods]
for m in production_methods:
    method_inputs += m.get_extra_inputs()


@page.callback(
    outputs=[
        Output('district-heating-emission-factor-graph', 'figure'),
        Output('district-heating-production-graph', 'figure'),
        Output('district-heating-table-container', 'children'),
        Output('district-heating-prod-sticky-page-summary-container', 'children'),
        *[o for m in production_methods for o in m.get_outputs()],
    ],
    inputs=method_inputs
)
def district_heating_callback(*args):
    # set_variable('bio_emission_factor', bio_emission_factor)

    args = list(args)
    weights = [args.pop(0) for m in production_methods]

    total_weights = sum(weights)
    if total_weights == 0:
        shares = [1 / len(weights)] * len(weights)
    else:
        shares = [val / total_weights for val in weights]
    shares = [int(x * 100) for x in shares]

    # Make sure the sum is 100
    diff = 100 - sum(shares)
    shares[0] += diff

    for method, share in zip(production_methods, shares):
        method.set_ratio(share)
        vals = [args.pop(0) for o in method.get_extra_inputs()]
        if vals:
            method.set_extra_input_values(vals)

    production_stats, production_source = calc_district_heating_unit_emissions_forecast()
    ef_fig = generate_district_heating_emission_factor_graph(production_stats)
    fig = generate_district_heating_forecast_graph(production_stats)
    table = generate_district_heating_forecast_table(production_stats)

    last_row = production_stats.iloc[-1]
    sticky = StickyBar(
        label='Kaukolämmöntuotannon päästökerroin', value=last_row['Emission factor'], unit='g/kWh',
        current_page=page,
    )

    method_outputs = []
    for method in production_methods:
        method_outputs += method.get_output_values(production_stats, production_source)

    return [ef_fig, fig, table, sticky.render(), *method_outputs]
