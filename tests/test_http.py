class TestSession:
    """
    Feature: HTTP requests session
    """

    def test_direct(self, mesh):
        """Scenario: Request"""
        response = mesh.http().session.get('http://nginx/')
        assert response.status_code == 200

    def test_proxy(self, mesh):
        """Scenario: Request through proxy"""
        mesh.configure(http={
            'proxies': {'http://proxy': 'http://nginx'},
        })
        response = mesh.http().session.get('http://proxy/')
        assert response.status_code == 200

    def test_unauthenticated(self, mesh):
        """Scenario: Request to restricted area without credentials"""
        response = mesh.http().session.get('http://nginx/restricted')
        assert response.status_code == 401

    def test_authenticated(self, mesh):
        """Scenario: Request to restricted area"""
        mesh.configure(http={
            'servers': {'http://nginx': 'guest:password'},
        })
        response = mesh.http().session.get('http://nginx/restricted')
        assert response.status_code == 200

    def test_authenticated_proxy(self, mesh):
        """Scenario: Request to restricted area through proxy"""
        mesh.configure(http={
            'proxies': {'http://proxy': 'http://nginx'},
            'servers': {'http://proxy': 'guest:password'},
        })
        response = mesh.http().session.get('http://proxy/restricted')
        assert response.status_code == 200
