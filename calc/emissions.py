import pandas as pd

from .district_heating import predict_district_heating_emissions
from .electricity import predict_electricity_consumption_emissions
from .geothermal import predict_geothermal_production
from .cars import predict_cars_emissions
from . import calcfunc
from utils.colors import GHG_MAIN_SECTOR_COLORS

SECTORS = {
    'BuildingHeating': dict(
        name='Rakennusten lämmitys',
        subsectors={
            'DistrictHeat': dict(
                name='Kaukolämpö',
                subsectors={
                    'DistrictHeatProduction': dict(name='Kaukolämmön tuotanto'),
                }
            ),
            'OilHeating': dict(name='Öljylämmitys'),
            'ElectricityHeating': dict(name='Sähkölämmitys'),
            'GeothermalHeating': dict(name='Maalämpö'),
        }
    ),
    'Transportation': dict(
        name='Liikenne',
        subsectors={
            'Cars': dict(name='Henkilöautot'),
            'Trucks': dict(name='Kuorma-autot'),
            'OtherTransportation': dict(name='Muu liikenne'),
        }
    ),
    'ElectricityConsumption': dict(
        name='Kulutussähkö',
        subsectors={
            'SolarProduction': dict(name='Aurinkosähkö'),
        }
    ),
    'Waste': dict(name='Jätteiden käsittely'),
    'Industry': dict(name='Teollisuus ja työkoneet'),
    'Agriculture': dict(name='Maatalous'),
}
for key, val in SECTORS.items():
    if 'subsectors' not in val:
        val['subsectors'] = {}
    val['color'] = GHG_MAIN_SECTOR_COLORS[key]


TARGETS = {
    ('BuildingHeating', 'DistrictHeat'): (754.589056908339, 250.733198734865),
    ('BuildingHeating', 'OilHeating'): (16.1569293157852, 0.0),
    ('BuildingHeating', 'ElectricityHeating'): (51.0638673954148, 29.7160855925585),
    ('BuildingHeating', 'GeothermalHeating'): (0, 0),
    ('ElectricityConsumption', ''): (242.663770299608, 150.979312657901),
    # ('Liikenne', 262.55592574098, 229.655246625791),
    ('Transportation', 'Cars'): (128, 118.98),
    ('Transportation', 'Trucks'): (60, 49.47),
    ('Transportation', 'OtherTransportation'): (74.55, 61.2),
    ('Industry', ''): (3.23358058861613, 2.62034901128448),
    ('Waste', ''): (60.5886441012345, 50.6492489473935),
    ('Agriculture', ''): (0.637983301315191, 0.55519935555745),
}


def get_sector_by_path(path):
    if isinstance(path, str):
        path = tuple([path])

    next_metadata = SECTORS
    for sp in path:
        metadata = next_metadata[sp]
        next_metadata = metadata.get('subsectors', {})
    return metadata


@calcfunc(
    datasets=dict(
        ghg_emissions='jyrjola/hsy/pks_khk_paastot',
    ),
)
def prepare_emissions_dataset(datasets) -> pd.DataFrame:
    df = datasets['ghg_emissions']
    df = df[df.Kaupunki == 'Helsinki'].drop(columns='Kaupunki')
    df = df.set_index('Vuosi').copy()
    df = df.reset_index().groupby(['Vuosi', 'Sektori1', 'Sektori2', 'Sektori3'])['Päästöt'].sum().reset_index()

    df = df.rename(columns=dict(
        Sektori1='Sector1', Sektori2='Sector2', Sektori3='Sector3', Päästöt='Emissions', Vuosi='Year'
    ))

    sec1_renames = {val['name']: key for key, val in SECTORS.items()}
    sec1_renames['Lämmitys'] = 'BuildingHeating'
    sec1_renames['Sähkö'] = 'ElectricityConsumption'
    df['Sector1'] = df['Sector1'].map(lambda x: sec1_renames[x])

    sec2_renames = {}
    for sector in SECTORS.values():
        sec2_renames.update({val['name']: key for key, val in sector['subsectors'].items()})
    df['Sector2'] = df['Sector2'].map(lambda x: sec2_renames.get(x, ''))
    df['Sector3'] = df['Sector3'].map(lambda x: sec2_renames.get(x, ''))

    # Move transportation sectors one hierarchy level up
    df.loc[df.Sector1 == 'Transportation', 'Sector2'] = df['Sector3']

    df = df.groupby(['Year', 'Sector1', 'Sector2']).sum().reset_index()
    df.loc[(df.Sector1 == 'Transportation') & (df.Sector2 == ''), 'Sector2'] = 'OtherTransportation'
    df['Sector'] = list(zip(df.Sector1, df.Sector2))
    df = df.drop(columns=['Sector1', 'Sector2'])

    df = df.pivot(index='Year', columns='Sector', values='Emissions')

    df.columns = pd.MultiIndex.from_tuples(df.columns)
    return df


@calcfunc(
    variables=['target_year'],
    datasets=dict(),
    funcs=[
        prepare_emissions_dataset, predict_district_heating_emissions,
        predict_electricity_consumption_emissions,
        predict_cars_emissions, predict_geothermal_production,
    ],
)
def predict_emissions(variables, datasets):
    df = prepare_emissions_dataset()
    last_historical_year = df.index.max()

    for year in range(df.index.max() + 1, variables['target_year'] + 1):
        df.loc[year] = None

    subsector_map = {}
    for sec_name, sector in SECTORS.items():
        for subsector_name, subsector in sector['subsectors'].items():
            subsector_map[subsector_name] = dict(supersector=sec_name)

    """
    target_map = {}
    for key, val in TARGETS.items():
        if key in SECTORS:
            key = (key, None)
        else:
            key = (subsector_map[key]['supersector'], key)
        target_map[key] = val
    """

    df.loc[2030] = [TARGETS[key][0] for key in df.columns]
    df.loc[2035] = [TARGETS[key][1] for key in df.columns]
    df = df.interpolate()

    pdf = predict_district_heating_emissions()
    df.loc[df.index > last_historical_year, ('BuildingHeating', 'DistrictHeat')] = \
        pdf.loc[pdf.index > last_historical_year, 'NetEmissions']

    pdf = predict_electricity_consumption_emissions()
    df.loc[df.index > last_historical_year, ('ElectricityConsumption', '')] = \
        pdf.loc[pdf.index > last_historical_year, 'NetEmissions']

    pdf = predict_geothermal_production()
    df.loc[df.index > last_historical_year, ('BuildingHeating', 'GeothermalHeating')] = \
        pdf.loc[pdf.index > last_historical_year, 'Emissions']

    df[('ElectricityConsumption', 'SolarProduction')] = None

    pdf = predict_cars_emissions()
    df.loc[df.index > last_historical_year, ('Transportation', 'Cars')] = \
        pdf.loc[pdf.index > last_historical_year, 'Emissions']

    # FIXME: Plug other emission prediction models

    df['Forecast'] = False
    df.loc[df.index > last_historical_year, 'Forecast'] = True

    return df


if __name__ == '__main__':
    pd.set_option('display.max_rows', None)
    df = predict_emissions()
    print(df)
