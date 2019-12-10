import pandas as pd

from .district_heating import predict_district_heating_emissions
from . import calcfunc


SECTORS = {
    'BuildingHeating': 'Rakennusten lämmitys',
    'Transportation': 'Liikenne',
    'ElectricityConsumption': 'Kulutussähkö',
    'Waste': 'Jätteiden käsittely',
    'Industry': 'Teollisuus ja työkoneet',
    'Agriculture': 'Maatalous',
}

HEATING_SUBSECTORS = {
    'DistrictHeat': 'Kaukolämpö',
    'OilHeating': 'Öljylämmitys',
    'ElectricityHeating': 'Sähkölämmitys',
    'GeothermalHeating': 'Maalämpö',
}

TARGETS = [
    ('Kaukolämpö', 754.589056908339, 250.733198734865),
    ('Öljylämmitys', 16.1569293157852, 0.0),
    ('Sähkölämmitys', 51.0638673954148, 29.7160855925585),
    ('Maalämpö', 0, 0),
    ('Kulutussähkö', 242.663770299608, 150.979312657901),
    ('Liikenne', 262.55592574098, 229.655246625791),
    ('Teollisuus ja työkoneet', 3.23358058861613, 2.62034901128448),
    ('Jätteiden käsittely', 60.5886441012345, 50.6492489473935),
    ('Maatalous', 0.637983301315191, 0.55519935555745),
]


@calcfunc(
    datasets=dict(
        ghg_emissions='jyrjola/hsy/pks_khk_paastot',
    ),
)
def prepare_emissions_dataset(datasets) -> pd.DataFrame:
    df = datasets['ghg_emissions']
    df = df[df.Kaupunki == 'Helsinki'].drop(columns='Kaupunki')
    df = df.set_index('Vuosi').copy()
    df = df.reset_index().groupby(['Vuosi', 'Sektori1', 'Sektori2'])['Päästöt'].sum().reset_index()

    sec_names = [x[0] for x in TARGETS]
    sec1 = df[df.Sektori1.isin(sec_names)].groupby(['Vuosi', 'Sektori1'])['Päästöt'].sum().reset_index()
    sec2 = df[df.Sektori2.isin(sec_names)].groupby(['Vuosi', 'Sektori2'])['Päästöt'].sum().reset_index()

    sec1 = sec1.rename(columns=dict(Sektori1='Sector', Päästöt='Emissions', Vuosi='Year'))
    sec2 = sec2.rename(columns=dict(Sektori2='Sector', Päästöt='Emissions', Vuosi='Year'))
    pd.set_option('display.max_rows', 200)
    df = sec1.append(sec2).set_index(['Year', 'Sector']).sort_index().reset_index()
    df = df.pivot(index='Year', columns='Sector', values='Emissions')
    return df


@calcfunc(
    variables=['target_year'],
    datasets=dict(),
    funcs=[prepare_emissions_dataset, predict_district_heating_emissions],
)
def generate_emissions_forecast(variables, datasets):
    df = prepare_emissions_dataset()

    last_historical_year = df.index.max()

    for year in range(df.index.max() + 1, variables['target_year'] + 1):
        df.loc[year] = None

    target_map = {x[0]: (x[1], x[2]) for x in TARGETS}
    df.loc[2030] = [target_map[key][0] for key in df.columns]
    df.loc[2035] = [target_map[key][1] for key in df.columns]
    df = df.interpolate()

    col_rename = SECTORS.copy()
    col_rename.pop('BuildingHeating')
    col_rename.update(HEATING_SUBSECTORS)
    col_rename = {val: key for key, val in col_rename.items()}
    df = df.rename(columns=col_rename)

    district_heat_df = predict_district_heating_emissions()
    df = df.drop(columns=['DistrictHeat'])
    df['DistrictHeat'] = district_heat_df['District heat consumption emissions']

    # df['Total'] = df.sum(axis=1)
    df = df.reset_index().melt(id_vars=['Year'], value_name='Emissions', var_name='Sector')
    df['Sector1'] = df.Sector.map(lambda x: x if x in SECTORS.keys() else 'BuildingHeating')
    df['Sector2'] = df.Sector.map(lambda x: x if x in HEATING_SUBSECTORS.keys() else '')
    df = df[['Year', 'Sector1', 'Sector2', 'Emissions']]

    df.loc[df.Year <= last_historical_year, 'Forecast'] = False
    df.loc[df.Year > last_historical_year, 'Forecast'] = True

    return df


if __name__ == '__main__':
    df = generate_emissions_forecast()
    df = df.set_index(['Sector1', 'Sector2'])
    print(df)
