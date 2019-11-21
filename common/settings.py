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

MEMCACHED_URL = os.getenv('MEMCACHED_URL', None)


def get_cache_config():
    global CACHE_TYPE, CACHE_MEMCACHED_SERVERS

    url = os.getenv('CACHE_BACKEND_URL', None)
    if not url and MEMCACHED_URL:
        url = MEMCACHED_URL

    if not url:
        return

    o = urlparse(url)
    if o.scheme == 'memcached':
        CACHE_TYPE = 'memcached'
        CACHE_MEMCACHED_SERVERS = (o.netloc,)
    elif o.scheme == 'simple':
        pass
    else:
        raise ImproperlyConfigured('Invalid CACHE_BACKEND_URL: %s' % url)


get_cache_config()


def get_session_config():
    global SESSION_TYPE, SESSION_MEMCACHED

    url = os.getenv('SESSION_BACKEND_URL', None)
    if not url and MEMCACHED_URL:
        url = MEMCACHED_URL

    o = urlparse(url)
    if o.scheme == 'memcached':
        import pylibmc

        SESSION_TYPE = 'memcached'

        if not o.netloc and MEMCACHED_URL:
            o = urlparse(MEMCACHED_URL)

        SESSION_MEMCACHED = pylibmc.Client([o.netloc], binary=True)
    else:
        raise ImproperlyConfigured('Invalid SESSION_BACKEND_URL: %s' % url)


get_session_config()
