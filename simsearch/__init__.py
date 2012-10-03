#!/usr/bin/env python

"""SimSearch is an item based retrieval engine which implements Bayesian Sets:

http://www.gatsby.ucl.ac.uk/~heller/bsets.pdf
http://thenoisychannel.com/2010/04/04/guest-post-information-retrieval-using-a-bayesian-model-of-learning-and-generalization/
"""

__version__ = '0.5'
__author__ = 'Alex Ksikes <alex.ksikes@gmail.com>'
__license__ = 'GPL'

from bsets import *
from simsphinx import *
from indexer import *
