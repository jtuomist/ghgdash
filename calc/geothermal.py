import numpy as np
import pandas as pd

from . import calcfunc
from .buildings import (
    generate_building_floor_area_forecast,
    generate_heat_use_per_net_area_forecast_existing_buildings,
    generate_heat_use_per_net_area_forecast_new_buildings
)
from .district_heating import calc_district_heating_unit_emissions_forecast
from .electricity import predict_electricity_emission_factor
from utils.data import find_consecutive_start


# Calculate the yearly production capacity of boreholes depending
# on the depth of the borehole. Production in kWh/year.
BOREHOLE_PRODUCTION = [
    (1, 38),
    (10, 501),
    (50, 4680),
    (100, 10278),
    (200, 22656),
    (300, 36612),
    (500, 69252),
    (750, 118922),
    (1000, 178448),
]

get_borehole_production = np.poly1d(np.polyfit(
    [x[0] for x in BOREHOLE_PRODUCTION], [x[1] for x in BOREHOLE_PRODUCTION], deg=5
))


@calcfunc(
    datasets=dict(
        ghg_emissions='jyrjola/hsy/pks_khk_paastot',
    ),
)
def get_historical_production(datasets):
    df = datasets['ghg_emissions']
    df = df[df.Kaupunki == 'Helsinki'].drop(columns='Kaupunki')
    df = df[df.Sektori2 == 'Maalämpö'].groupby(['Vuosi', 'Sektori2']).sum()
    df = df.reset_index().set_index('Vuosi')
    return df['Energiankulutus']


@calcfunc(
    datasets=dict(
        energy_use='jyrjola/ymparistotilastot/e12_helsingin_kaukolammon_sahkonkulutus',
    ),
    variables=[
        'target_year', 'geothermal_heat_pump_cop',
        'geothermal_existing_building_renovation',
        'geothermal_new_building_installation_share',
        'geothermal_borehole_depth',
    ],
    funcs=[
        generate_building_floor_area_forecast,
        generate_heat_use_per_net_area_forecast_existing_buildings,
        calc_district_heating_unit_emissions_forecast,
        predict_electricity_emission_factor,
        get_historical_production
    ]
)
def predict_geothermal_production(variables, datasets):
    target_year = variables['target_year']
    yearly_renovation = variables['geothermal_existing_building_renovation'] / 100
    new_building_geothermal_percentage = variables['geothermal_new_building_installation_share'] / 100

    old_heat_use_df = generate_heat_use_per_net_area_forecast_existing_buildings()
    new_heat_use_df = generate_heat_use_per_net_area_forecast_new_buildings()
    building_df = generate_building_floor_area_forecast()
    hist_geo = get_historical_production()

    DH_PERCENTAGE = 0.85

    df = building_df.copy()
    hist_df = df[~df.Forecast]
    last_historical_year = hist_geo.index.max()

    last_area = df.loc[last_historical_year]
    dh_area = last_area.sum() * DH_PERCENTAGE

    dh_left = dh_area.copy()
    geo = pd.Series()
    for year in range(last_historical_year + 1, target_year + 1):
        dh_left *= (1 - yearly_renovation)
        geo.loc[year] = float(dh_area - dh_left)

    df = pd.DataFrame()
    df['GeoBuildingNetAreaExisting'] = geo
    s = df['GeoBuildingNetAreaExisting'] * old_heat_use_df['HeatUsePerNetArea'] / 1000000  # kWh -> GWh
    df['GeoEnergyProductionExisting'] = s

    bdf = building_df.loc[building_df.index >= last_historical_year]
    bdf = bdf.drop(columns='Forecast').sum(axis=1)
    bdf = bdf.diff().dropna()

    df['GeoBuildingNetAreaNew'] = (bdf * new_building_geothermal_percentage).cumsum()
    df['GeoEnergyProductionNew'] = df['GeoBuildingNetAreaNew'] * new_heat_use_df / 1000000  # kWh -> GWh

    df['GeoBuildingNetAreaNew'] /= 1000000
    df['GeoBuildingNetAreaExisting'] /= 1000000

    ep = df['GeoEnergyProductionExisting']
    ep = hist_geo.append(ep).sort_index()
    start_year = find_consecutive_start(hist_geo.index)
    df = df.reindex(range(start_year, df.index.max() + 1))
    df['GeoEnergyProductionExisting'] = ep
    df['GeoEnergyProduction'] = df['GeoEnergyProductionNew'].fillna(0) + df['GeoEnergyProductionExisting']

    df['ElectricityUse'] = df['GeoEnergyProduction'] / variables['geothermal_heat_pump_cop']
    edf = predict_electricity_emission_factor()
    df['Emissions'] = df['ElectricityUse'] * edf['EmissionFactor'] / 1000
    dhdf, _ = calc_district_heating_unit_emissions_forecast()
    df['EmissionReductions'] = df['GeoEnergyProduction'] * dhdf['Emission factor'] / 1000
    df['NetEmissions'] = df['Emissions'] - df['EmissionReductions']

    production_per_hole = get_borehole_production(variables['geothermal_borehole_depth'])

    boreholes = df['GeoEnergyProduction'] * 1000000 / production_per_hole
    boreholes[last_historical_year] = 0
    boreholes = boreholes.sort_index()
    df['BoreholesPerYear'] = boreholes.diff().fillna(0)
    # assume grid formation
    df['BoreholeAreaNeeded'] = (boreholes * 25**2) / 1000000  # m2 -> km2

    df['Forecast'] = False
    df.loc[df.index > last_historical_year, 'Forecast'] = True

    return df


if __name__ == '__main__':
    #get_historical_production()
    predict_geothermal_production()
