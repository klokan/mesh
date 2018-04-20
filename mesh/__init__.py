import json
import logging

from contextlib import contextmanager
from types import SimpleNamespace


class MeshBase:

    def __init__(self):
        self.config = {}
        self.amqp = None
        self.cron = None
        self.db = None
        self.http = None
        self.influx = None
        self.logger = None
        self.sentry = None

    def configure(self, path_or_config=None, **kwargs):
        if path_or_config is not None:
            if isinstance(path_or_config, str):
                with open(path_or_config, 'r') as fp:
                    self.config.update(json.load(fp))
            else:
                self.config.update(path_or_config)
        self.config.update(kwargs)

    def init_amqp(self):
        if self.amqp is None and 'amqp' in self.config:
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
        if self.influx is None and 'influx' in self.config:
            from mesh.influx import Influx
            self.influx = Influx(self)
        return self.influx

    def init_sentry(self):
        if self.sentry is None and 'sentry' in self.config:
            from mesh.sentry import make_client
            self.sentry = make_client(self)
        return self.sentry


class Mesh(MeshBase):

    logging_format = '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'

    def __init__(self):
        super().__init__()
        self.context = None
        self.teardown_callbacks = []

    def init_db(self):
        if self.db is None and 'db' in self.config:
            from mesh.db import DB
            self.db = DB(self)
        return self.db

    def init_logger(self):
        if self.logger is None:
            logging.basicConfig(format=self.logging_format, level=logging.INFO)
            self.logger = logging.getLogger()
        return self.logger

    def teardown_context(self, callback):
        self.teardown_callbacks.append(callback)
        return callback

    @contextmanager
    def make_context(self, **kwargs):
        self.context = SimpleNamespace()
        try:
            yield
        except Exception:
            self.logger.exception('Exception occured')
        finally:
            for callback in self.teardown_callbacks:
                callback()
            self.context = None

    def current_context(self):
        return self.context
