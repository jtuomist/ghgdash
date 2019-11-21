from pint import UnitRegistry

ureg = UnitRegistry()
Q = ureg.Quantity


def convert_units(series, from_unit, to_unit):
    series = Q(series, from_unit)
    return series.to(to_unit).m
