from datetime import datetime

import pandas as pd
import scipy.stats

from . import calcfunc
from .buildings import generate_building_floor_area_forecast


@calcfunc(
    datasets=dict(
        energy_use='jyrjola/ymparistotilastot/e12_helsingin_kaukolammon_sahkonkulutus',
        building_stock='jyrjola/aluesarjat/a01s_hki_rakennuskanta'
    ),
    variables=['municipality_name', 'target_year', 'district_heating_existing_building_efficiency_change']
)
def generate_heat_use_per_net_area_forecast_existing_buildings(variables, datasets):
    assert variables['municipality_name'] == 'Helsinki'

    bdf = datasets['building_stock'].query('Alue == "091 Helsinki" & Yksikkö == "Kerrosala"')
    bdf = bdf.loc[bdf['Käyttötarkoitus ja kerrosluku'] == "Kaikki rakennukset"]
    net_area = bdf.query('Valmistumisvuosi == "Yhteensä"').set_index('Vuosi').value

    muni_energy_use = datasets['energy_use'].query('Kunta == "Helsinki" & Energiamuoto == "Kaukolämpö"')\
        .drop(columns=['Energiamuoto', 'Kunta'])
    edf = muni_energy_use
    edf = edf.loc[edf.Sektori.isin(['Ominaiskulutus sääkorjaamaton (kWh/m3)', 'Ominaiskulutus sääkorjattu (kWh/m3)'])]
    edf = edf.pivot(index='Vuosi', columns='Sektori', values='value').dropna()
    heating_need_correction_factor = edf['Ominaiskulutus sääkorjattu (kWh/m3)'] / edf['Ominaiskulutus sääkorjaamaton (kWh/m3)']

    heat_use = muni_energy_use.query('Sektori == "Kulutus yhteensä (GWh)"').set_index('Vuosi').value
    heat_use *= 1000000  # convert to kWh

    heat_use_per_net_area = heat_use.div(net_area, axis='index').mul(heating_need_correction_factor, axis='index').dropna()
    heat_use_per_net_area.name = 'HeatUsePerNetArea'

    df = pd.DataFrame(heat_use_per_net_area)
    df['Forecast'] = False
    df.index = df.index.astype(int)
    df = df.reindex(range(df.index.min(), variables['target_year'] + 1))
    df.loc[df.Forecast != False, 'Forecast'] = True

    change_perc = variables['district_heating_existing_building_efficiency_change']
    df['HeatUsePerNetArea'] = df['HeatUsePerNetArea'].fillna(heat_use_per_net_area.iloc[-1])
    first_forecast_year = df[df.Forecast].index.min()
    for year in df[df.Forecast].index:
        factor = (1 + (change_perc / 100)) ** (year - first_forecast_year + 1)
        df.loc[year, 'HeatUsePerNetArea'] *= factor

    return df


@calcfunc(
    variables=['target_year', 'district_heating_new_building_efficiency_change']
)
def generate_heat_use_per_net_area_forecast_new_buildings(variables):
    target_year = variables['target_year']

    heat_use_per_net_area = 95
    start_year = 2017
    years = range(start_year, target_year + 1)

    vals = []
    change_perc = variables['district_heating_new_building_efficiency_change']

    for year in years:
        factor = (1 + (change_perc / 100)) ** (year - start_year + 1)
        vals.append(heat_use_per_net_area * factor)

    return pd.Series(vals, index=years)


@calcfunc(
    datasets=dict(
        energy_use='jyrjola/ymparistotilastot/e12_helsingin_kaukolammon_sahkonkulutus',
    ),
    variables=['target_year'],
    funcs=[
        generate_building_floor_area_forecast,
        generate_heat_use_per_net_area_forecast_existing_buildings,
        generate_heat_use_per_net_area_forecast_new_buildings
    ]
)
def predict_district_heat_consumption(variables, datasets):
    net_area = generate_building_floor_area_forecast()
    existing_heating_factor = generate_heat_use_per_net_area_forecast_existing_buildings()
    future_heating_factor = generate_heat_use_per_net_area_forecast_new_buildings()

    heat_use = datasets['energy_use'].query('Kunta == "Helsinki" & Energiamuoto == "Kaukolämpö"')\
        .drop(columns=['Energiamuoto', 'Kunta']).query('Sektori == "Kulutus yhteensä (GWh)"')\
        .set_index('Vuosi').value
    heat_use.index = heat_use.index.astype(int)
    heat_use *= 1000000  # convert to kWh

    forecast = net_area.pop('Forecast')
    net_area = net_area.sum(axis=1) / 1000  # convert to thousand m2
    net_area.name = 'NetArea'
    df = pd.DataFrame(net_area)
    df['Forecast'] = forecast

    df['ExistingBuildingHeatUsePerNetArea'] = existing_heating_factor.HeatUsePerNetArea
    df['NewBuildingHeatUsePerNetArea'] = future_heating_factor

    last_measured_area = df.loc[~df.Forecast, 'NetArea'].iloc[-1]
    df.loc[df.Forecast, 'NewBuildingNetArea'] = df.NetArea - last_measured_area
    df.NewBuildingNetArea = df.NewBuildingNetArea.fillna(0)
    df['ExistingBuildingNetArea'] = df.NetArea - df.NewBuildingNetArea
    df['BuiltPerYear'] = df.NewBuildingNetArea.diff()
    df['NewBuildingHeatUse'] = df['BuiltPerYear'].mul(future_heating_factor, axis=0) / 1000
    df['NewBuildingHeatUse'] = df.NewBuildingHeatUse.cumsum().fillna(0)

    df['ExistingBuildingHeatUse'] = heat_use / 1000000  # kWh to GWh
    forecast = df.ExistingBuildingNetArea.mul(existing_heating_factor.HeatUsePerNetArea, axis=0) / 1000
    forecast *= 0.95   # FIXME: magic correction factor (weather warming?), fix this later!
    df.loc[df.Forecast, 'ExistingBuildingHeatUse'] = forecast

    df['TotalHeatConsumption'] = df.ExistingBuildingHeatUse + df.NewBuildingHeatUse

    return df


if __name__ == '__main__':
    predict_district_heat_consumption()
