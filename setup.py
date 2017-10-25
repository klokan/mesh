from setuptools import setup

setup(
    name='Mesh',
    version='1.6',
    description='Service mesh',
    packages=['mesh'],
    install_requires=['requests>=2.12'],
    extras_require={
        'Flask': ['Flask>=0.11'],
        'Sentry': ['raven>=6.2'],
    })
