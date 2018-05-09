from mesh import Mesh
from uuid import uuid4


def test_amqp():
    mesh = Mesh({'AMQP_DSN': 'amqp://guest:guest@rabbitmq/'})
    amqp = mesh.init_amqp()
    consumer = amqp.init_consumer('my_consumer')
    exchange = amqp.make_exchange(name='testing.exchange', type='direct')
    exchange.declare()
    queue = amqp.make_queue(name='testing.queue')
    queue.declare()
    queue.bind_to(exchange=exchange, routing_key='testing.routing_key')
    consumer.add_queue(queue)

    correlation_id = str(uuid4())
    secret = str(uuid4())
    received = False

    with mesh.make_context():
        amqp.session.add(
            exchange='testing.exchange',
            type='testing.ping',
            routing_key='testing.routing_key',
            reply_to='testing.queue',
            correlation_id=correlation_id,
            json=lambda: secret)
        amqp.session.commit()

    @amqp.task('testing.ping', 'my_consumer')
    def ping(message):
        print('PING', message)
        amqp.session.respond(
            type='testing.pong',
            json=message.payload)
        message.ack()

    @amqp.task('testing.pong', 'my_consumer')
    def pong(message):
        nonlocal received
        print('PONG', message)
        assert message.properties['correlation_id'] == correlation_id
        assert message.payload == secret
        message.ack()
        amqp.stop()
        received = True

    amqp.run()
    assert received
