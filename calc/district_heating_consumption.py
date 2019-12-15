import pandas as pd

from . import calcfunc
from .buildings import (
    generate_building_floor_area_forecast,
    generate_heat_use_per_net_area_forecast_existing_buildings,
    generate_heat_use_per_net_area_forecast_new_buildings
)


@calcfunc(
    datasets=dict(
        energy_use='jyrjola/ymparistotilastot/e12_helsingin_kaukolammon_sahkonkulutus',
    ),
    variables=['target_year'],
    funcs=[
        generate_building_floor_area_forecast,
        generate_heat_use_per_net_area_forecast_existing_buildings,
        generate_heat_use_per_net_area_forecast_new_buildings,
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
