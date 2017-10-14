from setuptools import setup

setup(
    name='Mesh',
    version='1.2',
    description='Service mesh',
    packages=['mesh'],
    install_requires=[
        'requests>=2.12',
    ])
