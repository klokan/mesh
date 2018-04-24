import logging

from click import Command
from flask import _app_ctx_stack

from mesh import MeshBase


class Mesh(MeshBase):

    def __init__(self, app):
        super().__init__()
        app.extensions['mesh'] = self
        self.app = app
        self.logger = app.logger

    def init_cron(self):
        if self.cron is None:
            cron = super().init_cron()
            self.app.cli.add_command(Command('cron', callback=cron.run))
        return cron

    def init_db(self):
        if self.db is None and 'DB_DSN' in self.config:
            from flask_sqlalchemy import SQLAlchemy
            from mesh.db import DB

            engine_options = DB.engine_options(self.config)
            self.app.config.update(
                SQLALCHEMY_DATABASE_URI=engine_options['dsn'],
                SQLALCHEMY_ECHO=engine_options['echo'],
                SQLALCHEMY_TRACK_MODIFICATIONS=False)

            session_options = DB.session_options(self.config)
            self.db = SQLAlchemy(self.app, session_options=session_options)
            DB.register_amqp_events(self.db.session, self.init_amqp())

        return self.db

    def init_logger(self):
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
