from requests import Session


class Mesh:

    def __init__(self):
        self.proxies = {}
        self.clients = set()

    def init_proxies(self, file=None):
        if file is not None:
            with open(file, 'r') as fp:
                for line in fp:
                    line = line.strip()
                    if line:
                        proxied, proxy = line.split()
                        self.proxies[proxied] = proxy

    def init_clients(self, file=None):
        if file is not None:
            with open(file, 'r') as fp:
                for line in fp:
                    line = line.strip()
                    if line:
                        username, password = line.split(':')
                        self.clients.add((username, password))

    def current_context(self):
        return self

    @property
    def session(self):
        context = self.current_context()
        session = getattr(context, 'mesh_session', None)
        if session is None:
            # TODO: Add retry settings.
            session = context.mesh_session = Session()
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
