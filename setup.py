#!/usr/bin/env python

import sys
import os
from distutils.core import setup

try:
    from distutils.command.build_py import build_py_2to3 as build_py
except ImportError:
    from distutils.command.build_py import build_py

# This ugly hack executes the first few lines of the module file to look up some
# common variables. We cannot just import the module because it depends on other
# modules that might not be installed yet.
filename = os.path.join(os.path.dirname(__file__), 'bottle_mysql.py')
source = open(filename).read().split('### CUT HERE')[0]
exec(source)

setup(
    name = 'bottle-mysql',
    version = __version__,
    url = 'https://github.com/tg123/bottle-mysql',
    description = 'MySQL integration for Bottle.',
    long_description = __doc__,
    author = 'Michael Lustfield',
    author_email = 'dev@lustfield.net',
    license = __license__,
    platforms = 'any',
    py_modules = [
        'bottle_mysql'
    ],
    requires = [i.strip() for i in open("requirements.txt").readlines()],
    classifiers = [
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    cmdclass = {'build_py': build_py}
)
