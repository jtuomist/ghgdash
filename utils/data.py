import pandas as pd


def find_consecutive_start(values):
    last_val = start_val = values[0]
    for val in values[1:]:
        if val - last_val != 1:
            start_val = val
        last_val = val
    return start_val


def get_contributions_from_multipliers(df, mult1_column, mult2_column):
    hdf = df[~df.Forecast]
    fdf = df[df.Forecast]

    # Values from reference year
    ref = hdf.loc[hdf.index.max(), [mult1_column, mult2_column]]
    ref_product = ref.product()

    # Check how the product would look like if the other factor
    # remained the same.
    product1 = ref_product - fdf[mult1_column] * ref[mult2_column]
    product2 = ref_product - fdf[mult2_column] * ref[mult1_column]
    product = ref_product - fdf[mult1_column] * fdf[mult2_column]

    sum_product = product1 + product2
    product1 = (product1 / sum_product)

    product.name = 'EmissionReductions'
    product2 = 1 - product1

    df = pd.DataFrame(index=product.index)
    df['EmissionReductions'] = product
    df[mult1_column] = product1
    df[mult2_column] = product2

    return df
