import sqlalchemy
import sqlalchemy.orm

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

try:
    from thread import get_ident
except ImportError:
    from _thread import get_ident


class DB:

    @staticmethod
    def engine_options(config):
        return {
            'dsn': config['DB_DSN'],
            'echo': config.bool('DB_ECHO', False),
        }

    @staticmethod
    def session_options(config):
        return {
            'autoflush': config.bool('DB_AUTOFLUSH', False),
            'expire_on_commit': config.bool('DB_EXPIRE_ON_COMMIT', True),
        }

    @staticmethod
    def register_amqp_events(session, amqp):
        if amqp is not None:
            @event.listens_for(session, 'after_flush')
            def after_flush(session, context):
                amqp.session.flush()

            @event.listens_for(session, 'after_commit')
            def after_commit(session):
                amqp.session.commit()

            @event.listens_for(session, 'after_rollback')
            def after_rollback(session):
                amqp.session.rollback()

    def __init__(self, mesh):
        self.engine = self.create_engine(self.engine_options(mesh.config))
        self.session = self.create_session(self.session_options(mesh.config))
        self.register_amqp_events(self.session, mesh.init_amqp())
        self.Model = self.create_declarative_base()
        self.include_sqlalchemy()

    def create_engine(self, options):
        return create_engine(options['dsn'], echo=options['echo'])

    def create_session(self, options):
        factory = sessionmaker(bind=self.engine, **options)
        return scoped_session(factory, scopefunc=get_ident)

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
