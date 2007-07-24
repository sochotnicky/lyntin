#!/usr/bin/env python

from distutils.core import setup
import re, sys, lyntin

from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages

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
      long_description = """
Lyntin
======

Summary
-------

Lyntin is a mud client written in Python that sports multiple
user interfaces (tk, text, curses) and runs on multiple platforms
(Windows, Linux, Mac OSX, ...).  It has a module system that allows
users to write new Lyntin commands, modify default Lyntin behavior,
and extend the client to suit their individual needs.

Download and installation
-------------------------

To download and install PyBlosxom you can go to::

   http://lyntin.sourceforge.net/

to download the .tar.gz file, or you can use easy_install::

   easy_install Lyntin

""",
      license=LICENSE,
      author=AUTHOR,
      author_email=EMAIL,
      keywords="mud client",
      url=URL,
      packages=find_packages(exclude=["ez_setup"]),
      scripts=SCRIPTS,
      include_package_data = False,
      install_requires = [], # FIXME
      classifiers = ["Development Status :: 5 - Production/Stable",
                     "Intended Audience :: Developers",
                     "Intended Audience :: End Users/Desktop",
                     "License :: OSI Approved :: GNU General Public License 3.0 (GPL)",
                     "Operating System :: OS Independent",
                     "Programming Language :: Python",
                     "Topic :: Games/Entertainment :: Multi-User Dungeons (MUD)",
                     ],
       )
