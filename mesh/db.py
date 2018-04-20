import sqlalchemy
import sqlalchemy.orm

from copy import deepcopy
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

try:
    from thread import get_ident
except ImportError:
    from _thread import get_ident


class DB:

    def __init__(self, mesh):
        config = deepcopy(mesh.config['db'])
        self.mesh = mesh
        self.engine = self.create_engine(config['engine'])
        self.session = self.create_scoped_session(config.get('session', {}))
        self.Model = self.create_declarative_base()
        self.include_sqlalchemy()

    def create_engine(self, options):
        url = options.pop('url')
        return create_engine(url, **options)

    def create_scoped_session(self, options):
        options.setdefault('autoflush', False)
        session_factory = sessionmaker(bind=self.engine, **options)
        return scoped_session(session_factory, scopefunc=get_ident)

    def create_declarative_base(self):
        model = declarative_base(cls=Model, name='Model')
        model.query = QueryProperty(self)
        return model

    def include_sqlalchemy(self):
        for module in sqlalchemy, sqlalchemy.orm:
            for key in module.__all__:
                if not hasattr(self, key):
                    setattr(self, key, getattr(module, key))


class Model:

    query = None


class QueryProperty:

    def __init__(self, db):
        self.db = db

    def __get__(self, obj, type):
        return self.db.session.query(type)
