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
# $Id: gag.py,v 1.11 2007/07/24 00:39:03 willhelm Exp $
#########################################################################
"""
This module defines gag functionality.
"""
import string
from lyntin import ansi, manager, utils, exported
from lyntin.modules import modutils

class GagData:
  def __init__(self):
    self._gags = {}
    self._antigags = {}

  def addGag(self, item):
    """
    Adds a gag to the dict.

    @param item: the item to gag
    @type  item: string
    """
    compiled = utils.compile_regexp(item, 1)
    self._gags[item] = compiled

  def addAntiGag(self, item):
    """ Adds an antigag."""
    compiled = utils.compile_regexp(item, 1)
    self._antigags[item] = compiled

  def clear(self):
    """
    Removes all the gags.
    """
    self._gags.clear()
    self._antigags.clear()

  def removeGags(self, text):
    """
    Removes gags from the list.

    Returns a list of tuples of gag item/gag that
    were removed.

    @param text: gags matching text will be removed
    @type  text: string

    @returns: list of (item, gag) tuples of removed gags
    @rtype: list of (string, string)
    """
    badgags = utils.expand_text(text, self._gags.keys())

    ret = []
    for mem in badgags:
      ret.append(mem)
      del self._gags[mem]

    return ret

  def removeAntiGags(self, text=''):
    """
    Removes antigags from the list.

    @returns: a list of antigags that were removed.
    @rtype: list of strings
    """
    badgags = utils.expand_text(text, self._antigags.keys())

    ret = []
    for mem in badgags:
      ret.append(mem)
      del self._antigags[mem]

    return ret

  def getAntiGags(self):
    """
    Returns the list of antigags that we have.

    @returns: list of all antigags
    @rtype: list of strings
    """
    listing = self._antigags.keys()
    listing.sort()
    return listing

  def expand(self, text):
    """
    Looks at mud data and performs any gags.

    It returns the final text--even if there were no gags.

    @param text: the text to expand gags in
    @type  text: string

    @return: the (un)adjusted text
    @rtype: string
    """
    if len(text) > 0:
      # check for antigags first
      for mem in self._antigags.values():
        if mem.search(ansi.filter_ansi(text)):
          return text

      # check for gags
      for mem in self._gags.values():
        if mem.search(ansi.filter_ansi(text)):
          tokens = ansi.split_ansi_from_text(text)
          tokens = [m for m in tokens if ansi.is_color_token(m)]
          return "".join(tokens)

    return text 

  def getInfo(self, text=''):
    """
    Returns information about the gags in here.

    This is used by #gag to tell all the gags involved
    as well as #write which takes this information and dumps
    it to the file.

    @param text: the text used to figure out which gags to provide
        information on
    @type  text: string

    @return: list of strings where each string represents a gag
    @rtype: list of strings
    """
    data = self._gags.keys()
    if text:
      data = utils.expand_text(text, data)

    data = ["gag {%s}" % mem for mem in data]

    return data

  def getGagInfoMappings(self):
    l = []
    for mem in self._gags.keys():
      l.append( {"text": mem} )

    return l

  def getAntiGagsInfo(self, text=""):
    """
    Returns information about the antigags in here.

    This is used by #antigag to tell all the antigags involved
    as well as #write which takes this information and dumps it to the file.

    @param text: the text used to figure out which antigags to provide
        information on
    @type  text: string

    @return: list of strings where each string represents a gag
    @rtype: list of strings
    """
    data = self._antigags.keys()
    if text:
      data = utils.expand_text(text, data)

    data = ["antigag {%s}" % mem for mem in data]

    return data

  def getAntiGagInfoMappings(self):
    l = []
    for mem in self._antigags.keys():
      l.append( { "item": mem } )

    return l

  def getStatus(self):
    """
    Returns a one liner of number of gags we're managing.

    @returns: string describing how many gags and gags we're managing
    @rtype: string
    """
    gags = len(self._gags.keys())
    antigags = len(self._antigags.keys())

    return "%d gag(s). %d antigag(s)" % (gags, antigags)


