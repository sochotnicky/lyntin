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
# $Id: helpmanager.py,v 1.7 2007/07/24 00:39:03 willhelm Exp $
#########################################################################
"""
Lyntin has a comprehensive X{help} system that can be accessed in-game
through the "#help" command.  The help material is all organized
and manipulated by the "HelpManager".  Help is organized as
topics which exist in a hierarchy of categories and it comes from 
a couple of sources:

  1. dynamically loaded at Lyntin startup from files located in 
     the help subdirectory and ending with .tpc extension

  2. when commands are registered via the exported.add_command
     function

  3. by any module using the exported.add_help function


It's interesting to note that the README and COMMANDS files
are generated entirely of in-game help topics using a template
script file and my personal home-brew #exporthelp command.

The help manager holds a hierarchy of help files indexed by category.
It also houses a series of methods for adding new help text, parsing
help file text, and also exporting help content into some format
which then can be converted to a variety of other formats: HTML,
XML, JoesMagicTextMarkup, ...
"""
import types
from lyntin import utils, config, manager

class HelpManager(manager.Manager):
  """
  The HelpManager exists on the engine scoping--there is only one
  per Lyntin instance.  It holds a hierarchy of help texts which
  can be retrieved and perused through via the #help user command.
  In general, it's best to access the HelpManager instance through
  the exported module.

  Help texts are indexed by an 'fqn' which is a fully-qualified-name.
  For example, the #alias command would be under 'commands.alias'
  where 'commands' is the category in the help hierarchy that it goes
  under and 'alias' is the help text topic name.

  Help text can also handle options set in the text in itself.  Currently
  the only option we support is "category".  This will be used if
  the fqn you supply to the addHelp call is lacking a category--for
  example 'alias'.
  """
  def __init__(self, e):
    self._help_tree = {}
    self._engine = e

  def addHelp(self, fqn, helptext):
    """
    Adds a help text to the hierarchy.  Use the 'exported.add_help'
    and not this directly.

    @param fqn: the fully qualified name
    @type  fqn: string

    @param helptext: the help text
    @type  helptext: string

    @return: the fqn of the help topic we just added (this can change
        depending on whether there's a category directive)
    @rtype: string

    @raises ValueError: if the help name or help text are not valid
    """
    categorylist, helpname = self._split_name(fqn)

    if not helptext or not helpname:
      raise ValueError("Help name and text are required.")

    directives, helptext = _parse_directives(helptext)

    if directives.has_key("category"):
      categorylist = directives["category"].split(".") + categorylist

    place = self._help_tree
    for mem in categorylist:
      if place.has_key(mem):
        if type(place[mem]) == types.DictType:
          place = place[mem]
        else:
          tmp = place[mem]
          place[mem] = {}
          place[mem]["__doc__"] = tmp
          place = place[mem]
      else:
        place[mem] = {}
        place = place[mem]

    if place.has_key(helpname):
      if type(place[helpname]) == types.DictType:
        place[helpname]["__doc__"] = helptext
      else:
        place[helpname] = helptext
    else:
      place[helpname] = helptext

    if categorylist:
      fqn = "%s.%s" % (".".join(categorylist), helpname)
    else:
      fqn = "root.%s" % helpname
    return fqn

  def removeHelp(self, fqn):
    """
    Takes in a fully-qualified name and attempts to remove it from
    the structure.

    @param fqn: the fully qualified name of the help topic to remove
    @type  fqn: string

    @raises ValueError: if no topic by that fqn exists
    """
    categories, name = self._split_name(fqn)

    place = self._help_tree
    breadcrumbs = []

    for mem in categories:
      if place.has_key(mem):
        breadcrumbs.append(place)
        place = place[mem]
      else:
        raise ValueError("Topic '%s' does not exist." % fqn)

    if place.has_key(name):
      del place[name]
      self._trimTree(self._help_tree)

    else:
      raise ValueError("Topic '%s' does not exist." % fqn)


  def _trimTree(self, tree):
    """
    Takes a tree and trims off the branches that don't hold any 
    elements.  This method is recursive and will call itself at
    the various branches.  It modifies the tree in place.

    @param tree: the map of topics to trim
    @type  tree: dict
    """
    for mem in tree.keys():
      if type(tree[mem]) == types.DictType:
        self._trimTree(tree[mem])

        if len(tree[mem].keys()) == 0:
          del tree[mem]

  def getNode(self, fqn):
    """
    Retrieves the help topic requested.

    The difference between this and getHelp is that getHelp will
    do searching and try to find the best topic for what you asked
    for.  This will return the topic at the prescribed place or
    throw an exception if it doesn't exist.  This is better for
    exporting help topics to a manual of some kind.

    @param fqn: the fully qualified name of the topic being requested
    @type  fqn: string

    @return: a tuple consisting of the topic data string, and then a list
        of nodes under this fqn (if it's a category)
    @rtype: (string, list of strings)

    @raises ValueError: if the fqn doesn't exist
    """
    categorylist, name = self._split_name(fqn)
    categorylist.append(name)

    tree = self._help_tree

    for mem in categorylist:
      if type(tree) == types.DictType:
        if tree.has_key(mem):
          tree = tree[mem]
        else:
          raise ValueError("FQN '%s' doesn't exist." % fqn)
      else:
        raise ValueError("FQN '%s' doesn't exist." % fqn)

    if type(tree) == types.DictType:
      list = []
      for key, value in tree.items():
        list.append("%s.%s" % (".".join(categorylist), key))

      list.sort()
      if tree.has_key("__doc__"):
        list.remove(".".join(categorylist) + ".__doc__")
        return (tree["__doc__"], list)

      return ('', list)

    return (tree, [])

    
  def getHelp(self, fqn):
    """
    Retrieves the help topic requested.  This is the hard-core
    attempt at finding help text.  It will look for it outright,
    then try searching, then try black magic.

    @param fqn: the fully qualified name or topic name
    @type  fqn: string

    @return: A tuple composed of three strings.  The first string is
        error text (if any or empty string if none).  The second
        string is the breadcrumbs trail.  The third string is the
        help text found or a columnized text of what tree elements
        exist at that level.
    @rtype: tuple of (string, string, string)
    """
    categorylist, name = self._split_name(fqn)

    categorylist.append(name)

    tree = self._help_tree
    breadcrumbs = "root"
    found = 1

    for mem in categorylist:
      if type(tree) == types.DictType:
        if tree.has_key(mem):
          tree = tree[mem]
          breadcrumbs += "." + mem
        else:
          found = 0
          break
      else:
        found = 0
        break
    
    if found == 0 and fqn != "": 
      # first find all instances of categorylist[0] in the help tree.
      potentialroots = []
      start = categorylist[0]

      tosearch = [ ("root",self._help_tree) ]
      while tosearch:
        nextbreadcrumbs, nextnode = tosearch[0]
        tosearch = tosearch[1:]
        for key in nextnode.keys():
          currentbreadcrumbs = "%s.%s" % (nextbreadcrumbs, key)
          if key == categorylist[0]:
            potentialroots.append( (currentbreadcrumbs,nextnode[key]) )
          if type(nextnode[key]) == types.DictType:
            tosearch.append( (currentbreadcrumbs,nextnode[key]) )

      foundnodes = []

      # Now walk through all of the nodes named categorylist[0] and see if
      # they have they have categorylist[1:] under them.
      for bc,node in potentialroots:
        for key in categorylist[1:]:
          if type(node) != types.DictType or not node.has_key(key):
            bc=None
            node=None
          else:
            bc = "%s.%s" % (bc, key)
            node = node[key]
        if node:
          foundnodes.append( (bc,node) )


      # If we only found one thing then run the rest of the function
      # as though that was what was entered.  Otherwise build the
      # The error text to state the nodes that were found.
      if len(foundnodes) == 1:
        breadcrumbs,tree = foundnodes[0]
        error = ""
      elif len(foundnodes) == 0:
        error = "Cannot find '%s'.  We did find this:" % fqn
      else:
        error = "Could not find exact match for '%s'.  We did find these matches:" % fqn
        list = map(lambda x:x[0],foundnodes)
        return (error, "", utils.columnize(textlist=list,indent=3))
    else:
      error = ""

    if type(tree) == types.DictType:
      toplist = []
      catlist = []
      for key, value in tree.items():
        if type(value) == types.DictType:
          catlist.append("%s(%d) " % (key, len(value)))
        else:
          toplist.append(key)
      toplist.sort()
      catlist.sort()
      if tree.has_key("__doc__"):
        if "__doc__" in toplist: toplist.remove("__doc__")
        if "__doc__" in catlist: catlist.remove("__doc__")
        helphead = tree["__doc__"] + "\n\nOther things in this category:\n\n"
      else:
        helphead = ""
      data = helphead
      if catlist:
        data += "Categories:\n" + utils.columnize(catlist, indent=3) + "\n"
      if toplist:
        data += "Topics:\n" + utils.columnize(toplist, indent=3) + "\n"

      return (error, breadcrumbs, data)
    return (error, breadcrumbs, tree)
    
  def _printTree(self, tree=None, tab=""):
    """
    Prints out the hierarchy--for debugging purposes.
    """
    if tree == None:
      tree = self._help_tree
      print tab + "Root:"

    for mem in tree.keys():
      if type(tree[mem]) == types.DictType:
        print "%s  %s:" % (tab, mem)
        self._printTree(tree[mem], tab + "  ")
      else:
        print "%s  node: %s" % (tab, mem)


  def _split_name(self, fqn):
    """
    Takes an fqn and splits it into a series of categories and a help
    topic name.  fqn's are delimited by a '.' (period).

    It tries to fix up the fqn as well--doing things like removing
    lyntin command characters from the name (some users type "#help #alias"
    to view the help on the alias command) and also removing instances
    of "root" from the beginning of the fqn because it's not needed.

    @param fqn: the fully qualified name to split
    @type  fqn: string

    @return: the category list and the help topic name
    @rtype: tuple of (list of strings, string)
    """
    if not fqn:
      fqn = ""

    keys = fqn.split(".")
    if len(keys) > 1 and keys[0] == "root":
      keys = keys[1:]

    if len(keys) > 0:
      categories = keys[:-1]
      name = keys[-1]
      if len(name) > 0 and name[0] == self._engine.getConfigManager().get("commandchar"):
        name = name[1:]
      return (categories, name)
    else:
      return ([], "")


_directives = ["category"]

def _parse_directives(helptext):
  """
  Parses out the directives in the last lines of a given help text 
  and returns these directives in a dict.  Also strips the helptext
  (removing whitespace at the beginning and the end), removes
  directives found at the end, and returns this adjusted help text.

  To add new directives to extract, add them to the '_directives' 
  variable.

  If no directives were found, we return an empty string.

  @param helptext: the help text topic
  @type  helptext: string

  @return: the dictionary of directives and adjusted helptext
  @rtype: tuple of (dict, string)
  """
  ret = {}

  helptext = helptext.strip()
  lines = helptext.splitlines()

  i = len(lines) - 1
  while (i >= 0):
    mem = lines[i]
    founditem = 0
    for mem2 in _directives:
      if mem.find(mem2 + ": ") == 0:
        ret[mem2] = mem[len(mem2 + ": "):]
        founditem = 1
        break

    if founditem == 0:
      break

    i = i - 1

  return (ret, "\n".join(lines[:i+1]).strip())

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
