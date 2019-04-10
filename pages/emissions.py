import dash_table
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from dash_table.Format import Format, Scheme
from dash.dependencies import Input, Output

from variables import get_variable, set_variable
from utils.quilt import load_datasets
from . import page_callback, Page


INPUT_DATASETS = [
    'jyrjola/hsy/pks_khk_paastot',
]

ghg_emissions = None


def prepare_ghg_emissions_dataset(df):
    df = df[df.Kaupunki == 'Helsinki'].drop(columns='Kaupunki')
    df = df.set_index('Vuosi')
    return df


def find_consecutive_start(values):
    last_val = start_val = values[0]
    for val in values[1:]:
        if val - last_val != 1:
            start_val = val
        last_val = val
    return start_val


def generate_ghg_emission_graph(df):
    COLORS = {
        'Lämmitys': '#3E9FA8',
        'Sähkö': '#9FD9DA',
        'Liikenne': '#E9A5CA',
        'Teollisuus ja työkoneet': '#E281B6',
        'Jätteiden käsittely': '#9E266D',
        'Maatalous': '#680D48',
    }

    start_year = find_consecutive_start(df.index.unique())

    hist_df = df.query('~Forecast & index > %s' % start_year)

    latest_year = hist_df.loc[hist_df.index.max()]
    data_columns = list(latest_year.sort_values(ascending=False).index)
    data_columns.remove('Forecast')

    hist_traces = [go.Scatter(
        x=hist_df.index,
        y=hist_df[sector],
        mode='lines',
        name=sector,
        line=dict(
            color=COLORS[sector]
        )
    ) for sector in data_columns]

    forecast_df = df.query('Forecast | index == %s' % hist_df.index.max())
    forecast_traces = [go.Scatter(
        x=forecast_df.index,
        y=forecast_df[sector],
        mode='lines',
        name=sector,
        line=dict(
            color=COLORS[sector],
            dash='dash',
        ),
        showlegend=False,
    ) for sector in data_columns]

    layout = go.Layout(
        yaxis=dict(
            hoverformat='.3r',
            separatethousands=True,
            title='KHK-päästöt (kt CO₂-ekv.)'
        ),
        margin=go.layout.Margin(
            t=0,
            r=0,
        ),
        legend=dict(
            x=0.7,
            y=1,
            traceorder='normal',
            bgcolor='#fff',
        ),
    )

    fig = go.Figure(data=hist_traces + forecast_traces, layout=layout)
    return fig


GHG_SECTOR_MAP = {
    'heating': 'Lämmitys',
    'electricity': 'Sähkö',
    'transport': 'Liikenne',
    'waste_management': 'Jätteiden käsittely',
    'industry': 'Teollisuus ja työkoneet',
}

ghg_sliders = []


def generate_ghg_sliders():
    out = []
    for key, val in GHG_SECTOR_MAP.items():
        if val == 'Lämmitys':
            slider_val = 40
        else:
            slider_val = 25
        slider = dcc.Slider(
            id='ghg-%s-slider' % key,
            min=5,
            max=50,
            step=1,
            value=slider_val,
            marks={25: ''},
        )
        out.append(dbc.Col([
            html.Strong('%s' % val),
            slider
        ], md=12, className='mb-4'))
        ghg_sliders.append(slider)

    return dbc.Row(out)


