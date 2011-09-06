#!/usr/bin/env python

from distutils.core import setup

long_description = '''
Implementation of Bayesian Sets for fast similarity searches.
'''

setup(name='SimSearch',
    version='0.2',
    description='Implementation of Bayesian Sets for fast similarity searches',
    author='Alex Ksikes',
    author_email='alex.ksikes@gmail.com',
    url='https://github.com/alexksikes/SimSearch',
    download_url='https://github.com/alexksikes/SimSearch/zipball/0.2',
    packages=['simsearch'],
    long_description=long_description,
    license='GPL'
)