#######################################################################
# This file is part of Lyntin
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: __init__.py,v 1.1 2003/05/05 05:54:19 willhelm Exp $
#######################################################################
"""
Lyntin is an open-source mud client framework written in Python which allows
for additional functionality to be written in Python as Lyntin modules.
"""
__docformat__ = 'epytext en'

__version__ = 'CVS-DEV'
__author__ = 'Will Guaraldi <willhelm@users.sourceforge.net>'
__url__ = 'http://lyntin.sourceforge.net/'

__copyright__ = '(C) 2003 FSF'
__license__ = 'GPL'


# lyntin's title and catch phrase
LYNTINTITLE = "Lyntin -- The Hacker's Mudclient "

# version information
VERSION = """Lyntin """ + __version__ + """
For bugs, suggestions, mailing list info, feature requests,
architecture docs, et al, see """ + __url__ + """
"""

# help text which gets printed to stdout if you do 'lyntin.py --help'
HELPTEXT = """syntax: lyntin.py [[OPTIONS] | [--help] | [--version]]

  --help
       displays this text and exits.

  -v or --version
       prints out the version information and exits.


OPTIONS:

  -d or --datadir
       If you don't set your datadir, Lyntin will set the 
       datadir to the HOME environment variable.  Using this 
       option allows you to set it manually.  You can specify 
       only one --datadir flag.  Specifying additional ones 
       will overwrite the last one.

  -m or --moduledir
       Lyntin dynamically loads everything in the lyntin/modules 
       dir, but will additionally dynamically load modules in dirs 
       specified by this flag.  You can specify multiple 
       --moduledir flags.
         
  -r or --read or --readfile
       Reads a file in at startup populating the common session 
       with aliases, actions, and whatnot.  You can specify 
       multiple files to read with multiple --read flags.

  --nosnoop
       Lyntin defaults to snooping.  This sets it so Lyntin will
       default to no snooping.

  -u or --ui
       Launches a specific ui for Lyntin.  Lyntin comes with two 
       ui's: 'text' and 'tk'.  Other ui's can be dropped into the 
       ui/ subdirectory and this switch can be used for starting 
       them as well.
"""

# the wizlist of folks without whom Lyntin wouldn't exist.
WIZLIST = """See the website: http://lyntin.sourceforge.net/contrib.php
"""

# Lyntin displays this after it's done initializing and it's
# ready for user interaction.
STARTUPTEXT = """Initialization complete.
--------------------------------------
Welcome to Lyntin.
For help, type "#help general".
--------------------------------------
"""


# the character used to denote variables (FIXME - this is only half true)
variablechar = '$'

# the character used to denote commands
commandchar = '#'

# whether (1) or not (0) we're in debug mode which helps us figure out
# how our commands are being evaluated
debugmode = 0

# whether (1) or not (0) we're doing prompt detection.  prompt detection
# is done in net.py when mud data comes in.
promptdetection = 0

# whether (1) or not (0) we do speedwalking checks
speedwalk = 1

# whether (1) or not (0) we whack all the ansi stuff for incoming mud data
ansicolor = 1

# whether (1) or not (0) we're echoing user input to the ui
mudecho = 1

# this holds a list of all the modules Lyntin has dynamically imported
# or have been imported via the #import command.
lyntinmodules = []

# Lyntin counts the total number of errors it's encountered.
# This enables us to shut ourselves down if we encounter too
# many which indicates a "bigger problem".
errorcount = 0

# holds the application options--these are adjusted by command-line 
# arguments only
options = {'datadir': '',
           'moduledir': [],
           'readfile': [],
           'snoopdefault': 1,
           'ui': 'text'}
