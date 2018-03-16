from setuptools import setup

setup(
    name='Mesh',
    version='2.3',
    description='Service mesh',
    packages=['mesh'],
    extras_require={
        'amqp': ['kombu>=4.1'],
        'http': ['requests>=2.12'],
        'sentry': ['raven>=6.2'],
    })
