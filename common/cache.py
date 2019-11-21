from flask_caching import Cache

_cache = Cache()

init_app = _cache.init_app
memoize = _cache.memoize
