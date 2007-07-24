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
# $Id: __init__.py,v 1.3 2007/07/24 00:39:03 willhelm Exp $
#########################################################################
"""
The modules package holds all of the dynamically loaded Lyntin modules.
Modules get loaded when Lyntin starts up unless:

  1. the module throws an exception when getting imported
  2. the module's name starts with an _

On multi-user systems, you'll want to dump modules that everyone will want
to use here.  Otherwise, users can put modules that they want to use in
their moduledir and specify the moduledir at the command line using the
-m flag.
"""

import glob, os, sys
from lyntin import exported, config


def test_for_conflicts(name, module):
  """
  Tests a module we just imported with the name the path the module
  should have.  This allows us to test Lyntin modules we just dynamically
  loaded to verify it's the one we intended to load.

  Right now we don't really do anything except kick up an error to the
  user.  Let them deal with the issue.

  @param name: the full name of the module we wanted to load
  @type  name: string

  @param module: the actual module we loaded
  @type  module: module instance
  """
  if module.__file__ != name + "c" and module.__file__ != name:
    exported.write_error("possible name conflict: '%s' and '%s'" % 
                         (name, module.__file__))


def get_module_name(filename):
  """
  Takes in a fully qualified filename and returns the module name
  portion.

  example::

    /home/willg/lyntinng/modules/alias.py -> alias

  @param filename:  the fully qualified filename
  @type filename: string

  @returns: the module name
  @rtype: string
  """
  path, filename = os.path.split(filename)
  return os.path.splitext(filename)[0]
  
def load_modules():
  """
  Magically dynamically loads all the modules in the modules
  package.  This is truly a semi-magic function.
  """
  # handle modules.*
  index = __file__.rfind(os.sep)
  if index == -1:
    path = "." + os.sep
  else:
    path = __file__[:index]

  _module_list = glob.glob( os.path.join(path, "*.py"))
  _module_list.sort()

  for mem in _module_list:
    # we skip over all files that start with a _
    # this allows hackers to be working on a module and not have
    # it die every time.
    mem2 = get_module_name(mem)
    if mem2.startswith("_"):
      continue

    try:
      name = "lyntin.modules." + mem2
      _module = __import__(name)
      _module = sys.modules[name]

      if _module.__dict__.has_key("load"):
        _module.load()

      _module.__dict__["lyntin_import"] = 1
      config.lyntinmodules.append(name)
    except:
      exported.write_traceback("Module '%s' refuses to load." % name)

  # handle modules found in the moduledir
  moduledirlist = config.options["moduledir"]
  if moduledirlist:
    for moduledir in moduledirlist:
      # grab the contents of the moduledir directory
      _module_list = glob.glob( os.path.join( moduledir, "*.py"))

      # toss the moduledir in the sys.path
      sys.path.append(moduledir)

      # and toss all the contents of the directory in our _module_list
      for mem in _module_list:
        mem2 = get_module_name(mem)
        if mem2.startswith("_"):
          continue

        try:
          _module = __import__(mem2)
          if _module.__dict__.has_key("load"):
            _module.load()

          test_for_conflicts(mem, _module)

          _module.__dict__["lyntin_import"] = 1
          config.lyntinmodules.append(mem2)
        except:
          exported.write_traceback("Module '%s' refuses to load." % mem)


# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
