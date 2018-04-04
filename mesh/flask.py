import logging

from flask import _app_ctx_stack

from mesh import MeshBase


class Mesh(MeshBase):

    def __init__(self, app=None):
        super().__init__()
        self.app = app
        if app is not None:
            self.init_app(app)
            self.logger = app.logger

    def init_app(self, app):
        app.extensions['mesh'] = self
        self.configure(app.config.get('MESH_CONFIG'))

    def init_logger(self):
        if self.logger is None:
            raise Exception

    def teardown_context(self, callback):
        self.app.teardown_appcontext(callback)

    def make_context(self, **kwargs):
        return self.app.test_request_context(**kwargs)

    def current_context(self):
        return _app_ctx_stack.top

    def init_sentry(self):
        if self.sentry is None and not self.app.debug:
            client = super().init_sentry()
            if client is not None:
                from raven.contrib.flask import Sentry
                self.sentry = Sentry(
                    self.app,
                    client=client,
                    logging=True,
                    level=logging.WARNING)
        return self.sentry
