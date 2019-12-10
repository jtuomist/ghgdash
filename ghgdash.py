# -*- coding: utf-8 -*-
import dash
import os

from flask_session import Session
from flask_babel import Babel

from layout import generate_layout, register_callbacks
from common import cache

os.environ['DASH_PRUNE_ERRORS'] = 'False'
os.environ['DASH_SILENCE_ROUTES_LOGGING'] = 'False'

app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True
)
app.css.config.serve_locally = True
app.scripts.config.serve_locally = True

server = app.server
with server.app_context():
    server.config.from_object('common.settings')

    cache.init_app(server)

    sess = Session()
    sess.init_app(server)

    babel = Babel(server)


app.layout = generate_layout(app)
register_callbacks(app)

if __name__ == '__main__':
    # Write the process pid to a file for easier profiling with py-spy
    with open('.ghgdash.pid', 'w') as pid_file:
        pid_file.write(str(os.getpid()))
    app.run_server(debug=True)
