import json

from functools import partial
from requests import Session
from requests.adapters import HTTPAdapter as BaseHTTPAdapter
from requests.auth import _basic_auth_str
from requests.utils import select_proxy


class Mesh:

    def __init__(self):
        self.proxies = {}
        self.servers = {}
        self.clients = set()
        self.http_adapter = HTTPAdapter(self.servers)
        self.sentry_client = None

    def configure(self, file=None):
        if not file:
            return

        with open(file, 'r') as fp:
            config = json.load(fp)

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

        sentry = config.get('sentry')
        if sentry:
            from raven import Client
            from mesh.sentry import Transport
            self.sentry_client = Client(
                dsn=sentry['dsn'],
                name=sentry.get('name'),
                release=sentry.get('release'),
                environment=sentry.get('environment'),
                transport=partial(Transport, self))

    def current_context(self):
        return self

    @property
    def session(self):
        context = self.current_context()
        session = getattr(context, 'mesh_session', None)
        if session is None:
            # TODO: Add retry settings.
            session = context.mesh_session = Session()
            session.mount('http://', self.http_adapter)
            session.mount('https://', self.http_adapter)
            session.proxies = self.proxies
            session.timeout = 20
        return session

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


class HTTPAdapter(BaseHTTPAdapter):

    def __init__(self, servers):
        super().__init__()
        self.servers = servers

    def add_headers(self, request, **kwargs):
        auth = select_proxy(request.url, self.servers)
        if auth is not None:
            username, password = auth
            value = _basic_auth_str(username, password)
            request.headers.setdefault('Authorization', value)
