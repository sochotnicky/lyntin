#######################################################################
# This file is part of Lyntin
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: constants.py,v 1.2 2003/08/27 03:19:58 willhelm Exp $
#######################################################################
"""
Holds constants which will get used through the code-base as well as in
various Lyntin modules.  We attempt to keep all the useful stuff in three
different modules: constants, exported, and utils.
"""
import __init__

FIRST = 1
LAST = 99

TRUE_VALUES = ["yes", "true", "1", "on"]
FALSE_VALUES = ["no", "false", "0", "off"]

# lyntin's title and catch phrase
LYNTINTITLE = "Lyntin -- The Hacker's Mudclient "

# version information
VERSION = """Lyntin """ + __init__.__version__ + """
For bugs, suggestions, mailing list info, feature requests,
architecture docs, et al, see """ + __init__.__url__ + """
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

# Lyntin displays this after it's done initializing and it's
# ready for user interaction.
STARTUPTEXT = """Initialization complete.
--------------------------------------
Welcome to Lyntin.
For help, type "#help general".
--------------------------------------
"""

NODEFAULTVALUE = "No default value"
