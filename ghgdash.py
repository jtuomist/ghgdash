# -*- coding: utf-8 -*-
import dash

from flask_session import Session
from flask_babel import Babel

from layout import generate_layout
from common import cache


app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True
)
app.css.config.serve_locally = True
app.scripts.config.serve_locally = True

server = app.server
server.config.from_object('common.settings')

cache.init_app(server)

sess = Session()
sess.init_app(server)

babel = Babel(server)


app.layout = generate_layout(app)

if __name__ == '__main__':
    app.run_server(debug=True)
