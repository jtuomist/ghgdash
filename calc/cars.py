import math
import pandas as pd
import scipy.stats
from . import calcfunc
from .population import get_adjusted_population_forecast
from .electricity import predict_electricity_emission_factor


@calcfunc(
    datasets=dict(
        emissions='jyrjola/lipasto/emissions_by_municipality',
    ),
    variables=[
        'municipality_name'
    ]
)
def prepare_car_emissions_dataset(datasets, variables):
    df = datasets['emissions']
    df = df[df.Municipality == 'Helsinki'].copy()
    df.Vehicle = df.Vehicle.astype('category')
    df.Road = df.Road.astype('category')
    return df


@calcfunc(
    variables=[
        'target_year', 'municipality_name', 'cars_mileage_per_resident_adjustment'
    ],
    funcs=[get_adjusted_population_forecast, prepare_car_emissions_dataset],
)
def predict_cars_mileage(variables):
    target_year = variables['target_year']
    mileage_adj = variables['cars_mileage_per_resident_adjustment']

    df = prepare_car_emissions_dataset()
    df = df.loc[df.Vehicle == 'Cars', ['Year', 'Road', 'Mileage', 'CO2e']].set_index('Year')
    df = df.pivot(columns='Road', values='Mileage')
    df.columns = df.columns.astype(str)
    df['Forecast'] = False
    last_historical_year = df.index.max()
    df = df.reindex(range(df.index.min(), target_year + 1))
    pop_df = get_adjusted_population_forecast()
    df['Population'] = pop_df['Population']
    df['UrbanPerResident'] = df['Urban'] / df['Population']
    df['HighwaysPerResident'] = df['Highways'] / df['Population']
    df.loc[df.Forecast.isna(), 'Forecast'] = True
    for road in ('Highways', 'Urban'):
        s = df[road + 'PerResident'].copy()
        target_per_resident = s.loc[last_historical_year] * (1 + (mileage_adj / 100))
        s.loc[target_year] = target_per_resident
        s = s.interpolate()
        df.loc[df.Forecast, road + 'PerResident'] = s
        df.loc[df.Forecast, road] = df[road + 'PerResident'] * df['Population']

    df['Mileage'] = df['Highways'] + df['Urban']
    df['PerResident'] = df['UrbanPerResident'] + df['HighwaysPerResident']

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


def estimate_mileage_ratios(df, start_year, year, bev_target_share, target_year):
    df = df.copy()
    # Assume BEV share is increasing according to the Bass diffusion model
    # and that increase in share comes equally out of petrol and diesel engines
    # starting from the most polluting engine classes.
    bev = df.loc['electric']
    bev_share_start = bev_share = bev['EURO 6']

    def estimate_bass_m(m):
        return abs(bev_target_share - calculate_bev_share(m, bev_share_start, target_year - start_year))
    m = scipy.optimize.minimize_scalar(estimate_bass_m).x

    bev_share = bev['EURO 6'] = calculate_bev_share(m, bev_share_start, year - start_year)

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
    out /= 1000000000  # convert to t (CO2e)
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
        predict_cars_mileage,
        prepare_car_emissions_dataset
    ]
)
def predict_cars_emissions(datasets, variables):
    target_year = variables['target_year']
    bev_percentage = variables['cars_bev_percentage']

    mileage_per_engine_type = datasets['mileage_per_engine_type']
    mileage_share_per_engine_type = mileage_per_engine_type.set_index(['Vehicle', 'Engine']).drop(columns='Sum')

    df = prepare_car_emissions_dataset()
    df = df.loc[df.Vehicle == 'Cars', ['Year', 'CO2e', 'Road']].set_index('Year')
    emissions_df = df.pivot(values='CO2e', columns='Road')

    df = predict_cars_mileage()
    for road in ('Highways', 'Urban'):
        df[road + 'Emissions'] = emissions_df[road] / 1000  # -> kt

    car_unit_emissions = datasets['car_unit_emissions'].set_index(['Engine', 'Road'])
    elec_df = predict_electricity_emission_factor()
    share_df = mileage_share_per_engine_type.copy().xs('Cars')

    start_year = df[~df.Forecast].index.max()

    # Prepare unit emissions dataset
    for year in range(start_year, target_year + 1):
        # Estimate mileage ratio shares between engine types
        share = estimate_mileage_ratios(share_df, start_year, year, bev_percentage / 100.0, target_year)
        shares = share.sum(axis='columns')
        for col in ['electric', 'gasoline', 'diesel']:
            df.loc[year, col] = shares[col]

        # Do not calculate emissions for the year we have actual data on
        if year == start_year:
            continue

        # Estimate emissions per km per engine type
        unit_df = car_unit_emissions.copy().reset_index()
        unit_df = estimate_bev_unit_emissions(unit_df, elec_df.loc[year]['EmissionFactor'])
        unit_df.set_index(['Engine', 'Road'], inplace=True)
        unit_df = unit_df.groupby(['Road', 'Engine', 'Class']).mean()['CO2e'].unstack('Class')

        # Calculate emissions for the year
        co2e = calculate_co2e_per_engine_type(df.loc[year], share, unit_df)
        co2e = co2e.sum(axis='columns').reset_index().groupby('Road').sum()
        co2e.columns = ['Emissions']
        co2e = co2e.to_dict()
        for road in ('Urban', 'Highways'):
            df.loc[year, road + 'Emissions'] = co2e['Emissions'][road] / 1000000  # -> kt

    df['Emissions'] = df['HighwaysEmissions'] + df['UrbanEmissions']
    df['EmissionFactor'] = df['Emissions'] / (df['Urban'] + df['Highways']) * 1000000000  # g/km

    return df


if __name__ == '__main__':
    predict_cars_emissions()
