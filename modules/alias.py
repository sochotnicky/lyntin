#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: alias.py,v 1.2 2003/05/02 01:32:52 willhelm Exp $
#######################################################################
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
import string
import manager, utils, lyntin, exported, hooks, modutils

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

  def getAlias(self, alias):
    """
    Does an alias lookup and returns the alias in question or
    an empty string.

    @returns: empty string or the alias expansion
    @rtype: string
    """
    if self._aliases.has_key(alias):
      return self._aliases[alias]
    else:
      return ""

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

    @return: a string containing all the alias information
    @rtype: string
    """
    if len(self._aliases) == 0:
      return ''

    listing = self._aliases.keys()

    if text:
      listing = utils.expand_text(text, listing)

    data = []
    for mem in listing:
      data.append("%salias {%s} {%s}" %
          (lyntin.commandchar, mem, utils.escape(self._aliases[mem])))

    return string.join(data, "\n")

  def getCount(self):
    """
    Returns the alias count.

    @return: the number of aliases managed
    @rtype: int
    """
    return len(self._aliases)


class AliasManager(manager.Manager):
  """
  Extends the manager.Manager base class to implement alias
  functionality.  The AliasManager holds session -> AliasData objects
  which handle the alias functionality.
  """
  def __init__(self):
    # session -> AliasData objects
    self._aliasdata = {}

  def addAlias(self, ses, name, expansion):
    if not self._aliasdata.has_key(ses):
      self._aliasdata[ses] = AliasData()
    self._aliasdata[ses].addAlias(name, expansion)

  def clear(self, ses):
    if not self._aliasdata.has_key(ses):
      return
    self._aliasdata[ses].clear()

  def removeAliases(self, ses, text):
    if not self._aliasdata.has_key(ses):
      return []
    return self._aliasdata[ses].removeAliases(text)

  def getAlias(self, ses, name):
    if not self._aliasdata.has_key(ses):
      return ""
    return self._aliasdata[ses].getAlias(name)

  def expand(self, ses, input):
    if not self._aliasdata.has_key(ses):
      return None
    return self._aliasdata[ses].expand(input)

  def getStatus(self, ses):
    if not self._aliasdata.has_key(ses):
      return "0 alias(es)."
    return self._aliasdata[ses].getStatus()

  def getInfo(self, ses, text=""):
    if not self._aliasdata.has_key(ses):
      return ""
    return self._aliasdata[ses].getInfo(text)

  def persist(self, args):
    """
    write_hook function for persisting the state of our session.
    """
    ses = args[0]
    file = args[1]
    quiet = args[2]

    data = self.getInfo(ses)
    if data:
      if quiet == 1:
        data = data.replace("\n", " quiet={true}\n")
        file.write(data + " quiet={true}\n")
      else:
        file.write(data + "\n")
      file.flush()

  def userfilter(self, args):
    """ 
    user_filter_hook.
    """
    # we check for aliases here--and if we find some, we
    # do the variable expansion and then recurse over the result
    ses = args[0]
    internal = args[1]
    verbatim = args[2]
    text = args[-1]
  
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
        aldata = self._aliasdata[basesession]
        for mem in aldata._aliases.keys():
          self.addAlias(newsession, mem, aldata._aliases[mem])

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

  # they typed '#alias'--print out all current aliases
  if not name and not command:
    data = am.getInfo(ses)
    if data == '':
      data = "alias: no aliases defined."

    exported.write_message("aliases:\n" + data, ses)
    return

  # they typed '#alias dd*' and are looking for matching aliases
  if not command:
    data = am.getInfo(ses, name)
    if data == '':
      data = "alias: no aliases defined."

    exported.write_message("aliases:\n" + data, ses)
    return

  try:
    am.addAlias(ses, name, command)
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
  func = exported.get_manager("alias").removeAliases
  modutils.unsomething_helper(args, func, ses, "alias", "aliases")

commands_dict["unalias"] = (unalias_cmd, "str= quiet:boolean=false")

am = None

def load():
  """ Initializes the module by binding all the commands."""
  global am
  modutils.load_commands(commands_dict)
  am = AliasManager()
  exported.add_manager("alias", am)

  hooks.user_filter_hook.register(am.userfilter, 20)
  hooks.write_hook.register(am.persist)

def unload():
  """ Unloads the module by calling any unload/unbind functions."""
  global am
  modutils.unload_commands(commands_dict.keys())
  exported.remove_manager("alias")
  hooks.user_filter_hook.unregister(am.userfilter)
  hooks.write_hook.unregister(am.persist)

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
