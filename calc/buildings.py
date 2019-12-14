import pandas as pd
import scipy.stats

from . import calcfunc
from .population import get_adjusted_population_forecast


def generate_forecast_series(historical_series, year_until):
    s = historical_series
    start_year = s.index.min()
    res = scipy.stats.linregress(s.index, s)

    years = list(range(start_year, year_until + 1))
    predictions = pd.Series([res.intercept + res.slope * year for year in years], index=years)
    return predictions


@calcfunc(
    datasets=dict(
        buildings='jyrjola/aluesarjat/a01s_hki_rakennuskanta',
    )
)
def prepare_historical_building_area_dataset(datasets):
    df = datasets['buildings']
    df = df.loc[df.Alue == '091 Helsinki'].drop(columns='Alue')
    df = df.loc[df.Valmistumisvuosi != 'Yhteensä'].copy()
    df = df.rename(columns={'Käyttötarkoitus ja kerrosluku': 'Käyttötarkoitus'})
    df = df[~df['Käyttötarkoitus'].str.contains('yhteensä')]
    df = df[df['Käyttötarkoitus'] != 'Kaikki rakennukset']

    return df


@calcfunc(
    variables=dict(
        target_year='target_year',
    ),
    funcs=[prepare_historical_building_area_dataset, get_adjusted_population_forecast]
)
def generate_building_floor_area_forecast(variables):
    target_year = variables['target_year']

    df = prepare_historical_building_area_dataset()
    df = df.loc[df.Yksikkö == 'Kerrosala']
    building_total = df.groupby(['Käyttötarkoitus', 'Vuosi']).sum()\
        .unstack('Käyttötarkoitus')
    building_total.index = building_total.index.astype(int)
    building_total.columns = building_total.columns.get_level_values(1)

    pop_s = get_adjusted_population_forecast().Population
    # Replace negative population change with zero so that we don't
    # start bulldozing buildings.
    pop_diff = pop_s.diff().clip(lower=0).dropna()

    newly_built = building_total.diff().dropna()
    df = newly_built.div(pop_diff, axis=0).dropna()
    df = df.loc[df.index >= df.index.max() - 10]  # look at the last 10 years
    new_area_per_capita = df.mean()

    # Make the forecast of newly-built building net area by multiplying
    # the forecast of the yearly population increase by the amount of
    # new building area per capita.
    forecast_years = range(newly_built.index.max() + 1, target_year + 1)
    df = pd.DataFrame([new_area_per_capita] * len(forecast_years), index=forecast_years)
    building_forecast = df.multiply(pop_diff, axis=0).dropna()

    building_forecast.iloc[0] += building_total.iloc[-1]
    df = pd.concat([building_total, building_forecast.cumsum()], sort=True)

    df.index.name = 'Year'
    df['Forecast'] = False
    df.loc[df.index >= forecast_years[0], 'Forecast'] = True

    df['Asuinkerrostalot'] = df['Asuinkerrostalot alle 4 kerrosta'] + df['Asuinkerrostalot 4 + kerrosta']
    df = df.drop(columns=['Asuinkerrostalot alle 4 kerrosta', 'Asuinkerrostalot 4 + kerrosta'])

    return df


if __name__ == '__main__':
    print(generate_building_floor_area_forecast())