def get_ghg_emissions_forecast():
    target_year = get_variable('target_year')
    reference_year = get_variable('ghg_reductions_reference_year')
    reduction_percentage = get_variable('ghg_reductions_percentage_in_target_year')
    sector_weights = get_variable('ghg_reductions_weights')

    df = ghg_emissions.reset_index().groupby(['Vuosi', 'Sektori1'])['Päästöt'].sum().reset_index().set_index('Vuosi')

    ref_emissions = df[df.index == reference_year]['Päästöt'].sum()
    target_emissions = ref_emissions * (1 - (reduction_percentage / 100))
    last_emissions = dict(df.loc[[df.index.max()], ['Sektori1', 'Päästöt']].reset_index().set_index('Sektori1')['Päästöt'])    

    other_sectors = [s for s in last_emissions.keys() if s not in GHG_SECTOR_MAP.values()]

    main_sector_emissions = sum([val for key, val in last_emissions.items() if key in GHG_SECTOR_MAP.values()])
    emission_shares = {sector_id: last_emissions[sector_name] / main_sector_emissions for sector_id, sector_name in GHG_SECTOR_MAP.items()}
    main_sector_target_emissions = target_emissions - sum([last_emissions[s] for s in other_sectors])

    target_year_emissions = {}

    weight_sum = sum(sector_weights.values())
    for sector_id, sector_name in GHG_SECTOR_MAP.items():
        weight = (sector_weights[sector_id] / weight_sum) * len(sector_weights)
        emission_shares[sector_id] /= weight

    sum_shares = sum(emission_shares.values())
    for key, val in emission_shares.items():
        emission_shares[key] = val / sum_shares

    for sector_id, sector_name in GHG_SECTOR_MAP.items():
        target = main_sector_target_emissions * emission_shares[sector_id]
        target_year_emissions[sector_name] = target

    for sector_name in other_sectors:
        target_year_emissions[sector_name] = last_emissions[sector_name]

    df = df.reset_index().set_index(['Vuosi', 'Sektori1']).unstack('Sektori1')
    df.columns = df.columns.get_level_values(1)
    last_historical_year = df.index.max()
    df.loc[target_year] = [target_year_emissions[x] for x in df.columns]
    df = df.reindex(range(df.index.min(), df.index.max() + 1))
    future = df.loc[df.index >= last_historical_year].interpolate()
    df.update(future)
    df.dropna(inplace=True)
    df.loc[df.index <= last_historical_year, 'Forecast'] = False
    df.loc[df.index > last_historical_year, 'Forecast'] = True
    return df


def prepare_input_datasets():
    global ghg_emissions

    ghg_in = load_datasets(INPUT_DATASETS)
    ghg_emissions = prepare_ghg_emissions_dataset(ghg_in)


emissions_page = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H2('Kasvihuonekaasupäästöt', style=dict(marginBottom='1em')),
            html.Div(id='ghg-emissions-table-container'),
        ])
    ]),
    dbc.Row([
        dbc.Col([
            html.Div(generate_ghg_sliders(), id='ghg-sliders'),
        ], md=4),
        dbc.Col([
            dcc.Graph(
                id='ghg-emissions-graph',
                config={
                    'displayModeBar': False,
                    'showLink': False,
                }
            ),
        ], md=8),
    ], className='mt-4')
])


@page_callback(
    [Output('ghg-emissions-graph', 'figure'), Output('ghg-emissions-table-container', 'children')],
    [Input(slider.id, 'value') for slider in ghg_sliders])
def ghg_slider_callback(*values):
    sectors = [x.id.split('-')[1] for x in ghg_sliders]
    new_values = {s: val for s, val in zip(sectors, values)}
    set_variable('ghg_reductions_weights', new_values)
    df = get_ghg_emissions_forecast()
    fig = generate_ghg_emission_graph(df)

    df['Yhteensä'] = df.sum(axis=1)
    last_hist_year = df[~df.Forecast].index.max()
    data_columns = list(df.loc[df.index == last_hist_year].stack().sort_values(ascending=False).index.get_level_values(1))

    data_columns.remove('Forecast')
    data_columns.insert(0, 'Vuosi')
    data_columns.remove('Yhteensä')
    data_columns.append('Yhteensä')

    last_forecast_year = df[df.Forecast].index.max()
    table_df = df.loc[df.index.isin([last_hist_year, last_forecast_year - 5, last_forecast_year - 10, last_forecast_year])]
    table_data = table_df.reset_index().to_dict('rows')
    table_cols = []
    for col_name in data_columns:
        col = dict(id=col_name, name=col_name)
        if col_name == 'Vuosi':
            pass
        else:
            col['type'] = 'numeric'
            col['format'] = Format(precision=0, scheme=Scheme.fixed)
        table_cols.append(col)
    table = dash_table.DataTable(
        data=table_data,
        columns=table_cols,
        # style_as_list_view=True,
        style_cell={'padding': '5px'},
        style_header={
            'fontWeight': 'bold'
        },
        style_cell_conditional=[
            {
                'if': {'column_id': 'Vuosi'},
                'fontWeight': 'bold',
            }
        ]
    )

    return [fig, table]


prepare_input_datasets()

page = Page('Päästöt', emissions_page, [ghg_slider_callback])
