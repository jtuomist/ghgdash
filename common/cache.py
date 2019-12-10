from flask_caching import Cache


_cache = {}


def get(key):
    return _cache.get(key)


def set(key, val, timeout=None):
    _cache[key] = val


def init_app(app):
    global memoize, get, set

    _cache = Cache()
    _cache.init_app(app)

    memoize = _cache.memoize
    get = _cache.get
    set = _cache.set
