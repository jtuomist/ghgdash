import numpy as np
import pandas as pd
import scipy.stats
from . import calcfunc
from .buildings import generate_building_floor_area_forecast

@calcfunc(
    datasets=dict(
        building_potential='jyrjola/hsy/buildings',
    ),
    variables=[
        'target_year', 'municipality_name',
        'solar_power_existing_buildings_percentage',
        'solar_power_new_buildings_percentage',
        'yearly_pv_energy_production_kwh_wp'
    ],
    funcs=[generate_building_floor_area_forecast],
)
def generate_solar_power_forecast(datasets, variables):
    PAST_VALUES = (221, 296, 371, 851, 2343, 3724, 5108)
    START_YEAR = 2012
    target_year = variables['target_year']
    muni_name = variables['municipality_name']
    pv_kwh_wp = variables['yearly_pv_energy_production_kwh_wp']

    building_df = datasets['building_potential']
    ka_df = building_df.query(f'kuntanimi == "{muni_name}" & kerrosala > 0').copy()
    ka_df = ka_df.groupby(['kayt_luok'])[['elec_kwh_v', 'kerrosala']].sum()
    ka_df['kwh_per_ka_v'] = ka_df['elec_kwh_v'] / ka_df['kerrosala']
    max_potential = ka_df.sum()['elec_kwh_v'] / pv_kwh_wp / 1000000 #kWh -> MWp
    max_potential = max_potential * variables['solar_power_existing_buildings_percentage']/100

    df = pd.DataFrame(
        [x/1000.0 for x in PAST_VALUES],
        index=range(START_YEAR, START_YEAR + len(PAST_VALUES)),
        columns=['SolarPowerExisting']
    )

    df['Forecast'] = False
    df = df.reindex(pd.Index(range(START_YEAR, target_year + 1)))
    df.index.name = 'Year'
    df.Forecast = df.Forecast.fillna(True)

    df.loc[target_year, 'SolarPowerExisting'] = max_potential
    df['SolarPowerExisting'] = df['SolarPowerExisting'].interpolate()

    # Construct estimate of solar power potential available in new buildings
    # by using floor area forecast data and the current potential based on
    # floor area. Do the calculations per building category.
    new_df = generate_building_floor_area_forecast()
    new_df = new_df.query('Forecast').drop(columns='Forecast')
    new_df = new_df.diff()
    for col in new_df.columns:
        # Map building types from building floor area forecast to solar power data
        lcol = col
        if col == "Muu tai tuntematon käyttötarkoitus":
            lcol = "Muut rakennukset"
        elif col == "Rivi- tai ketjutalot":
            lcol = "Erilliset pientalot"
        kwh_per_pa = ka_df.loc[lcol, 'kwh_per_ka_v']
        new_df[col] *= kwh_per_pa / pv_kwh_wp / 1000000 #kWh -> MWp

    new_df['SolarPowerNew'] = new_df.sum(axis=1).cumsum() * variables['solar_power_new_buildings_percentage']/100
    df = pd.merge(df, new_df['SolarPowerNew'], on='Year', how="left")
    df.SolarPowerNew = df.SolarPowerNew.fillna(0.0)

    # Sum production
    df['SolarPowerAll'] = df['SolarPowerNew'] + df['SolarPowerExisting']

    return df
