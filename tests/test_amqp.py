from mesh import Mesh
from uuid import uuid4


def test_amqp():
    mesh = Mesh()
    mesh.configure(amqp={
        'broker': 'amqp://guest:guest@rabbitmq/'
    })

    amqp = mesh.init_amqp()
    consumer = amqp.init_consumer()
    exchange = amqp.make_exchange(name='testing.exchange', type='direct')
    exchange.declare()
    queue = amqp.make_queue(name='testing.queue')
    queue.declare()
    queue.bind_to(exchange=exchange, routing_key='testing.routing_key')
    consumer.add_queue(queue)

    secret = str(uuid4())
    received = False

    with mesh.make_context():
        amqp.session.add(
            exchange='testing.exchange',
            routing_key='testing.routing_key',
            type='testing.type',
            json=lambda: secret)
        amqp.session.commit()

    @amqp.task('testing.type')
    def task(message):
        nonlocal received
        print(message)
        message.ack()
        if message.payload == secret:
            amqp.stop()
            received = True

    amqp.run()
    assert received
