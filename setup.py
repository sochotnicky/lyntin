#!/usr/bin/env python

from distutils.core import setup
import re, sys, lyntin

VERSION = str(lyntin.__version__)
(AUTHOR, EMAIL) = re.match("^(.*?)\s*<(.*)>$", lyntin.__author__).groups()
URL = lyntin.__url__
LICENSE = lyntin.__license__

if '--format=wininst' in sys.argv:
  SCRIPTS = ['scripts/runlyntin.pyw']
else:
  SCRIPTS = ['scripts/runlyntin']

setup(name="lyntin",
      version=VERSION.lower(),
      description="Lyntin mud client",
      author=AUTHOR,
      author_email=EMAIL,
      license=LICENSE,
      url=URL,
      scripts=SCRIPTS,
      packages=['lyntin', 'lyntin.modules', 'lyntin.ui', 'scripts'],
      long_description=
"""Lyntin is a mud client framework written in Python which allows for 
plugins, different user interfaces, and the use of Python on the command 
line."""
      )
