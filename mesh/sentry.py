from functools import partial
from raven import Client
from raven.transport.http import HTTPTransport


def make_client(mesh):
    return Client(
        dsn=mesh.config['SENTRY_DSN'],
        name=mesh.config.get('SENTRY_NAME'),
        release=mesh.config.get('SENTRY_RELEASE'),
        environment=mesh.config.get('SENTRY_ENVIRONMENT'),
        transport=partial(Transport, mesh.init_http()))


class Transport(HTTPTransport):

    scheme = ['mesh+http', 'mesh+https']

    def __init__(self, mesh_http, **kwargs):
        super().__init__(**kwargs)
        self.mesh_http = mesh_http

    def send(self, url, data, headers):
        self.mesh_http.session.post(
            url, data=data, headers=headers, timeout=self.timeout)
