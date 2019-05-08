import pandas as pd


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
