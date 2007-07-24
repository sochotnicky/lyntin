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
# $Id: substitute.py,v 1.10 2007/07/24 00:39:03 willhelm Exp $
#########################################################################
"""
This module defines the SubstituteManager which handles substitutes.
"""
from lyntin import ansi, manager, utils, exported
from lyntin.modules import modutils

class SubstituteData:
  def __init__(self):
    self._substitutes = {}
    self._antisubs = []

  def addSubstitute(self, item, substitute):
    """
    Adds a substitute to the dict.

    @param item: the item to substitute
    @type  item: string

    @param substitute: the thing to substitute in place of "item"
    @type  substitute: string
    """
    self._substitutes[item] = substitute 

  def addAntiSubstitute(self, item):
    """ Adds an antisubstitute."""
    self._antisubs.append(item)

  def clear(self):
    """
    Removes all the substitutes.
    """
    self._substitutes.clear()
    self._antisubs = []

  def removeSubstitutes(self, text):
    """
    Removes substitutes from the list.

    Returns a list of tuples of substitute item/substitute that
    were removed.

    @param text: substitutes matching text will be removed
    @type  text: string

    @returns: list of (item, substitute) tuples of removed substitutes
    @rtype: list of (string, string)
    """
    badsubstitutes = utils.expand_text(text, self._substitutes.keys())

    ret = []
    for mem in badsubstitutes:
      ret.append((mem, self._substitutes[mem]))
      del self._substitutes[mem]

    return ret

  def removeAntiSubstitutes(self, text):
    """
    Removes antisubstitutes from the list.

    @returns: a list of antisubstitutes that were removed.
    @rtype: list of strings
    """
    badsubs = utils.expand_text(text, self._antisubs)

    ret = []
    for mem in badsubs:
      ret.append(mem)
      self._antisubs.remove(mem)

    return ret

  def getSubstitutes(self):
    """
    Returns the keys of the substitute dict.

    @returns: list of all the substitute items
    @rtype: list of strings
    """
    listing = self._substitutes.keys()
    listing.sort()
    return listing

  def getAntiSubstitutes(self):
    """
    Returns the list of antisubs that we have.

    @returns: list of all antisubs
    @rtype: list of strings
    """
    return self._antisubs

  def expand(self, text):
    """
    Looks at mud data and performs any substitutes.

    It returns the final text--even if there were no substitutes.

    @param text: the text to expand substitutes in
    @type  text: string

    @return: the (un)adjusted text
    @rtype: string
    """
    # FIXME -- this isn't done correctly.
    if len(text) > 0:
      # check for antisubs first
      for mem in self._antisubs:
        if text.find(mem) != -1:
          return text

      # check for subs
      for mem in self._substitutes.keys():
        text = text.replace(mem, self._substitutes[mem])

    return text 

  def getInfo(self, text=''):
    """
    Returns information about the substitutes in here.

    This is used by #substitute to tell all the substitutes involved
    as well as #write which takes this information and dumps
    it to the file.

    @param text: the text used to figure out which substitutes to provide
        information on
    @type  text: string

    @return: list of strings where each string represents a substitute
    @rtype: list of strings
    """
    listing = self._substitutes.keys()
    if text:
      listing = utils.expand_text(text, listing)

    listing = ["substitute {%s} {%s}" % (mem, utils.escape(self._substitutes[mem])) for mem in listing]

    return listing

  def getSubstituteInfoMapping(self):
    l = []
    for mem in self._substitutes.keys():
      l.append( { "item": mem,
                  "substitution": utils.escape(self._substitutes[mem]) } )
    return l

  def getAntiSubstitutesInfo(self, text):
    """
    Returns information about the antisubstitutes in here.

    This is used by #antisubstitute to tell all the antisubstitutes involved
    as well as #write which takes this information and dumps it to the file.

    @param text: the text used to figure out which antisubstitutes to provide
        information on
    @type  text: string

    @return: list of strings where each string represents an antisubstitute
    @rtype: list of strings
    """
    listing = self._antisubs
    if text:
      listing = utils.expand_text(text, listing)

    listing = ["antisubstitute {%s}" % mem for mem in listing]

    return listing

  def getAntiSubstituteInfoMapping(self):
    l = []
    for mem in self._antisubs:
      l.append( {"item": mem } )
    return l

  def getStatus(self):
    """
    Returns a one liner of number of substitutes we're managing.

    @returns: string describing how many substitutes we're managing
    @rtype: string
    """
    subs = len(self._substitutes.keys())
    antisubs = len(self._antisubs)

    return "%d substitute(s).  %d antisub(s)." % (subs, antisubs)


