#!/usr/bin/env python

from setuptools import setup, find_packages


version = '0.12.25'

setup(
    name='dino',
    version=version,
    description="Distributed Notifications",
    long_description="""Distributed notification server using websockets""",
    classifiers=[],
    keywords='notifications,chat,socketio,distributed',
    author='Oscar Eriksson',
    author_email='oscar.eriks@gmail.com',
    url='https://github.com/thenetcircle/dino',
    license='LICENSE.txt',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'zope.interface',   # interfaces
        'pyyaml',            # configuration files
        'redis',           # redis client
        'psycopg2',
        'sqlalchemy',
        'flask-restful',
        'flask-socketio',
        'flask_wtf',
        'wtforms',
        'python-socketio',
        'mysqlclient',
        'gunicorn',
        'activitystreams',
        'codecov',
        'fakeredis',
        'nose',
        'codecov',
        'coverage',
        'cassandra-driver',
        'kombu',
        'typing',
        'nose-parameterized',
        'python-dateutil',
        'psycogreen',
        'statsd',
        'pymitter',
        'psutil',
        'gitpython'
    ])
