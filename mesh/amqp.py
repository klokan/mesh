import atexit
import socket

from kombu import Connection, Exchange, Queue
from kombu.common import uuid
from signal import SIGINT, SIGTERM, signal
from threading import Lock


class AMQP:

    def __init__(self, mesh):
        self.mesh = mesh
        self.logger = mesh.init_logger()

        self.app_id = mesh.config.get('AMQP_APP_ID')
        self.base_url = 'amqp://{}/'.format(self.app_id or '')
        self.connection_prototype = Connection(mesh.config['AMQP_DSN'])

        self.sessions = []
        self.mutex = Lock()

        self.task_callbacks = {}
        self.connection = None
        self.consumers = {}
        self.running = False

        mesh.teardown_context(self.release_session)
        atexit.register(self.close)

    def close(self):
        while self.sessions:
            session = self.sessions.pop()
            session.close()
        for consumer in self.consumers.values():
            consumer.close()
        if self.connection is not None:
            self.connection.close()

    @property
    def session(self):
        context = self.mesh.current_context()
        session = getattr(context, 'amqp_session', None)
        if session is None:
            with self.mutex:
                try:
                    session = self.sessions.pop()
                except IndexError:
                    connection = self.connection_prototype.clone()
                    session = Session(self.mesh, self.app_id, connection)
            session.begin()
            setattr(context, 'amqp_session', session)
        return session

    def release_session(self, exc=None):
        context = self.mesh.current_context()
        session = getattr(context, 'amqp_session', None)
        if session is not None:
            session.rollback()
            if session.connected:
                with self.mutex:
                    self.sessions.append(session)

    def task(self, message_type, consumer_name='default'):
        def decorator(callback):
            self.task_callbacks[consumer_name, message_type] = callback
            return callback
        return decorator

    def init_connection(self):
        connection = self.connection
        if connection is None:
            connection = self.connection_prototype.clone(heartbeat=60)
            connection.ensure_connection(max_retries=3)
            self.connection = connection
        return connection

    def init_consumer(self, consumer_name='default'):
        consumer = self.consumers.get(consumer_name)
        if consumer is None:
            connection = self.init_connection()
            consumer = connection.Consumer(
                on_message=self.process_message,
                tag_prefix=f'{consumer_name}/',
                auto_declare=False)
            self.consumers[consumer_name] = consumer
        return consumer

    def make_exchange(self, **kwargs):
        return Exchange(channel=self.init_connection(), **kwargs)

    def make_queue(self, **kwargs):
        return Queue(channel=self.init_connection(), **kwargs)

    def run(self):
        self.running = True
        signal(SIGINT, self.stop)
        signal(SIGTERM, self.stop)

        for consumer in self.consumers.values():
            consumer.consume()

        while self.running:
            try:
                self.connection.drain_events(timeout=5)
            except socket.timeout:
                self.connection.heartbeat_check()
            except self.connection.connection_errors:
                self.connection.close()
                self.connection.ensure_connection(max_retries=3)
                for consumer in self.consumers.values():
                    consumer.revive(self.connection)
                    consumer.consume()

    def stop(self, signo=None, frame=None):
        self.running = False

    def process_message(self, message):
        consumer_name, __, __ = message.delivery_info['consumer_tag'].partition('/')  # noqa
        message_type = message.properties.get('type')

        context = self.mesh.make_context(
            method='CONSUME',
            base_url=self.base_url,
            path=f'/{consumer_name}/{message_type}',
            headers=message.properties,
            content_type=message.content_type,
            data=message.body)
        context.amqp_message = message

        with context:
            try:
                callback = self.task_callbacks[consumer_name, message_type]
                callback(message)
            except Exception:
                self.logger.exception('Exception occured')
            finally:
                if not message.acknowledged:
                    message.reject()


