import json
import time
from functools import wraps

from variables import get_variable
from utils.quilt import load_datasets


_dataset_cache = {}
_func_cache = {}


def _generate_cache_key(func, variables):
    if variables:
        var_hash = json.dumps(variables, sort_keys=True)
    else:
        var_hash = None
    key = '%s:%s' % (hash(func), hash(var_hash))
    ## print(key)
    return key


def calcfunc(variables=None, datasets=None, funcs=None):
    if datasets is not None:
        assert isinstance(datasets, (list, tuple, dict))
        if not isinstance(datasets, dict):
            datasets = {x: x for x in datasets}

    if variables is not None:
        assert isinstance(variables, (list, tuple, dict))
        if not isinstance(variables, dict):
            variables = {x: x for x in variables}

        for var_name in variables.values():
            # Test that the variables indeed exist.
            get_variable(var_name)

    if funcs is not None:
        assert isinstance(funcs, (list, tuple, dict))
        if not isinstance(funcs, dict):
            for func in funcs:
                assert callable(func)
            funcs = {x.__qualname__: x for x in funcs}
        else:
            for func in funcs.values():
                assert callable(func)

    def wrapper_factory(func):
        func.variables = variables
        func.datasets = datasets

        @wraps(func)
        def wrap_calc_func(*args, **kwargs):
            start = time.perf_counter()

            assert 'variables' not in kwargs
            assert 'datasets' not in kwargs

            if not args and not kwargs and not funcs:
                cache_func = True
            else:
                cache_func = False

            if variables is not None:
                kwargs['variables'] = {x: get_variable(y) for x, y in variables.items()}

            if datasets is not None:
                datasets_to_load = set(list(datasets.values())) - set(_dataset_cache.keys())
                if datasets_to_load:
                    loaded_datasets = load_datasets(list(datasets_to_load))
                    if not isinstance(loaded_datasets, list):
                        loaded_datasets = [loaded_datasets]
                    for dataset_name, dataset in zip(datasets_to_load, loaded_datasets):
                        _dataset_cache[dataset_name] = dataset

                kwargs['datasets'] = {ds_name: _dataset_cache[ds_url] for ds_name, ds_url in datasets.items()}

            ## print("%f ms calling func %s" % ((time.perf_counter() - start) * 1000.0, func.__qualname__))
            found_in_cache = False
            if cache_func:
                cache_key = _generate_cache_key(func, kwargs.get('variables'))
                if cache_key in _func_cache:
                    ret = _func_cache[cache_key]
                    found_in_cache = True

            if not found_in_cache:
                ret = func(*args, **kwargs)
                if cache_func:
                    _func_cache[cache_key] = ret
            ## print("%f ms ret from %s" % ((time.perf_counter() - start) * 1000.0, func.__qualname__))

            return ret

        return wrap_calc_func

    return wrapper_factory
