#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: gag.py,v 1.4 2003/09/02 01:20:52 willhelm Exp $
#######################################################################
"""
This module defines gag functionality.
"""
import string
from lyntin import ansi, manager, utils, exported
from lyntin.modules import modutils

class GagData:
  def __init__(self):
    self._gags = {}
    self._antigags = []

  def addGag(self, item, gag):
    """
    Adds a gag to the dict.

    @param item: the item to gag
    @type  item: string

    @param gag: the thing to gag in place of "item"
    @type  gag: string
    """
    self._gags[item] = gag 

  def addAntiGag(self, item):
    """ Adds an antigag."""
    self._antigags.append(item)

  def clear(self):
    """
    Removes all the gags.
    """
    self._gags.clear()
    self._antigags = []

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

  def removeAntiGags(self, text):
    """
    Removes antigags from the list.

    @returns: a list of antigags that were removed.
    @rtype: list of strings
    """
    badgags = utils.expand_text(text, self._antigags)

    ret = []
    for mem in badgags:
      ret.append(mem)
      self._antigags.remove(mem)

    return ret

  def getGags(self):
    """
    Returns the keys of the gag dict.

    @returns: list of all the gag items
    @rtype: list of strings
    """
    listing = self._gags.keys()
    listing.sort()
    return listing

  def getAntiGags(self):
    """
    Returns the list of antigags that we have.

    @returns: list of all antigags
    @rtype: list of strings
    """
    return self._antigags

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
      for mem in self._antigags:
        if text.find(mem) != -1:
          return text

      # check for gags
      for mem in self._gags.keys():
        if ansi.filter_ansi(text).find(mem) != -1:
          tokens = ansi.split_ansi_from_text(text)
          text = []
          for mem in tokens:
            if ansi.is_color_token(mem):
              text.append(mem)
          return "".join(text)

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

    data = ["gag {%s} {%s}" % (mem, utils.escape(self._gags[mem])) for mem in data]

    return data

  def getAntiGagsInfo(self, text):
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
    data = self._antigags
    if text:
      data = utils.expand_text(text, data)

    data = ["antigag {%s}" % (mem) for mem in data]

    return data


  def getStatus(self):
    """
    Returns a one liner of number of gags we're managing.

    @returns: string describing how many gags and gags we're managing
    @rtype: string
    """
    gags = len(self._gags.keys())
    antigags = len(self._antigags)

    return "%d gag(s). %d antigag(s)" % (gags, antigags)


class GagManager(manager.Manager):
  def __init__(self):
    self._gags = {}

  def addGag(self, ses, item, gag):
    if not self._gags.has_key(ses):
      self._gags[ses] = GagData()
    self._gags[ses].addGag(item, gag)

  def addAntiGag(self, ses, item):
    if not self._gags.has_key(ses):
      self._gags[ses] = GagData()
    self._gags[ses].addAntiGag(item)

  def clear(self, ses):
    if self._gags.has_key(ses):
      self._gags[ses].clear()

  def removeGags(self, ses, text):
    if self._gags.has_key(ses):
      return self._gags[ses].removeGags(text)
    return []

  def removeAntiGags(self, ses, text):
    if self._gags.has_key(ses):
      return self._gags[ses].removeAntiGags(text)
    return []

  def getGags(self, ses):
    if self._gags.has_key(ses):
      return self._gags[ses].getGags()
    return []

  def getInfo(self, ses, text=''):
    if self._gags.has_key(ses):
      return self._gags[ses].getInfo(text)
    return []

  def getAntiGagsInfo(self, ses, text=''):
    if self._gags.has_key(ses):
      return self._gags[ses].getAntiGagsInfo(text)
    return []

  def getStatus(self, ses):
    if self._gags.has_key(ses):
      return self._gags[ses].getStatus()
    return "0 gag(s). 0 antigag(s)."

  def addSession(self, newsession, basesession=None):
    if basesession:
      if self._gags.has_key(basesession):
        sdata = self._gags[basesession]
        for mem in sdata._gags.keys():
          self.addGag(newsession, mem, sdata._gags[mem])

  def removeSession(self, ses):
    if self._gags.has_key(ses):
      del self._gags[ses]

  def expand(self, ses, text):
    if self._gags.has_key(ses):
      return self._gags[ses].expand(text)
    return text

  def persist(self, args):
    """
    write_hook function for persisting the state of our session.
    """
    ses = args["session"]
    quiet = args["quiet"]

    data = self.getInfo(ses) + self.getAntiGagsInfo(ses)

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

    if exported.get_config("ignoresubs", ses, 0) == 0:
      text = self.expand(ses, text)
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

  if not item:
    data = gm.getAntiGagsInfo(ses)
    if not data:
      data = ["antigag: no antigags defined."]

    exported.write_message("\n".join(data), ses)
    return

  gm.addAntiGag(ses, item)
  if not quiet:
    exported.write_message("antigag: {%s} added." % item, ses)

commands_dict["antigag"] = (antigag_cmd, "item= quiet:boolean=false")

def unantigag_cmd(ses, args, input):
  """
  Allows you to remove antigags.

  category: commands
  """
  func = exported.get_manager("gag").removeAntiGags
  modutils.unsomething_helper(args, func, ses, "antigag", "antigags")

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
  argument creates a gag.  gag accepts multiple gags at once, and
  accepts a quiet argument to supress reporting of what has been
  gagged.  

  examples:
    #gag {has missed you.}    <-- will prevent any incoming line
                                  with "has missed you" to be shown.
    #gag has missed you       <-- will gag any text with "has",
                                  "missed", or "you"

  category: commands
  """
  gaggedtext = args["text"]
  quiet = args["quiet"]

  gm = exported.get_manager("gag")

  if not gaggedtext:
    data = gm.getInfo(ses)
    if not data:
      data = ["gag: no gags defined."]

    exported.write_message("\n".join(data), ses)
    return

  for togag in gaggedtext:
    gm.addGag(ses, togag, ".")
    if not quiet:
      exported.write_message("gag: {%s} added." % togag, ses)

commands_dict["gag"] = (gag_cmd, "text* quiet:boolean=false")


def ungag_cmd(ses, args, input):
  """
  Allows you to remove gags.

  category: commands
  """
  gm = exported.get_manager("gag")

  func = gm.removeGags
  modutils.unsomething_helper(args, func, ses, "gag", "gags")

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
