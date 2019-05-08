# Variables
VARIABLES = {
    'target_year': 2035,
    'population_forecast_correction': 0,  # Percent in target year
    'ghg_reductions_reference_year': 1990,
    'ghg_reductions_percentage_in_target_year': 80,
    'ghg_reductions_weights': {
        'heating': 39,
        'electricity': 21,
        'transport': 21,
        'waste_management': 11,
        'industry': 50
    },
    'ghg_emission_targets': [
        {
            'year': 2030,
            'Kaukolämpö': 755,
            'Öljylämmitys': 16,
            'Sähkölämmitys': 51,
            'Kulutussähkö': 243,
            'Liikenne': 263,
            'Teollisuus ja työkoneet': 3,
            'Jätteiden käsittely': 61,
            'Maatalous': 1,
        }, {
            'year': 2035,
            'Kaukolämpö': 251,
            'Öljylämmitys': 0,
            'Sähkölämmitys': 30,
            'Kulutussähkö': 151,
            'Liikenne': 230,
            'Teollisuus ja työkoneet': 3,
            'Jätteiden käsittely': 51,
            'Maatalous': 1,
        }
    ],

    'bio_is_emissionless': True,

    'municipality_name': 'Helsinki',

    'district_heating_operator': '005',  # Helen Oy
    'district_heating_target_production_ratios': {
        'Lämpöpumput': 30,
        'Puupelletit ja -briketit': 30,
        'Maakaasu': 30,
        'Kivihiili ja antrasiitti': 10
    },
    'district_heating_target_demand_change': 0,

    'electricity_production_emissions_correction': 0,
}


def set_variable(var_name, value):
    assert var_name in VARIABLES
    assert isinstance(value, type(VARIABLES[var_name]))
    VARIABLES[var_name] = value


def get_variable(var_name):
    return VARIABLES[var_name]
