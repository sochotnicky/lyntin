#######################################################################
# This file is part of Lyntin
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: constants.py,v 1.3 2003/09/11 00:23:53 willhelm Exp $
#######################################################################
"""
Holds constants which will get used through the code-base as well as in
various Lyntin modules.  We attempt to keep all the useful stuff in three
different modules: constants, exported, and utils.
"""
import __init__

FIRST = 1
LAST = 99

TRUE_VALUES = ["yes", "true", "1", "on", 1]
FALSE_VALUES = ["no", "false", "0", "off", 0]

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

  -c or --configuration
       sets the configuration file to use for setting up the
       datadir, moduledirs, plugins to load, files to read,
       ui to use, and other boot options.
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
