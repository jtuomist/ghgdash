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


if __name__ == '__main__':
    print(generate_electricity_consumption_forecast())
