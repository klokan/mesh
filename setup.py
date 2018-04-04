from setuptools import setup

setup(
    name='Mesh',
    version='2.4',
    description='Service mesh',
    packages=['mesh'],
    extras_require={
        'amqp': ['kombu>=4.1'],
        'cron': ['schedule>=0.5'],
        'http': ['requests>=2.12'],
        'influx': ['influxdb>=5.0'],
        'sentry': ['raven>=6.2'],
    })
