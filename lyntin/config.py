#######################################################################
# This file is part of Lyntin
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: config.py,v 1.1 2003/08/06 22:59:44 willhelm Exp $
#######################################################################
"""
This module holds the configuration mechanisms and a series of functions
to handle configuration from the command line and other configuration
mechanisms.
"""
import os, os.path

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

def fixdir(d):
  """
  Takes in a directory (datadir, moduledir, ...) and fixes it (by
  adding an os.sep to the end) as well as verifies that it exists.

  If it does not exist, then it returns a None.  If it does exist,
  then it returns the adjusted directory name.

  @param d: the directory in question
  @type  d: string

  @returns: None or the fixed directory
  @rtype: string
  """
  if not os.path.exists(d):
    return None

  if len(d) > 0 and d[-1] != os.sep:
    d = d + os.sep

  return d

