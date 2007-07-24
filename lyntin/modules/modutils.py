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
# $Id: modutils.py,v 1.4 2007/07/24 00:39:03 willhelm Exp $
#########################################################################
"""
This module holds helper functions for building other Lyntin modules.
This module will likely make things easier for you, however, it is not
an API module and the contents herein are subject to change if we
need to change them.  Having said that, I will note it doesn't change
much.
"""
import types
from lyntin import exported


def load_commands(commands_dict):
  """
  Takes in a dict and loads all the commands in that dict.

  The dict is a mapping of command name to arguments to be passed
  to exported.add_command.  Pretty much we just turn around and
  call exported.add_command with the arguments in the dict without
  any transformation at all.

  @param commands_dict: the map holding the command names and the
      arguments we need to call exported.add_command repeatedly
  @type  commands_dict: dict
  """
  for mem in commands_dict.keys(): 
    args = commands_dict[mem]
    if type(args) == types.TupleType:
      exported.add_command(*((mem,)+args))
    else:
      exported.add_command(mem, args)

def unload_commands(commands_list):
  """
  Takes in a list of command names and removes the commands from
  Lyntin by calling exported.remove_command.

  @param commands_list: the list of command names to remove
  @type  commands_list: list of strings
  """
  for mem in commands_list:
    exported.remove_command(mem)


def unsomething_helper(args, func, ses=None, sing="", plur=""):
  """
  Helps automate some of the un(something) commands.  These are
  commands that remove data from a given manager.  For example,
  unalias, unaction....

  This method also handles printing out status information to
  the user as to how many somethings were removed.

  @param args: the map with the str and quiet arguments in it
  @type  args: dict

  @param func: the function to call to actually do the work.
      it should take in a single string argument.
  @type  func: function

  @param ses: the session to apply this to
  @type  ses: Session

  @param sing: the singular form of the unsomething--for output
      (ex: "alias")
  @type  sing: string

  @param plur: the plural form of the unsomething--for output
      (ex: "aliases")
  @type  plur: string
  """
  text = args["str"]
  quiet = args["quiet"]

  if ses:
    removedthings = func(ses, text)
  else:
    removedthings = func(text)

  if not quiet:
    if len(removedthings) == 0:
      data = "un%s: No %s removed." % (sing, plur)
    else:
      data = []
      for mem in removedthings:
        if type(mem) == types.TupleType or type(mem) == types.ListType:
          mem = "{%s}" % ("} {".join(map(str, mem)))
          data.append("un%s: %s removed." % (sing, mem))
        else:
          data.append("un%s: {%s} removed." % (sing, mem))
      data = "\n".join(data)
    exported.write_message(data, ses)


# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