class SubstituteManager(manager.Manager):
  def __init__(self):
    self._subs = {}

  def addSubstitute(self, ses, item, sub):
    if not self._subs.has_key(ses):
      self._subs[ses] = SubstituteData()
    self._subs[ses].addSubstitute(item, sub)

  def addAntiSubstitute(self, ses, item):
    if not self._subs.has_key(ses):
      self._subs[ses] = SubstituteData()
    self._subs[ses].addAntiSubstitute(item)

  def clear(self, ses):
    if self._subs.has_key(ses):
      self._subs[ses].clear()

  def removeSubstitutes(self, ses, text):
    if self._subs.has_key(ses):
      return self._subs[ses].removeSubstitutes(text)
    return []

  def removeAntiSubstitutes(self, ses, text):
    if self._subs.has_key(ses):
      return self._subs[ses].removeAntiSubstitutes(text)
    return []

  def getSubstitutes(self, ses):
    if self._subs.has_key(ses):
      return self._subs[ses].getSubstitutes()
    return []

  def getInfo(self, ses, text=''):
    if self._subs.has_key(ses):
      return self._subs[ses].getInfo(text)
    return []

  def getItems(self):
    return [ "substitute", "antisubstitute" ]

  def getParameters(self, item):
    if item == "substitute":
      return [ ("item", "The thing to substitute."),
               ("substitution", "The thing to substitute with.") ]

    if item == "antisubstitute":
      return [ ( "item", "The thing whose presence denotes we shouldn't substitute." ) ]

    raise ValueError("%s is not a valid item for this manager." % item)

  def getInfoMappings(self, item, ses):
    if item not in ["substitute", "antisubstitute"]:
      raise ValueError("%s is not a valid item for this manager." % item)
    
    if not self._subs.has_key(ses):
      return []

    if item == "substitute":
      return self._subs[ses].getSubstituteInfoMapping()

    return self._subs[ses].getAntiSubstituteInfoMapping()

  def getAntiSubstitutesInfo(self, ses, text=''):
    if self._subs.has_key(ses):
      return self._subs[ses].getAntiSubstitutesInfo(text)
    return []

  def getStatus(self, ses):
    if self._subs.has_key(ses):
      return self._subs[ses].getStatus()
    return "0 substitute(s). 0 antisub(s)."

  def addSession(self, newsession, basesession=None):
    if basesession:
      if self._subs.has_key(basesession):
        sdata = self._subs[basesession]
        for mem in sdata._substitutes.keys():
          self.addSubstitute(newsession, mem, sdata._substitutes[mem])

  def removeSession(self, ses):
    if self._subs.has_key(ses):
      del self._subs[ses]

  def expand(self, ses, text):
    if self._subs.has_key(ses):
      return self._subs[ses].expand(text)
    return text

  def persist(self, args):
    """
    write_hook function for persisting the state of our session.
    """
    ses = args["session"]
    quiet = args["quiet"]

    data = self.getInfo(ses) + self.getAntiSubstitutesInfo(ses)
    if not quiet:
      data = [m + " quiet={true}" for m in data]

    return data

  def mudfilter(self, args):
    """
    mud_filter_hook function to perform substitutions on data 
    that comes from the mud.
    """
    ses = args["session"]
    text = args["dataadj"]

    if exported.get_config("ignoresubs", ses, 0) == 0:
      text = self.expand(ses, text)
    return text


commands_dict = {}

def substitute_cmd(ses, args, input):
  """
  With no arguments, prints all substitutes.
  With one argument, prints all substitutes which match the argument.
  Otherwise creates a substitution.

  Braces are advised around both 'item' and 'substitution'.

  category: commands
  """
  item = args["item"]
  substitution = args["substitution"]
  quiet = args["quiet"]

  sm = exported.get_manager("substitute")

  if not substitution:
    data = sm.getInfo(ses, item)
    if not data:
      data = ["substitute: no substitutes defined."]

    exported.write_message("substitutes:\n" + "\n".join(data), ses)
    return 

  sm.addSubstitute(ses, item, substitution)
  if not quiet:
    exported.write_message("substitute: {%s} {%s} added." % (item, substitution), ses)

commands_dict["substitute"] = (substitute_cmd, "item= substitution= quiet:boolean=false")

def unsubstitute_cmd(ses, args, input):
  """
  Allows you to remove substitutes.

  category: commands
  """
  func = exported.get_manager("substitute").removeSubstitutes
  modutils.unsomething_helper(args, func, ses, "substitute", "substitutes")

commands_dict["unsubstitute"] = (unsubstitute_cmd, "str= quiet:boolean=false")

def antisubstitute_cmd(ses, args, input):
  """
  Allows you to create antisubstitutes.

  For any line that contains an antisubstitute, we won't do substitutions
  on it.

  category: commands
  """
  item = args["item"]
  quiet = args["quiet"]

  sm = exported.get_manager("substitute")

  if not item:
    data = sm.getAntiSubstitutesInfo(ses)
    if not data:
      data = ["antisubstitute: no antisubstitutes defined."]

    exported.write_message("antisubstitutes:\n" + "\n".join(data), ses)
    return

  sm.addAntiSubstitute(ses, item)
  if not quiet:
    exported.write_message("antisubstitute: {%s} added." % item, ses)

commands_dict["antisubstitute"] = (antisubstitute_cmd, "item= quiet:boolean=false")

def unantisubstitute_cmd(ses, args, input):
  """
  Allows you to remove antisubstitutes.

  category: commands
  """
  func = exported.get_manager("substitute").removeAntiSubstitutes
  modutils.unsomething_helper(args, func, ses, "antisubstitute", "antisubstitutes")

commands_dict["unantisubstitute"] = (unantisubstitute_cmd, "str= quiet:boolean=false")

sm = None

def load():
  """ Initializes the module by binding all the commands."""
  global sm
  modutils.load_commands(commands_dict)
  sm = SubstituteManager()
  exported.add_manager("substitute", sm)

  exported.hook_register("mud_filter_hook", sm.mudfilter, 50)
  exported.hook_register("write_hook", sm.persist)

  from lyntin import config
  for mem in exported.get_active_sessions():
    tc = config.BoolConfig("ignoresubs", 0, 1,
         "Allows you to turn on and turn off substitutions.")
    exported.add_config("ignoresubs", tc, mem)


def unload():
  """ Unloads the module by calling any unload/unbind functions."""
  global sm
  modutils.unload_commands(commands_dict.keys())
  exported.remove_manager("substitute")

  exported.hook_unregister("mud_filter_hook", sm.mudfilter)
  exported.hook_unregister("write_hook", sm.persist)

  # remove configuration items for every session involved
  for mem in exported.get_active_sessions():
    exported.remove_config("ignoresubs", mem)

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
