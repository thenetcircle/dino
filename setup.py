#!/usr/bin/env python

from setuptools import setup, find_packages


version = '0.1.0'

setup(
    name='gridchat',
    version=version,
    description="",
    long_description="""Scalable chat server using websockets""",
    classifiers=[],
    keywords='chat',
    author='Oscar Eriksson',
    author_email='oscar@thenetcircle.com',
    url='',
    license='LICENSE.txt',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'zope.interface==4.1.3',   # interfaces
        'pyyaml==3.11',            # configuration files
        'redis==2.10.5',           # redis client
        'mysqlclient',     # connect to mysql to save statistics
        'flask-socketio==2.7.1',
        'flask_wtf',
        'wtforms',
        'eventlet',
        'gunicorn',
        #'activitystreams'
    ],
    entry_points={
        'console_scripts': [
            'gridchat = gridchat:entry',
        ]
    })
