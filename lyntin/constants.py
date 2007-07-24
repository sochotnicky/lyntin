#########################################################################
# This file is part of Lyntin.
#
# Lyntin is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Lyntin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# copyright (c) Free Software Foundation 2001-2007
#
# $Id: constants.py,v 1.5 2007/07/24 00:39:03 willhelm Exp $
#########################################################################
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
-------------------------------------------------------------
Welcome to Lyntin.

Lyntin is licensed under the GPLv3.  For more details see
LICENSE.

%s
For help, type "#help general".
-------------------------------------------------------------
""" % VERSION

NODEFAULTVALUE = "No default value"
