import logging

from flask import _app_ctx_stack

from mesh import Mesh as Base


class Mesh(Base):

    def __init__(self, app=None):
        super().__init__()
        self.app = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        app.extensions['mesh'] = self
        self.configure(app.config.get('MESH_CONFIG'))

    def context(self):
        return _app_ctx_stack.top

    def sentry(self):
        sentry = self._sentry
        if sentry is None:
            from raven.contrib.flask import Sentry
            sentry = Sentry(
                self.app,
                client=super().sentry(),
                logging=True,
                level=logging.WARNING)
            self._sentry = sentry
        return sentry
