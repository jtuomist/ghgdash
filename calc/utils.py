import json
from functools import wraps

from variables import get_variable
from utils.quilt import load_datasets
from utils.perf import PerfCounter

from common import cache


_dataset_cache = {}


def _generate_cache_key(func, variables):
    if variables:
        var_hash = json.dumps(variables, sort_keys=True)
    else:
        var_hash = None
    key = '%s:%s' % (hash(func), hash(var_hash))
    # print(key)
    return key


def _get_func_hash_data(func):
    variables = func.variables or {}
    all_variables = set(variables.values())

    children = func.calcfuncs or []
    all_funcs = set(children)

    for child in children:
        hash_data = _get_func_hash_data(child)
        all_variables.update(hash_data['variables'])
        all_funcs.update(hash_data['funcs'])

    all_funcs.add(func)

    return dict(variables=all_variables, funcs=all_funcs)


def _calculate_cache_key(hash_data):
    funcs = hash_data['funcs']
    variables = hash_data['variables']
    var_data = json.dumps({x: get_variable(x) for x in variables}, sort_keys=True)
    func_hash = 0
    for func in funcs:
        func_hash ^= hash(func)
    return '%s:%s' % (hash(var_data), func_hash)


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
        assert isinstance(funcs, (list, tuple))
        for func in funcs:
            assert callable(func)

    def wrapper_factory(func):
        func.variables = variables
        func.datasets = datasets
        func.calcfuncs = funcs

        @wraps(func)
        def wrap_calc_func(*args, **kwargs):
            pc = PerfCounter('%s.%s' % (func.__module__, func.__name__))
            pc.display('enter')

            hash_data = _get_func_hash_data(func)
            cache_key = _calculate_cache_key(hash_data)

            assert 'variables' not in kwargs
            assert 'datasets' not in kwargs

            if not args and not kwargs:
                should_cache_func = True
            else:
                should_cache_func = False
                print('not caching func %s.%s' % (func.__module__, func.__name__))

            if should_cache_func:
                ret = cache.get(cache_key)
                if ret is not None:  # calcfuncs must not return None
                    pc.display('cache hit')
                    return ret

            if variables is not None:
                kwargs['variables'] = {x: get_variable(y) for x, y in variables.items()}

            if datasets is not None:
                datasets_to_load = set(list(datasets.values())) - set(_dataset_cache.keys())
                if datasets_to_load:
                    loaded_datasets = []
                    for dataset_name in datasets_to_load:
                        ds_pc = PerfCounter('dataset %s' % dataset_name)
                        df = load_datasets(dataset_name)
                        ds_pc.display('loaded')
                        loaded_datasets.append(df)
                        del ds_pc

                    for dataset_name, dataset in zip(datasets_to_load, loaded_datasets):
                        _dataset_cache[dataset_name] = dataset

                kwargs['datasets'] = {ds_name: _dataset_cache[ds_url] for ds_name, ds_url in datasets.items()}

            ret = func(*args, **kwargs)
            pc.display('func ret')
            if should_cache_func:
                assert ret is not None
                cache.set(cache_key, ret, timeout=600)

            return ret

        return wrap_calc_func

    return wrapper_factory
