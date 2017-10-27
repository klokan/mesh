import logging

from functools import wraps
from flask import _app_ctx_stack, abort, current_app, jsonify, request
from werkzeug.exceptions import HTTPException
from werkzeug.http import HTTP_STATUS_CODES

from . import Mesh as Base


class Mesh(Base):

    def __init__(self, app=None):
        super().__init__()
        self.app = app or current_app
        self.sentry = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.extensions['mesh'] = self
        self.configure(app.config.get('MESH_CONFIG_FILE'))
        if self.sentry_client is not None:
            from raven.contrib.flask import Sentry
            self.sentry = Sentry(
                app,
                client=self.sentry_client,
                logging=True,
                level=logging.WARNING)

    def current_context(self):
        return _app_ctx_stack.top

    def auth_required(self, callback):
        @wraps(callback)
        def wrapper(**values):
            auth = request.authorization
            if auth is None:
                abort(401)
            if (auth.username, auth.password) not in self.clients:
                abort(403)
            return callback(**values)
        return wrapper

    def json_endpoint(self, callback):
        @wraps(callback)
        def wrapper(**values):
            try:
                return callback(**values)
            except HTTPException as exc:
                response = jsonify(message=HTTP_STATUS_CODES[exc.code])
                response.status_code = exc.code
                return response
            except Exception:
                self.app.logger.exception('Internal server error')
                response = jsonify(message='Internal server error')
                response.status_code = 500
                return response
        return wrapper
