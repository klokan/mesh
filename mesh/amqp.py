import atexit
import socket

from kombu import Connection, Exchange, Queue
from kombu.common import uuid
from signal import SIGINT, SIGTERM, signal
from threading import Lock


class AMQP:

    def __init__(self, mesh):
        config = mesh.config['amqp']
        self.mesh = mesh
        self.logger = mesh.logger

        self.app_id = config.get('app_id')
        self.base_url = 'amqp://{}/'.format(self.app_id or '')
        self.connection = Connection(config['broker'])

        self.sessions = []
        self.mutex = Lock()

        self.task_callbacks = {}
        self.consumer = None
        self.running = False

        mesh.teardown_context(self.release_session)
        atexit.register(self.close)

    def close(self):
        while self.sessions:
            session = self.sessions.pop()
            session.close()
        if self.consumer is not None:
            self.consumer.close()
            if self.consumer.connection is not None:
                self.consumer.connection.close()

    @property
    def session(self):
        context = self.mesh.current_context()
        session = getattr(context, 'amqp_session', None)
        if session is None:
            with self.mutex:
                try:
                    session = self.sessions.pop()
                except IndexError:
                    session = Session(self.app_id, self.connection.clone())
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

    def task(self, message_type):
        def decorator(callback):
            self.task_callbacks[message_type] = callback
            return callback
        return decorator

    def init_consumer(self):
        if self.consumer is None:
            connection = self.connection.clone(heartbeat=60)
            connection.ensure_connection(max_retries=3)
            self.consumer = connection.Consumer(on_message=self.process_message)  # noqa
        return self.consumer

    def make_exchange(self, **kwargs):
        return Exchange(channel=self.consumer.connection, **kwargs)

    def make_queue(self, **kwargs):
        return Queue(channel=self.consumer.connection, **kwargs)

    def run(self):
        self.running = True
        signal(SIGINT, self.stop)
        signal(SIGTERM, self.stop)

        self.consumer.consume()
        connection = self.consumer.connection

        while self.running:
            try:
                connection.drain_events(timeout=5)
            except socket.timeout:
                connection.heartbeat_check()
            except connection.connection_errors:
                connection.close()
                connection.ensure_connection(max_retries=3)
                self.consumer.revive(connection)
                self.consumer.consume()

    def stop(self, signo=None, frame=None):
        self.running = False

    def process_message(self, message):
        message_type = message.properties.get('type')
        context = self.mesh.make_context(
            method='CONSUME',
            base_url=self.base_url,
            path=message_type,
            headers=message.properties,
            content_type=message.content_type,
            data=message.body)
        with context:
            try:
                callback = self.task_callbacks[message_type]
                callback(message)
            except Exception:
                self.logger.exception('Exception occured')


class Session:

    reply_queue = Queue('amq.rabbitmq.reply-to')

    def __init__(self, app_id, connection):
        self.app_id = app_id
        self.connection = connection
        self.producer = None
        self.consumer = None
        self.messages = []
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
        self.messages.clear()
        self.replies.clear()

    def commit(self):
        for message in self.messages:
            self.publish(**message)
        self.messages.clear()

    def rollback(self):
        self.messages.clear()

    def add(self, **kwargs):
        self.messages.append(kwargs)

    def publish(self, *, exchange=None, routing_key=None, reply_to=None,
                correlation_id=None, json=None, persistent=False, **kwargs):
        message_id = uuid()
        self.init_producer()

        if reply_to is not None:
            if isinstance(reply_to, Queue):
                reply_to = reply_to.name
            if reply_to == self.reply_queue.name:
                self.init_consumer()
                if correlation_id is None:
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

        try:
            self.producer.publish(**kwargs)
        except self.connection.connection_errors:
            self.revive()
            self.producer.publish(**kwargs)

        return correlation_id

    def wait(self, correlation_id, timeout=None):
        if timeout is None:
            timeout = 10
        elapsed = 0
        while elapsed < timeout:
            reply = self.replies.pop(correlation_id, None)
            if reply is not None:
                return reply

            try:
                self.connection.drain_events(timeout=1)
            except socket.timeout:
                elapsed += 1
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

    def process_reply(self, message):
        correlation_id = message.properties['correlation_id']
        if correlation_id is not None:
            self.replies[correlation_id] = message