class GagManager(manager.Manager):
  def __init__(self):
    self._gagdata = {}

  def getGagData(self, ses):
    if not self._gagdata.has_key(ses):
      self._gagdata[ses] = GagData()
    return self._gagdata[ses]
    
  def clear(self, ses):
    if self._gagdata.has_key(ses):
      self._gagdata[ses].clear()

  def getInfo(self, ses, text=''):
    return self.getGagData(ses).getInfo(text)

  def getItems(self):
    return ["gag", "antigag"]

  def getParameters(self, item):
    if item == "gag":
      return [ ( "text", "The text whose presence indicates we should gag the line." ) ]

    if item == "antigag":
      return [ ( "item", "The item whose presence indicates we shouldn't gag the line." ) ]

    raise ValueError("%s is not a valid item for this manager." % item)

  def getInfoMappings(self, item, ses):
    if item not in ["gag", "antigag"]:
      raise ValueError("%s is not a valid item for this manager." % item)

    if not self._gagdata.has_key(ses):
      return []

    if item == "gag":
      return self._gagdata.getGagInfoMappings()

    return self._gagdata.getAntiGagInfoMappings()

  def getStatus(self, ses):
    return self.getGagData(ses).getStatus()

  def addSession(self, newsession, basesession=None):
    if basesession:
      if self._gagdata.has_key(basesession):
        bdata = self.getGagData(basesession)
        ndata = self.getGagData(newsession)

        for mem in bdata._gags.keys():
          ndata.addGag(mem)
        for mem in bdata._antigags.keys():
          ndaga.addAntiGag(mem)

  def removeSession(self, ses):
    if self._gagdata.has_key(ses):
      del self._gagdata[ses]

  def persist(self, args):
    """
    write_hook function for persisting the state of our session.
    """
    ses = args["session"]
    quiet = args["quiet"]

    gd = self.getGagData(ses)
    data = gd.getInfo() + gd.getAntiGagsInfo()

    if quiet == 1:
      data = [m + " quiet={true}" for m in data]

    return data

  def mudfilter(self, args):
    """
    mud_filter_hook function to perform gagstitutions on data 
    that comes from the mud.
    """
    ses = args["session"]
    text = args["dataadj"]

    if exported.get_config("ignoresubs", ses, 0) == 0 and self._gagdata.has_key(ses):
      text = self._gagdata[ses].expand(text)
    return text


commands_dict = {}

def antigag_cmd(ses, args, input):
  """
  Allows you to create antigags.

  For any line that contains an antigag, we won't do gags on it.

  category: commands
  """
  item = args["item"]
  quiet = args["quiet"]

  gm = exported.get_manager("gag")
  gd = gm.getGagData(ses)

  if not item:
    data = gd.getAntiGagsInfo()
    if not data:
      data = ["antigag: no antigags defined."]

    exported.write_message("antigags\n" + "\n".join(data), ses)
    return

  gd.addAntiGag(item)
  if not quiet:
    exported.write_message("antigag: {%s} added." % item, ses)

commands_dict["antigag"] = (antigag_cmd, "item= quiet:boolean=false")

def unantigag_cmd(ses, args, input):
  """
  Allows you to remove antigags.

  category: commands
  """
  str = args["str"]
  quiet = args["quiet"]

  gm = exported.get_manager("gag")
  gd = gm.getGagData(ses)

  func = gd.removeAntiGags
  modutils.unsomething_helper(args, func, None, "antigag", "antigags")

commands_dict["unantigag"] = (unantigag_cmd, "str= quiet:boolean=false")

def gag_cmd(ses, args, input):
  """
  With no arguments, prints out all gags.
  With arguments, creates a gag.

  Incoming lines from the mud which contain gagged text will
  be removed and not shown on the ui.

  Gags get converted to regular expressions.  Feel free to use
  regular expression matching syntax as you see fit.

  As with all commands, braces get stripped off and each complete
  argument creates a gag.  

  examples:
    #gag {has missed you.}    <-- will prevent any incoming line
                                  with "has missed you" to be shown.
    #gag missed               <-- will gag lines with "missed" in them.
    #gag {r[sven.*?dealt]i}   <-- will gag anything that matches the
                                  regexp "sven.*?dealt" and ignore
                                  case.

  category: commands
  """
  gaggedtext = args["text"]
  quiet = args["quiet"]

  gm = exported.get_manager("gag")
  gd = gm.getGagData(ses)

  if not gaggedtext:
    data = gd.getInfo()
    if not data:
      data = ["gag: no gags defined."]

    exported.write_message("gags\n" + "\n".join(data), ses)
    return

  gd.addGag(gaggedtext)
  if not quiet:
    exported.write_message("gag: {%s} added." % gaggedtext, ses)

commands_dict["gag"] = (gag_cmd, "text= quiet:boolean=false")


def ungag_cmd(ses, args, input):
  """
  Allows you to remove gags.

  category: commands
  """
  str = args["str"]
  quiet = args["quiet"]

  gm = exported.get_manager("gag")
  gd = gm.getGagData(ses)

  func = gd.removeGags
  modutils.unsomething_helper(args, func, None, "gag", "gags")

commands_dict["ungag"] = (ungag_cmd, "str= quiet:boolean=false")


gm = None

def load():
  """ Initializes the module by binding all the commands."""
  global gm
  modutils.load_commands(commands_dict)
  gm = GagManager()
  exported.add_manager("gag", gm)

  exported.hook_register("mud_filter_hook", gm.mudfilter, 50)
  exported.hook_register("write_hook", gm.persist)

def unload():
  """ Unloads the module by calling any unload/unbind functions."""
  global gm
  modutils.unload_commands(commands_dict.keys())
  exported.remove_manager("gag")

  exported.hook_unregister("mud_filter_hook", gm.mudfilter)
  exported.hook_unregister("write_hook", gm.persist)

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
