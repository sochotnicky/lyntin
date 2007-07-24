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
# $Id: alias.py,v 1.9 2007/07/24 00:39:03 willhelm Exp $
#########################################################################
"""
This module defines the AliasManager which manages aliases, creating new
aliases, removing aliases, checking user input for aliases, expanding
aliases, and other such things.

The AliasManager has an AliasData object for every session that has
aliases.

An alias consists of an "alias" and an "expansion".  So if there is
an alias:

   l3k -> #ses a localhost 3000

the "alias" is "l3k" and the "expansion" is "#ses a localhost 3000".
Whenever the user types "l3k" this module expands it to 
"#ses a localhost 3000" which then (after going through other user_filter
hook functions) gets executed.

Aliases are currently handled via string finding and not regular
expressions.  At some point in the future, this will be changed to
regular expressions to better handle a wider variety of aliases.
"""
from lyntin import manager, utils, exported
from lyntin.modules import modutils

class AliasData:
  """ Manages aliases."""
  def __init__(self):
    self._aliases = {}

  def addAlias(self, name, expansion):
    """
    Adds an alias to the dict.

    @param name: the alias name
    @type  name: string

    @param expansion: the string the alias expands to
    @type  expansion: string

    @raises ValueError: when the name is the same as the expansion
    """
    if name == expansion:
      raise ValueError, "name cannot equal expansion."
    self._aliases[name] = expansion

  def clear(self):
    """
    Removes all the aliases.
    """
    self._aliases.clear()

  def removeAliases(self, text):
    """
    Removes aliases from the list.

    Returns a list of tuples of alias name/expansion that
    were removed.

    @param text: the text which when run through util.expand
        gives us the aliases to remove
    @type  text: string

    @return: the list of alias/expansions that match the text
    @rtype: list of (string, string)
    """
    badaliases = utils.expand_text(text, self._aliases.keys())

    ret = []
    for mem in badaliases:
      ret.append((mem, self._aliases[mem]))
      del self._aliases[mem]

    return ret

  def getAliases(self):
    """
    Returns the keys of the alias dict.

    @return: all the aliases we're managing (but not the expansions)
    @rtype: list of strings
    """
    listing = self._aliases.keys()
    listing.sort()
    return listing

  def expand(self, input):
    """
    Looks at user input and expands any aliases involved.

    It'll return the expansion if there is one.  Otherwise
    it returns None.

    @param input: the user input to expand
    @type  input: string

    @return: the alias expansion for the given input if it's an alias
        or None
    @rtype: string
    """
    if len(input) > 0:
      # pull out the first word of the input
      firstword = input.split(' ', 1)[0]

      # if we match an alias, we return the expansion
      if firstword in self._aliases.keys():
        return self._aliases[firstword]            

    return None

  def getStatus(self):
    """
    Returns the one-line status of this manager.

    @return: the one line status
    @rtype: string
    """
    return "%d alias(es)." % len(self._aliases)
    
  def getInfo(self, text=""):
    """
    Returns information about the aliases in here.

    This is used by #alias to tell all the aliases involved
    as well as #write which takes this information and dumps
    it to the file.

    @param text: the text to expand to find aliases the user
        wants information about.
    @type  text: string

    @return: a list of strings where each string represents an alias
    @rtype: list of strings
    """
    if len(self._aliases) == 0:
      return []

    listing = self._aliases.keys()
    if text:
      listing = utils.expand_text(text, listing)

    data = []
    for mem in listing:
      data.append("alias {%s} {%s}" % (mem, utils.escape(self._aliases[mem])))

    return data

  def getInfoMappings(self):
    l = []
    for m in self._aliases.keys():
      l.append( { "alias": m, "expansion": self._aliases[m] } )

    return l


