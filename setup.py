#!/usr/bin/env python

from setuptools import setup, find_packages
from setuptools.command.install import install as _install


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
    cmdclass={'install': Install},
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    setup_requires=['nltk'],
    install_requires=[
        'zope.interface==4.1.3',   # interfaces
        'pyyaml==3.11',            # configuration files
        'redis==2.10.5',           # redis client
        'MySQL-python==1.2.5',     # connect to mysql to save statistics
    ],
    entry_points={
        'console_scripts': [
            'spammer = spam:entry',
        ]
    })