class Session:

    reply_queue = Queue('amq.rabbitmq.reply-to')

    def __init__(self, mesh, app_id, connection):
        self.mesh = mesh
        self.app_id = app_id
        self.connection = connection
        self.producer = None
        self.consumer = None
        self.new = []
        self.pending = []
        self.replies = {}

    def init_producer(self):
        if self.producer is None:
            self.producer = self.connection.Producer()

    def init_consumer(self):
        if self.consumer is None:
            self.consumer = self.connection.Consumer(
                queues=[self.reply_queue],
                on_message=self.process_reply,
                no_ack=True)
            self.consumer.consume()

    @property
    def connected(self):
        return self.connection.connected

    def revive(self):
        self.connection.close()
        self.connection.ensure_connection(max_retries=3)
        if self.producer is not None:
            self.producer.revive(self.connection)
        if self.consumer is not None:
            self.consumer.revive(self.connection)
            self.consumer.consume()

    def close(self):
        if self.consumer is not None:
            self.consumer.close()
        if self.producer is not None:
            self.producer.close()
        self.connection.close()

    def begin(self):
        self.new.clear()
        self.pending.clear()
        self.replies.clear()

    def add(self, **kwargs):
        self.new.append(kwargs)

    def flush(self):
        for message in self.new:
            prepared_message = self.prepare(**message)
            self.pending.append(prepared_message)
        self.new.clear()

    def commit(self):
        if self.new:
            self.flush()
        for prepared_message in self.pending:
            self.publish(prepared_message)
        self.pending.clear()

    def rollback(self):
        self.new.clear()
        self.pending.clear()

    def prepare(self, *, exchange=None, routing_key=None, reply_to=None,
                correlation_id=None, json=None, persistent=True, **kwargs):
        message_id = uuid()

        if reply_to is not None:
            if isinstance(reply_to, Queue):
                reply_to = reply_to.name
            if reply_to == self.reply_queue.name and correlation_id is None:
                correlation_id = message_id

        kwargs['exchange'] = exchange if exchange is not None else ''
        kwargs['routing_key'] = routing_key if routing_key is not None else ''
        kwargs['reply_to'] = reply_to
        kwargs['app_id'] = self.app_id
        kwargs['message_id'] = message_id
        kwargs['correlation_id'] = correlation_id
        kwargs['delivery_mode'] = 2 if persistent else 1

        if json is not None:
            if callable(json):
                json = json()
            kwargs['serializer'] = 'json'
            kwargs['body'] = json
        else:
            kwargs.setdefault('body', '')

        return kwargs

    def publish(self, prepared_message=None, **kwargs):
        if prepared_message is None:
            prepared_message = self.prepare(**kwargs)

        self.init_producer()
        if prepared_message['reply_to'] == self.reply_queue.name:
            self.init_consumer()

        try:
            self.producer.publish(**prepared_message)
        except self.connection.connection_errors:
            self.revive()
            self.producer.publish(**prepared_message)

        return prepared_message['correlation_id']

    def wait(self, correlation_id, timeout=None):
        if timeout is None:
            timeout = 10

        elapsed = 0
        while True:
            reply = self.replies.pop(correlation_id, None)
            if reply is not None:
                return reply

            try:
                self.connection.drain_events(timeout=1)
            except socket.timeout:
                elapsed += 1
                if elapsed >= timeout:
                    raise
            except self.connection.connection_errors:
                # There is no point in retrying. Direct reply queues
                # are tied to connections, so we couldn't receive
                # replies anyway.
                self.close()
                raise

    def request(self, timeout=None, **kwargs):
        kwargs.setdefault('reply_to', self.reply_queue)
        correlation_id = self.publish(**kwargs)
        return self.wait(correlation_id, timeout=timeout)

    def respond(self, **kwargs):
        context = self.mesh.current_context()
        request = context.amqp_message.properties
        kwargs.setdefault('routing_key', request['reply_to'])
        kwargs.setdefault('correlation_id', request.get('correlation_id'))
        return self.publish(**kwargs)

    def process_reply(self, message):
        correlation_id = message.properties['correlation_id']
        if correlation_id is not None:
            self.replies[correlation_id] = message
