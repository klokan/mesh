from contextlib import contextmanager
from mesh import Mesh


class TestSession:
    """
    Feature: HTTP requests session
    """

    @contextmanager
    def http(self, config=None):
        mesh = Mesh()
        if config is not None:
            mesh.configure(http=config)
        http = mesh.init_http()
        with mesh.make_context():
            yield http

    def test_direct(self):
        """Scenario: Request"""
        with self.http() as http:
            response = http.session.get('http://nginx/')
            assert response.status_code == 200

    def test_proxy(self):
        """Scenario: Request through proxy"""
        config = {
            'proxies': {'http://proxy': 'http://nginx'},
        }
        with self.http(config) as http:
            response = http.session.get('http://proxy/')
            assert response.status_code == 200

    def test_unauthenticated(self):
        """Scenario: Request to restricted area without credentials"""
        with self.http() as http:
            response = http.session.get('http://nginx/restricted')
            assert response.status_code == 401

    def test_authenticated(self):
        """Scenario: Request to restricted area"""
        config = {
            'servers': {'http://nginx': 'guest:password'},
        }
        with self.http(config) as http:
            response = http.session.get('http://nginx/restricted')
            assert response.status_code == 200

    def test_authenticated_proxy(self):
        """Scenario: Request to restricted area through proxy"""
        config = {
            'proxies': {'http://proxy': 'http://nginx'},
            'servers': {'http://proxy': 'guest:password'},
        }
        with self.http(config) as http:
            response = http.session.get('http://proxy/restricted')
            assert response.status_code == 200
