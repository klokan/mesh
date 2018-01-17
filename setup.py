from setuptools import setup

setup(
    name='Mesh',
    version='2.0',
    description='Service mesh',
    packages=['mesh'],
    extras_require={
        'http': ['requests>=2.12'],
        'sentry': ['raven>=6.2'],
    })