class AliasManager(manager.Manager):
  """
  Extends the manager.Manager base class to implement alias
  functionality.  The AliasManager holds session -> AliasData objects
  which handle the alias functionality.
  """
  def __init__(self):
    # session -> AliasData objects
    self._aliasdata = {}

  def getAliasData(self, ses):
    if not self._aliasdata.has_key(ses):
      self._aliasdata[ses] = AliasData()
    return self._aliasdata[ses]

  def clear(self, ses):
    if not self._aliasdata.has_key(ses):
      return
    self._aliasdata[ses].clear()

  def getAlias(self, ses, text):
    return self.getAliasData(ses).expand(text)

  def getStatus(self, ses):
    return self.getAliasData(ses).getStatus()

  def getInfo(self, ses, text=""):
    return self.getAliasData(ses).getInfo(text)

  def getInfoMappings(self, item, ses):
    if item != "alias":
      raise ValueError("%s is not a valid item for this manager." % item)

    if self._aliasdata.has_key(ses):
      return self._aliasdata[ses].getInfoMappings()
    return []
    
  def getItems(self):
    return [ "alias" ]

  def getParameters(self, item):
    if item != "alias":
      raise ValueError("%s is not a valid item for this manager." % item)

    return [ ("alias", "The alias name."),
             ("expansion", "The alias expansion.") ]

  def persist(self, args):
    """
    write_hook function for persisting the state of our session.
    """
    ses = args["session"]
    quiet = args["quiet"]

    data = self.getInfo(ses)
    if quiet == 1:
      data = [m + " quiet={true}" for m in data]
        
    return data

  def userfilter(self, args):
    """ 
    user_filter_hook.
    """
    # we check for aliases here--and if we find some, we
    # do the variable expansion and then recurse over the result
    ses = args["session"]
    internal = args["internal"]
    verbatim = args["verbatim"]
    text = args["dataadj"]
  
    if not self._aliasdata.has_key(ses) or verbatim == 1:
      return text

    aliasexpansion = self._aliasdata[ses].expand(text)

    if not aliasexpansion:
      return text
    else:
      aliasexpansion = utils.expand_placement_vars(text, aliasexpansion)
      exported.lyntin_command(aliasexpansion, 1, ses)
      return None

  def addSession(self, newsession, basesession=None):
    if basesession:
      if self._aliasdata.has_key(basesession):
        bdata = self.getAliasData(basesession)
        ndata = self.getAliasData(newsession)

        for mem in bdata._aliases.keys():
          ndata.addAlias(mem, bdata._aliases[mem])

  def removeSession(self, ses):
    if self._aliasdata.has_key(ses):
      del self._aliasdata[ses]


commands_dict = {}

def alias_cmd(ses, args, input):
  """
  With no arguments, prints all aliases.
  With one argument, prints all aliases which match the arg.
  With multiple arguments, creates an alias.

  You can use pattern variables which look like % and a number.  %0 
  will be all the arguments passed in.

  Ranges can be used by using python colon-syntax, specifying a
  half-open slice of the input items, so %0:3 is the alias name, first,
  and second arguments of the input.

  Negative numbers count back from the end of the list.  So %-1 is the
  last item in the list, %:-1 is everything but the last item in the
  list. 

  examples:
    #alias {k*}                    - prints out aliases that start with k
    #alias {k} {kill %1}           - builds a new alias
    #alias {gg} {put %1: in chest} - builds a new alias

  category: commands
  """
  name = args["alias"]
  command = args["expansion"]
  quiet = args["quiet"]

  am = exported.get_manager("alias")
  ad = am.getAliasData(ses)

  # they typed '#alias' or '#alias x' so we print the relevant aliases
  if not command:
    data = ad.getInfo(name)
    if not data:
      data = ["alias: no aliases defined."]

    exported.write_message("aliases:\n" + "\n".join(data), ses)
    return

  # they're creating an alias
  try:
    ad.addAlias(name, command)
  except ValueError, e:
    exported.write_error("alias: %s" % e, ses)

  if not quiet:
    exported.write_message("alias: {%s} {%s} added." % (name, command), ses)

commands_dict["alias"] = (alias_cmd, "alias= expansion= quiet:boolean=false")


def unalias_cmd(ses, args, input):
  """
  Allows you to remove aliases.

  category: commands
  """
  func = exported.get_manager("alias").getAliasData(ses).removeAliases
  modutils.unsomething_helper(args, func, None, "alias", "aliases")

commands_dict["unalias"] = (unalias_cmd, "str= quiet:boolean=false")

am = None

def load():
  """ Initializes the module by binding all the commands."""
  global am
  modutils.load_commands(commands_dict)
  am = AliasManager()
  exported.add_manager("alias", am)

  exported.hook_register("user_filter_hook", am.userfilter, 20)
  exported.hook_register("write_hook", am.persist)

def unload():
  """ Unloads the module by calling any unload/unbind functions."""
  global am
  modutils.unload_commands(commands_dict.keys())
  exported.remove_manager("alias")

  exported.hook_register("user_filter_hook", am.userfilter)
  exported.hook_register("write_hook", am.persist)

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
