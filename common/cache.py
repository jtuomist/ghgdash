import pandas as pd
from flask_caching import Cache


_cache = {}


def get(key):
    ret = _cache.get(key)
    if isinstance(ret, (pd.DataFrame, pd.Series)):
        ret = ret.copy(deep=True)
    return ret


def set(key, val, timeout=None):
    if isinstance(val, (pd.DataFrame, pd.Series)):
        val = val.copy(deep=True)
    _cache[key] = val


def init_app(app):
    global memoize, get, set

    _cache = Cache()
    _cache.init_app(app)

    memoize = _cache.memoize
    get = _cache.get
    set = _cache.set
