#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: substitute.py,v 1.2 2003/05/27 02:06:39 willhelm Exp $
#######################################################################
"""
This module defines the SubstituteManager which handles substitutes and
gags.
"""
import string
from lyntin import ansi, manager, utils, __init__, exported
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

      # check for subs/gags
      for mem in self._substitutes.keys():
        if self._substitutes[mem] == ".":
          # handling gags
          if ansi.filter_ansi(text).find(mem) != -1:
            tokens = ansi.split_ansi_from_text(text)
            text = []
            for mem in tokens:
              if ansi.is_color_token(mem):
                text.append(mem)
            return "".join(text)
        else:
          # handling regular substitutes
          if self._substitutes[mem] == r"\.":
            text = text.replace(mem, ".")
          else:
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

    @return: the string of the substitute information
    @rtype: string
    """
    if len(self._substitutes.keys()) == 0:
      return ''

    if text=='':
      listing = self._substitutes.keys()
    else:
      listing = utils.expand_text(text, self._substitutes.keys())

    listing = ["%ssubstitute {%s} {%s}" % (__init__.commandchar, mem, utils.escape(self._substitutes[mem])) for mem in listing]

    return string.join(listing, "\n")

  def getAntiSubstitutesInfo(self, text):
    """
    Returns information about the antisubstitutes in here.

    This is used by #antisubstitute to tell all the antisubstitutes involved
    as well as #write which takes this information and dumps it to the file.

    @param text: the text used to figure out which antisubstitutes to provide
        information on
    @type  text: string

    @return: the string of the antisubstitute information
    @rtype: string
    """
    if len(self._antisubs) == 0:
      return ''

    if text=='':
      listing = self._antisubs
    else:
      listing = utils.expand_text(text, self._antisubs)

    listing = ["%santisubstitute {%s}" % (__init__.commandchar, mem) for mem in listing]

    return string.join(listing, "\n")


  def getStatus(self):
    """
    Returns a one liner of number of substitutes we're managing.

    @returns: string describing how many substitutes and gags we're managing
    @rtype: string
    """
    gags = 0
    subs = 0

    for mem in self._substitutes.keys():
      if self._substitutes[mem] == ".":
        gags += 1
      else:
        subs += 1
    antisubs = len(self._antisubs)

    return "%d substitute(s). %d gag(s). %d antisub(s)" % (subs, gags, antisubs)


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
    return ""

  def getAntiSubstitutesInfo(self, ses, text=''):
    if self._subs.has_key(ses):
      return self._subs[ses].getAntiSubstitutesInfo(text)
    return ""

  def getStatus(self, ses):
    if self._subs.has_key(ses):
      return self._subs[ses].getStatus()
    return "0 substitute(s). 0 gag(s). 0 antisub(s)."

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
    file = args["file"]
    quiet = args["quiet"]

    data = self.getInfo(ses)
    if data:
      if quiet == 1:
        data = data.replace("\n", " quiet={true}\n")
        file.write(data + " quiet={true}\n")
      else:
        file.write(data + "\n")
      file.flush()

    data = self.getAntiSubstitutesInfo(ses)
    if data:
      if quiet == 1:
        data = data.replace("\n", " quiet={true}\n")
        file.write(data + " quiet={true}\n")
      else:
        file.write(data + "\n")
      file.flush()

  def mudfilter(self, args):
    """
    mud_filter_hook function to perform substitutions on data 
    that comes from the mud.
    """
    ses = args["session"]
    text = args["dataadj"]

    if not ses._ignoresubs:
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

  if not item and not substitution:
    data = sm.getInfo(ses)
    if data == '':
      data = "substitute: no substitutes defined."

    exported.write_message(data, ses)
    return

  if not substitution:
    data = sm.getInfo(ses, item)
    if data == '':
      data = "substitute: no substitutes defined."

    exported.write_message(data, ses)
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
  or gags on it.

  category: commands
  """
  item = args["item"]
  quiet = args["quiet"]

  sm = exported.get_manager("substitute")

  if not item:
    data = sm.getAntiSubstitutesInfo(ses)
    if data == '':
      data = "antisubstitute: no antisubstitutes defined."

    exported.write_message(data, ses)
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

  sm = exported.get_manager("substitute")

  if not gaggedtext:
    data = sm.getInfo(ses)
    if data == '':
      data = "gag: no gags defined."

    exported.write_message(data, ses)
    return

  for togag in gaggedtext:
    sm.addSubstitute(ses, togag, ".")
    if not quiet:
      exported.write_message("gag: {%s} added." % togag, ses)

commands_dict["gag"] = (gag_cmd, "text* quiet:boolean=false")


def ungag_cmd(ses, args, input):
  """
  Allows you to remove gags.

  category: commands
  """
  sm = exported.get_manager("substitute")

  func = sm.removeSubstitutes
  modutils.unsomething_helper(args, func, ses, "gag", "gags")

commands_dict["ungag"] = (ungag_cmd, "str= quiet:boolean=false")


sm = None

def load():
  """ Initializes the module by binding all the commands."""
  global sm
  modutils.load_commands(commands_dict)
  sm = SubstituteManager()
  exported.add_manager("substitute", sm)

  exported.hook_register("mud_filter_hook", sm.mudfilter, 50)
  exported.hook_register("write_hook", sm.persist)

def unload():
  """ Unloads the module by calling any unload/unbind functions."""
  global sm
  modutils.unload_commands(commands_dict.keys())
  exported.remove_manager("substitute")

  exported.hook_unregister("mud_filter_hook", sm.mudfilter)
  exported.hook_unregister("write_hook", sm.persist)

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
