from datetime import timedelta
import numpy as np
import pandas as pd
import scipy.stats
from . import calcfunc
from .population import get_adjusted_population_forecast


def generate_electricity_emission_factor_forecast():
    PAST_VALUES = (270, 227, 167, 200, 173, 135, 146, 131)
    START_YEAR = 2010

    df = pd.DataFrame(
        PAST_VALUES,
        index=range(START_YEAR, START_YEAR + len(PAST_VALUES)),
        columns=['EmissionFactor']
    )

    df['Forecast'] = False
    df = df.reindex(pd.Index(range(START_YEAR, 2035 + 1)))
    df.Forecast = df.Forecast.fillna(True)
    df.loc[2030, 'EmissionFactor'] = 70  # g CO2e/kWh
    df.loc[2035, 'EmissionFactor'] = 45  # g CO2e/kWh

    df['EmissionFactor'] = df['EmissionFactor'].interpolate()

    return df


@calcfunc(
    variables=['target_year', 'municipality_name', 'electricity_consumption_forecast_adjustment'],
    datasets=dict(
        energy_consumption='jyrjola/ymparistotilastot/e12_helsingin_kaukolammon_sahkonkulutus'
    ),
    funcs=[get_adjusted_population_forecast],
)
def generate_electricity_consumption_forecast(variables, datasets):
    pop_df = get_adjusted_population_forecast()
    target_year = variables['target_year']

    el_df = datasets['energy_consumption']
    muni_name = variables['municipality_name']
    el_df = el_df.query(f'Kunta == "{muni_name}" & Energiamuoto == "Sähkö" & Sektori == "Kulutus yhteensä (GWh)"').copy()
    el_df['Vuosi'] = el_df.Vuosi.astype(int)
    el_df = el_df.set_index('Vuosi')['value']

    el_per_capita = (el_df / pop_df['Population']).dropna()
    el_per_capita *= 1000000  # GWh to kWh

    # Do a logarithmic regression
    s = np.log(el_per_capita)

    rs = s.loc[s.index >= 2007]
    res = scipy.stats.linregress(rs.index, rs)

    last_year = s.index.max()
    last_val = s.loc[last_year]
    for year in range(1, target_year - last_year + 1):
        s.loc[last_year + year] = last_val + res.slope * year

    s = np.exp(s)

    # Convert to electricity consumption
    el_s = pop_df['Population'] * s / 1000000
    el_s.name = 'ElectricityConsumption'
    df = pd.DataFrame(el_s)
    df['Forecast'] = False
    df.loc[df.index > last_year, 'Forecast'] = True
    df = df.dropna()
    return df


@calcfunc(
    datasets=dict(
        et_hourly='jyrjola/energiateollisuus/electricity_production_hourly',
        et_fuels='jyrjola/energiateollisuus/electricity_production_fuels'
    ),
    variables=['bio_is_emissionless'],
)
def calculate_electricity_production_emissions(datasets, variables):
    et_fuels = datasets['et_fuels']
    df = et_fuels.copy()
    df['FuelEmissionFactor'] = df.Fuel.map({
        'Bio': 0 if variables['bio_is_emissionless'] else 112,
        'Coal': 106.0 * 0.99,
        'Oil': 79.2,
        'Natural gas': 55.3,
        'Peat': 107.6 * 0.99,
        'Other': 31.8 * 0.99
    })
    df['Emissions'] = df['FuelEmissionFactor'] * df['FuelUse'] / 1000

    df = df.groupby(['Date', 'Method'])[['Production', 'Emissions']].sum()
    df['EmissionFactor'] = df['Emissions'] / df['Production'] * 1000
    df = df['EmissionFactor'].unstack('Method')
    df.index += timedelta(days=14)
    df = df.resample('h').mean().interpolate()
    df.index = df.index.tz_localize('Europe/Helsinki', nonexistent='NaT', ambiguous='NaT')
    df = df.loc[df.index.notnull()]

    return df


@calcfunc(
    datasets=dict(
        et_hourly='jyrjola/energiateollisuus/electricity_production_hourly',
    ),
    funcs=[calculate_electricity_production_emissions]
)
def calculate_electricity_supply_emission_factor(datasets):
    df = datasets['et_hourly'].copy()

    hourly_emission_factors = calculate_electricity_production_emissions()
    chp_emissions = df[['CHP-Industry', 'CHP-District heating']].mul(hourly_emission_factors['CHP'], axis=0).dropna()
    separate_thermal_emissions = df['Separate Thermal Power'].mul(hourly_emission_factors['Separate Thermal'], axis=0).dropna()

    supply_emissions = chp_emissions.sum(axis=1) + separate_thermal_emissions
    df['Emissions'] = supply_emissions
    df['EmissionFactor'] = supply_emissions.div(df['Production'] + df['Import'], axis=0)
    return df


if __name__ == '__main__':
    print(calculate_electricity_supply_emission_factor())
