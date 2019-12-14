from datetime import datetime

import pandas as pd
import scipy.stats

from . import calcfunc
from .buildings import generate_building_floor_area_forecast
from .district_heating_consumption import (
    generate_heat_use_per_net_area_forecast_existing_buildings,
    generate_heat_use_per_net_area_forecast_new_buildings
)
from .district_heating import calc_district_heating_unit_emissions_forecast
from .electricity import predict_electricity_emission_factor


@calcfunc(
    datasets=dict(
        energy_use='jyrjola/ymparistotilastot/e12_helsingin_kaukolammon_sahkonkulutus',
    ),
    variables=['target_year', 'geothermal_heat_pump_cop'],
    funcs=[
        generate_building_floor_area_forecast,
        generate_heat_use_per_net_area_forecast_existing_buildings,
        calc_district_heating_unit_emissions_forecast,
        predict_electricity_emission_factor
    ]
)
def predict_district_heat_consumption(variables, datasets):
    target_year = variables['target_year']
    yearly_renovation = 0.02
    new_building_geothermal_percentage = 0.5

    old_heat_use_df = generate_heat_use_per_net_area_forecast_existing_buildings()
    new_heat_use_df = generate_heat_use_per_net_area_forecast_new_buildings()
    building_df = generate_building_floor_area_forecast()

    DH_PERCENTAGE = 0.85

    df = building_df.copy()
    hist_df = df[~df.Forecast]
    last_historical_year = hist_df.index.max()

    last_area = df.loc[last_historical_year]
    dh_area = last_area.sum() * DH_PERCENTAGE

    dh_left = dh_area.copy()
    geo = pd.Series()
    for year in range(last_historical_year + 1, target_year + 1):
        dh_left *= (1 - yearly_renovation)
        geo.loc[year] = float(dh_area - dh_left)

    df = pd.DataFrame()
    df['GeoBuildingNetAreaOld'] = geo
    df['GeoEnergyProducedOld'] = df['GeoBuildingNetAreaOld'] * old_heat_use_df['HeatUsePerNetArea']

    bdf = building_df.loc[building_df.index >= last_historical_year].drop(columns='Forecast').diff()
    bdf = bdf.sum(axis=1)
    new_heat_use = bdf * new_heat_use_df
    df['NewBuildingHeatUse'] = bdf * new_heat_use_df
    df['NewBuildingHeatUse'] = df['NewBuildingHeatUse'].cumsum()
    df['GeoEnergyProducedNew'] = df['NewBuildingHeatUse'] * new_building_geothermal_percentage
    df['GeoEnergyProduced'] = df['GeoEnergyProducedNew'] + df['GeoEnergyProducedOld']

    df['ElectricityUse'] = df['GeoEnergyProduced'] / variables['geothermal_heat_pump_cop']
    edf = predict_electricity_emission_factor()
    df['Emissions'] = df['ElectricityUse'] * edf['EmissionFactor']
    dhdf, _ = calc_district_heating_unit_emissions_forecast()
    df['EmissionReductions'] = df['GeoEnergyProduced'] * dhdf['Emission factor']
    df['NetEmissions'] = df['Emissions'] - df['EmissionReductions']

    GEO_ENERGY_FROM_500M = 69300  # kWh
    GEO_ENERGY_FROM_200M = 22656  # kWh
    boreholes = df['GeoEnergyProduced'] / GEO_ENERGY_FROM_500M
    boreholes[last_historical_year] = 0
    boreholes = boreholes.sort_index()
    df['GeothermalBoreholesPerYear'] = boreholes.diff().fillna(0)
    # assume grid formation
    df['BoreholeAreaNeeded'] = (boreholes * 25**2) / 1000000  # m2 -> km2

    return df


if __name__ == '__main__':
    predict_district_heat_consumption()


