import os
from urllib.parse import urlparse
from dotenv import load_dotenv
from common.exceptions import ImproperlyConfigured


load_dotenv()

# Points to repo root
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

CACHE_KEY_PREFIX = 'ghgdash-cache'
CACHE_TYPE = 'simple'
CACHE_MEMCACHED_SERVERS = ()

SESSION_TYPE = 'filesystem'
SESSION_FILE_DIR = os.path.join(BASE_DIR, 'flask_session')
SESSION_KEY_PREFIX = 'ghgdash-session'


def get_cache_config():
    global CACHE_TYPE, CACHE_MEMCACHED_SERVERS

    url = os.getenv('CACHE_BACKEND_URL', 'simple://')
    o = urlparse(url)
    if o.scheme == 'simple':
        CACHE_TYPE = 'simple'
    elif o.scheme == 'memcached':
        CACHE_TYPE = 'memcached'
        CACHE_MEMCACHED_SERVERS = (o.netloc,)
    else:
        raise ImproperlyConfigured('Invalid CACHE_URL')


get_cache_config()


def get_session_config():
    global SESSION_TYPE, SESSION_MEMCACHED
    url = os.getenv('SESSION_BACKEND_URL', 'simple://')
    o = urlparse(url)
    if o.scheme == 'memcached':
        import pylibmc

        SESSION_TYPE = 'memcached'
        SESSION_MEMCACHED = pylibmc.Client([o.netloc], binary=True)


get_session_config()
