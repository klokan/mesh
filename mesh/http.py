from functools import wraps
from requests import Session
from requests.adapters import HTTPAdapter
from requests.auth import _basic_auth_str
from requests.utils import select_proxy

try:
    from flask import abort, jsonify, request
    from werkzeug.exceptions import HTTPException
    from werkzeug.http import HTTP_STATUS_CODES
except ImportError:
    pass


class HTTP:

    def __init__(self, mesh):
        config = mesh.config.get('http', {})
        self.mesh = mesh
        self.logger = mesh.logger

        self.proxies = {}
        self.servers = {}
        self.clients = set()
        self.adapter = Adapter(self.servers)

        proxies = config.get('proxies')
        if proxies:
            self.proxies.update(proxies)

        servers = config.get('servers')
        if servers:
            for server, auth in servers.items():
                username, password = auth.split(':')
                self.servers[server] = (username, password)

        clients = config.get('clients')
        if clients:
            for auth in clients:
                username, password = auth.split(':')
                self.clients.add((username, password))

    @property
    def session(self):
        context = self.mesh.current_context()
        session = getattr(context, 'http_session', None)
        if session is None:
            # TODO: Add retry settings.
            session = Session()
            session.mount('http://', self.adapter)
            session.mount('https://', self.adapter)
            session.proxies = self.proxies
            session.timeout = 20
            setattr(context, 'http_session', session)
        return session

    def auth_required(self, callback):
        @wraps(callback)
        def wrapper(**values):
            auth = request.authorization
            if auth is None:
                abort(401)
            if (auth.username, auth.password) not in self.clients:
                abort(403)
            return callback(**values)
        return wrapper

    def json_endpoint(self, callback):
        @wraps(callback)
        def wrapper(**values):
            try:
                return callback(**values)
            except HTTPException as exc:
                response = jsonify(message=HTTP_STATUS_CODES[exc.code])
                response.status_code = exc.code
                return response
            except Exception:
                self.logger.exception('Internal server error')
                response = jsonify(message='Internal server error')
                response.status_code = 500
                return response
        return wrapper

    def link_header(self, *items):
        links = []
        for item in items:
            link = []
            link.append('<{}>'.format(item['url']))
            for key, val in item.items():
                if key != 'url':
                    link.append('{}="{}"'.format(key, val))
            links.append('; '.join(link))
        return ', '.join(links)


class Adapter(HTTPAdapter):

    def __init__(self, servers):
        super().__init__()
        self.servers = servers

    def add_headers(self, request, **kwargs):
        auth = select_proxy(request.url, self.servers)
        if auth is not None:
            username, password = auth
            value = _basic_auth_str(username, password)
            request.headers.setdefault('Authorization', value)
