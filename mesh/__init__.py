import logging

from os import environ


class Config:

    def __init__(self, data):
        self.data = data

    def __contains__(self, key):
        return key in self.data

    def __getitem__(self, key):
        return self.data[key]

    def get(self, key, default=None):
        return self.data.get(key, default)

    def bool(self, key, default):
        text = self.get(key)
        if text is not None:
            return bool(int(text))
        else:
            return default


class MeshBase:

    def __init__(self, config):
        self.config = Config(config if config is not None else environ)
        self.amqp = None
        self.cron = None
        self.db = None
        self.http = None
        self.influx = None
        self.logger = None
        self.sentry = None

    def init_amqp(self):
        if self.amqp is None and 'AMQP_DSN' in self.config:
            from mesh.amqp import AMQP
            self.amqp = AMQP(self)
        return self.amqp

    def init_cron(self):
        if self.cron is None:
            from mesh.cron import CRON
            self.cron = CRON(self)
        return self.cron

    def init_http(self):
        if self.http is None:
            from mesh.http import HTTP
            self.http = HTTP(self)
        return self.http

    def init_influx(self):
        if self.influx is None and 'INFLUX_DSN' in self.config:
            from mesh.influx import Influx
            self.influx = Influx(self)
        return self.influx

    def init_sentry(self):
        if self.sentry is None and 'SENTRY_DSN' in self.config:
            from mesh.sentry import make_client
            self.sentry = make_client(self)
        return self.sentry


class Mesh(MeshBase):

    logging_format = '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'

    def __init__(self, config=None):
        super().__init__(config)
        self.context = None
        self.teardown_callbacks = []

    def init_db(self):
        if self.db is None and 'DB_DSN' in self.config:
            from mesh.db import DB
            self.db = DB(self)
        return self.db

    def init_logger(self):
        if self.logger is None:
            logging.basicConfig(format=self.logging_format, level=logging.INFO)
            self.logger = logging.getLogger()
        return self.logger

    def init_sentry(self):
        if self.sentry is None:
            sentry = super().init_sentry()
            if sentry is not None:
                sentry.install_logging_hook()
        return self.sentry

    def teardown_context(self, callback):
        self.teardown_callbacks.append(callback)
        return callback

    def make_context(self, **kwargs):
        return Context(self, kwargs)

    def current_context(self):
        return self.context


class Context:

    def __init__(self, mesh, attrs):
        self.mesh = mesh
        for key, value in attrs.items():
            setattr(self, key, value)

    def __enter__(self):
        self.mesh.context = self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            self.mesh.logger.exception('Exception occured')
        for callback in self.mesh.teardown_callbacks:
            callback()
        self.mesh.context = None
        return True
