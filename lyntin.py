#!/usr/bin/env python
#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: lyntin.py,v 1.1 2003/04/29 21:42:35 willhelm Exp $
#######################################################################
"""
This module holds the Lyntin "global variables" and constants as well
as the main function which starts Lyntin off.
"""

# lyntin's title and catch phrase
LYNTINTITLE = "Lyntin -- The Hacker's Mudclient "

# version information
VERSION = """Lyntin CVS DEV
For bugs, suggestions, mailing list info, feature requests,
architecture docs, et al, see http://lyntin.sourceforge.net/
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

  -e or --evalmode
       Lyntin has two user input evaluation modes: lyntin and 
       tintin.  This allows you to set the mode at the command 
       line.

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

# evalmode constants
EVALMODE_TINTIN = 0
EVALMODE_LYNTIN = 1

# holds the application options--these are adjusted by command-line 
# arguments only
options = {'datadir': '',
           'evalmode': EVALMODE_LYNTIN,
           'moduledir': [],
           'readfile': [],
           'snoopdefault': 1,
           'ui': 'text'}

# Lyntin has two modes for user input evaluation.  EVALMODE_TINTIN mode
# will evaluate user input just like Tintin does.  
# EVALMODE_LYNTIN mode evaluates user input using different semantics.  
# We default to EVALMODE_LYNTIN mode.
evalmode = EVALMODE_LYNTIN


def shutdown():
  """
  This gets called by the Python interpreter atexit.  The reason
  we do shutdown stuff here is we're more likely to catch things
  here than we are to let everything cycle through the 
  ShutdownEvent.  This should probably get fixed up at some point
  in the future.
  """
  import hooks, exported
  try:
    exported.write_message("shutting down...  goodbye.")
  except:
    print "shutting down...  goodbye."
  hooks.shutdown_hook.spamhook(())

if __name__ == '__main__':
  try:
    import sys, os
    import lyntin, engine, event, utils

    # read through options and arguments
    optlist = utils.parse_args(sys.argv[1:])

    for mem in optlist:
      if mem[0] == '--ui' or mem[0] == '-u':
        lyntin.options['ui'] = mem[1]

      elif mem[0] == '--readfile' or mem[0] == "--read" or mem[0] == '-r':
        lyntin.options['readfile'].append(mem[1])

      elif mem[0] == '--moduledir' or mem[0] == '-m':
        d = mem[1]
        if d[-1] != os.sep:
          d = mem[1] + os.sep
        lyntin.options['moduledir'].append(d)

      elif mem[0] == '--datadir' or mem[0] == '-d':
        d = mem[1]
        if d[-1] != os.sep:
          d = mem[1] + "/"
        lyntin.options['datadir'] = d

      elif mem[0] == '--evalmode' or mem[0] == '-e':
        if mem[1] == 'tintin':
          lyntin.options['evalmode'] = EVALMODE_TINTIN
        else:
          lyntin.options['evalmode'] = EVALMODE_LYNTIN

      elif mem[0] == '--nosnoop':
        lyntin.options['snoopdefault'] = 0

      elif mem[0] == '--help':
        print HELPTEXT
        sys.exit(0)

      elif mem[0] == '--version':
        print VERSION
        sys.exit(0)

      else:
        opt = mem[0]
        while len(opt) > 0 and opt[0] == "-":
          opt = opt[1:]

        if len(opt) > 0:
          if lyntin.options.has_key(opt):
            lyntin.options[opt].append(mem[1])
          else:
            lyntin.options[opt] = [mem[1]]

    # if they haven't set the datadir via the command line, then
    # we go see if they have a HOME in their environment variables....
    datadir = lyntin.options['datadir']
    if not datadir:
      if os.environ.has_key("HOME"):
        datadir = os.environ["HOME"]
        if len(datadir) > 0:
          if datadir[-1] != os.sep: 
            datadir = datadir + os.sep

      lyntin.options['datadir'] = datadir

    # set the lyntin evalmode
    lyntin.evalmode = lyntin.options['evalmode']

    import atexit
    atexit.register(lyntin.shutdown)

    # instantiate an engine
    engine.myengine = engine.Engine()
    engine.myengine.initialize()

    # generate a startup event.
    # StartupEvent handles all the rest of the initialization
    # including parsing command-line arguments and such.
    event.StartupEvent().enqueue()

    # start the engine which will execute the startupevent
    # and start executing.
    engine.myengine.runengine()

  except SystemExit:
    if engine.myengine != None:
      event.ShutdownEvent().enqueue()
      engine.myengine.runengine()
    
  except:
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
