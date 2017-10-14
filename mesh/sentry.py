from raven.transport.http import HTTPTransport


class Transport(HTTPTransport):

    scheme = ['mesh+http', 'mesh+https']

    def __init__(self, mesh, **kwargs):
        super().__init__(**kwargs)
        self.mesh = mesh

    def send(self, url, data, headers):
        self.mesh.session.post(
            url, data=data, headers=headers, timeout=self.timeout)
