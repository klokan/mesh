import json


class Mesh:

    def __init__(self):
        self.config = {}
        self._http = None
        self._sentry = None

    def configure(self, path_or_config=None, **kwargs):
        if path_or_config is not None:
            if isinstance(path_or_config, str):
                with open(path_or_config, 'r') as fp:
                    self.config.update(json.load(fp))
            else:
                self.config.update(path_or_config)
        self.config.update(kwargs)

    def context(self):
        return self

    def http(self):
        http = self._http
        if http is None:
            from mesh.http import HTTP
            http = HTTP(self)
            self._http = http
        return http

    def sentry(self):
        sentry = self._sentry
        if sentry is None:
            from mesh.sentry import Sentry
            sentry = Sentry(self)
            self._sentry = sentry
        return sentry
