from functools import wraps

from variables import get_variable
from utils.quilt import load_datasets


def calcfunc(variables=None, datasets=None):
    if datasets is None:
        datasets = []
    else:
        assert isinstance(datasets, (list, tuple, dict))

    if not isinstance(datasets, dict):
        datasets = {x: x for x in datasets}

    if variables is None:
        variables = []
    else:
        assert isinstance(variables, (list, tuple, dict))

    if not isinstance(variables, dict):
        variables = {x: x for x in variables}

    for var_name in variables.values():
        # Test that the variables indeed exist.
        get_variable(var_name)

    def wrapper_factory(func):
        func.variables = variables
        func.datasets = datasets

        @wraps(func)
        def load_data(*args, **kwargs):
            assert 'variables' not in kwargs
            assert 'datasets' not in kwargs

            kwargs['variables'] = {x: get_variable(y) for x, y in variables.items()}
            loaded_datasets = load_datasets(list(datasets.values()))
            if not isinstance(loaded_datasets, list):
                loaded_datasets = [loaded_datasets]
            kwargs['datasets'] = {ds_name: df for ds_name, df in zip(datasets.keys(), loaded_datasets)}

            return func(*args, **kwargs)

        return load_data

    return wrapper_factory


