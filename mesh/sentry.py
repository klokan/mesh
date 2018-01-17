from functools import partial
from raven import Client
from raven.transport.http import HTTPTransport


class Sentry(Client):

    def __init__(self, config, http):
        super().__init__(
            dsn=config['dsn'],
            name=config.get('name'),
            release=config.get('release'),
            environment=config.get('environment'),
            transport=partial(Transport, http))


class Transport(HTTPTransport):

    scheme = ['mesh+http', 'mesh+https']

    def __init__(self, mesh_http, **kwargs):
        super().__init__(**kwargs)
        self.mesh_http = mesh_http

    def send(self, url, data, headers):
        self.mesh_http.session.post(
            url, data=data, headers=headers, timeout=self.timeout)
