import math
import pandas as pd
import scipy.stats
from . import calcfunc
from .population import get_adjusted_population_forecast
from .electricity import predict_electricity_emission_factor

LIPASTO_START_YEAR = 2018


@calcfunc(
    datasets=dict(
        emissions='jyrjola/lipasto/emissions_by_municipality',
    ),
    variables=[
        'target_year', 'municipality_name',
        'cars_mileage_adjustment'
    ],
    funcs=[get_adjusted_population_forecast],
)
def generate_cars_mileage_forecast(datasets, variables):
    emissions = datasets['emissions']
    target_year = variables['target_year']
    mileage_adj = variables['cars_mileage_adjustment']

    emissions = emissions[emissions.Year == LIPASTO_START_YEAR].drop(columns='Year')

    muni = emissions.set_index(['Municipality', 'Vehicle'])
    mil_df = muni.xs((variables['municipality_name'], 'Cars'))[['Road', 'Mileage']].set_index('Road')

    pop_df = get_adjusted_population_forecast()
    population_baseline = pop_df.loc[LIPASTO_START_YEAR, 'Population']

    df = pd.DataFrame(
        index=range(LIPASTO_START_YEAR, target_year + 1),
        columns=['Mileage', 'Highways', 'Urban']
    )
    df.index.name = 'Year'

    n_years = df.index.max() - df.index.min()
    base = (1 + (mileage_adj / 100)) ** (1 / n_years)
    mileage_adj = pd.Series([base ** year for year in range(n_years + 1)], index=df.index)

    df['Mileage'] = 0
    for road in ('Highways', 'Urban'):
        df[road] = mil_df.loc[road, "Mileage"] * pop_df['Population'] / population_baseline * mileage_adj / 1000000
        df['Mileage'] += df[road]

    df['Forecast'] = True
    df.loc[LIPASTO_START_YEAR, 'Forecast'] = False
    return df


def bass_diffuse(t, p, q):
    e1 = math.e ** (-(p + q) * t)
    res = ((p + q) ** 2) / p
    res *= e1 / ((1 + q / p * e1) ** 2)
    return res


def calculate_bev_share(m, start_share, n_years):
    bev_share = start_share
    for t in range(n_years):
        bev_share *= 1 + bass_diffuse(t, 0.2, 0.2) * m
    return bev_share


def estimate_mileage_ratios(df, year, bev_target_share, target_year):
    df = df.copy()
    # Assume BEV share is increasing according to the Bass diffusion model
    # and that increase in share comes equally out of petrol and diesel engines
    # starting from the most polluting engine classes.
    bev = df.loc['electric']
    bev_share_start = bev_share = bev['EURO 6']

    def estimate_bass_m(m):
        return abs(bev_target_share - calculate_bev_share(m, bev_share_start, target_year - LIPASTO_START_YEAR))
    m = scipy.optimize.minimize_scalar(estimate_bass_m).x

    bev_share = bev['EURO 6'] = calculate_bev_share(m, bev_share_start, year - LIPASTO_START_YEAR)

    share_change = bev_share - bev_share_start
    sums = df.sum(axis='columns')
    diesel_share = sums['diesel'] / (sums['diesel'] + sums['gasoline'])
    share_left = dict(diesel=share_change * diesel_share)
    share_left['gasoline'] = share_change - share_left['diesel']

    for i in range(0, 6 + 1):
        key = 'EURO %d' % i
        for eng in ('diesel', 'gasoline'):
            if not share_left[eng]:
                continue

            val = df.loc[eng][key]
            decrease = min(val, share_left[eng])
            df.loc[eng][key] -= decrease
            share_left[eng] -= decrease

    return df


def estimate_bev_unit_emissions(unit_emissions, kwh_emissions):
    energy_consumption = (
        ('Highways', 0.2),   # kWh/km
        ('Urban', 0.17)
    )
    rows = []
    for road_type, kwh in energy_consumption:
        rows.append({
            "Engine": 'electric',
            "Road": road_type,
            "Car year": 2018,
            "CO2e": kwh * kwh_emissions,
            "Class": "EURO 6"
        })
    return unit_emissions.copy().append(pd.DataFrame(rows), ignore_index=True, sort=True)


def calculate_co2e_per_engine_type(mileage, ratios, unit_emissions):
    roads = ('Urban', 'Highways')
    df = pd.concat([ratios * mileage[road] * 1000000 for road in roads], keys=roads, names=['Road'])
    out = df * unit_emissions
    out /= 1000000000  # convert to kt (CO2e)
    return out


@calcfunc(
    datasets=dict(
        mileage_per_engine_type='jyrjola/lipasto/mileage_per_engine_type',
        car_unit_emissions='jyrjola/lipasto/car_unit_emissions',
    ),
    variables=[
        'target_year', 'municipality_name',
        'cars_bev_percentage'
    ],
    funcs=[
        predict_electricity_emission_factor,
        generate_cars_mileage_forecast,
    ]
)
def predict_cars_emissions(datasets, variables):
    target_year = variables['target_year']
    bev_percentage = variables['cars_bev_percentage']

    mileage_per_engine_type = datasets['mileage_per_engine_type']
    mileage_share_per_engine_type = mileage_per_engine_type.set_index(['Vehicle', 'Engine']).drop(columns='Sum')

    mil_df = generate_cars_mileage_forecast()

    car_unit_emissions = datasets['car_unit_emissions'].set_index(['Engine', 'Road'])
    elec_df = predict_electricity_emission_factor()
    share_df = mileage_share_per_engine_type.copy().xs('Cars')

    df = pd.DataFrame(
        index=range(LIPASTO_START_YEAR, target_year + 1),
        columns=['Forecast', 'electric', 'gasoline', 'diesel', 'Emissions']
    )
    df.index.name = 'Year'
    df['Forecast'] = True
    df.loc[LIPASTO_START_YEAR, 'Forecast'] = False

    # Prepare unit emissions dataset
    for year in range(LIPASTO_START_YEAR, target_year+1):
        # Estimate mileage ratio shares between engine types
        share = estimate_mileage_ratios(share_df, year, bev_percentage / 100.0, target_year)
        shares = share.sum(axis='columns') * 100
        for col in ['electric', 'gasoline', 'diesel']:
            df.loc[year, col] = shares[col]

        # Estimate emissions per km per engine type
        unit_df = car_unit_emissions.copy().reset_index()
        unit_df = estimate_bev_unit_emissions(unit_df, elec_df.loc[year]['EmissionFactor'])
        unit_df.set_index(['Engine', 'Road'], inplace=True)
        unit_df = unit_df.groupby(['Road', 'Engine', 'Class']).mean()['CO2e'].unstack('Class')

        # Calculate emissions for the year
        co2e = calculate_co2e_per_engine_type(mil_df.loc[year], share, unit_df)
        co2e = co2e.sum(level='Engine').sum(axis='columns')
        df.loc[year, "Emissions"] = co2e.sum()

    return df
