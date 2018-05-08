from setuptools import setup

setup(
    name='Mesh',
    version='3.1',
    description='Service mesh',
    packages=['mesh'],
    extras_require={
        'amqp': ['kombu>=4.1'],
        'cron': ['schedule>=0.5'],
        'db': ['sqlalchemy>=1.1'],
        'http': ['requests>=2.12'],
        'influx': ['influxdb>=5.0'],
        'sentry': ['raven>=6.2'],
    })
