import pandas as pd
from . import calcfunc


@calcfunc(
    variables=['municipality_name'],
    datasets=dict(
        pop_forecast='jyrjola/aluesarjat/hginseutu_va_ve01_vaestoennuste_pks',
    )
)
def get_population_forecast(variables, datasets):
    FORECAST_MADE_YEAR = 2018

    df = datasets['pop_forecast']
    df = df.loc[df.Alue == variables['municipality_name']]
    df = df.loc[df.Laadintavuosi == 'Laadittu %s' % FORECAST_MADE_YEAR]
    df = df.loc[df.Vaihtoehto == 'Perusvaihtoehto']
    df = df.loc[df.Sukupuoli == 'Molemmat sukupuolet']
    df = df.copy()

    df.Vuosi = df.Vuosi.astype(int)
    df.value = df.value.astype(int)
    df.loc[df.Vuosi <= FORECAST_MADE_YEAR, 'Forecast'] = False
    df.loc[df.Vuosi > FORECAST_MADE_YEAR, 'Forecast'] = True
    df = df.set_index('Vuosi')
    df = df.loc[df.Ikä == 'Väestö yhteensä'][['value', 'Forecast']].copy()
    df.rename(columns=dict(value='Population'), inplace=True)
    return df


@calcfunc(
    variables=['population_forecast_correction', 'target_year'],
    funcs=[get_population_forecast]
)
def get_adjusted_population_forecast(variables):
    correction_perc = variables['population_forecast_correction']
    target_year = variables['target_year']

    df = get_population_forecast()
    df = df[df.index <= target_year].copy()
    forecast = df.loc[df.Forecast]
    n_years = forecast.index.max() - forecast.index.min()
    base = (1 + (correction_perc / 100)) ** (1 / n_years)
    multipliers = [base ** year for year in range(n_years + 1)]
    m_series = pd.Series(multipliers, index=forecast.index)
    df.loc[df.Forecast, 'Population'] *= m_series
    df.Population = df.Population.astype(int)
    return df


if __name__ == '__main__':
    print(get_adjusted_population_forecast())
