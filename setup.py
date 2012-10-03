#!/usr/bin/env python

from distutils.core import setup

long_description = '''
Item based retrieval engine with Bayesian Sets.
'''

setup(name='SimSearch',
    version='0.5',
    description='Item based retrieval engine with Bayesian Sets',
    author='Alex Ksikes',
    author_email='alex.ksikes@gmail.com',
    url='https://github.com/alexksikes/SimSearch',
    download_url='https://github.com/alexksikes/SimSearch/tarball/master',
    packages=['simsearch'],
    long_description=long_description,
    license='GPL'
)
