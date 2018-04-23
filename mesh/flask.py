import logging

from click import Command
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

    def init_cron(self):
        if self.cron is None:
            cron = super().init_cron()
            self.app.cli.add_command(Command('cron', callback=cron.run))
        return cron

    def init_db(self):
        if self.db is None and 'db' in self.config:
            from flask_sqlalchemy import SQLAlchemy
            config = self.config['db']
            engine = config['engine']
            session = config.get('session')
            self.app.config['SQLALCHEMY_DATABASE_URI'] = engine['url']
            self.app.config['SQLALCHEMY_ECHO'] = engine.get('echo', False)
            self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
            self.db = SQLAlchemy(self.app, session_options=session)
        return self.db

    def init_logger(self):
        if self.logger is None:
            raise Exception
        return self.logger

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

    def teardown_context(self, callback):
        self.app.teardown_appcontext(callback)

    def make_context(self, **kwargs):
        return self.app.test_request_context(**kwargs)

    def current_context(self):
        return _app_ctx_stack.top
