#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: highlight.py,v 1.1 2003/05/05 05:56:02 willhelm Exp $
#######################################################################
"""
This module defines the HighlightManager which handles highlights.

Highlights can be used by the user to colorize text making it easier
for the user to glance and see what's going on quickly.

Note, if Lyntin's ansi is turned off, though, highlights won't happen.  
We might at some point want to highlight things with [[ ... ]] or 
something like that when ansi is off.
"""
import string
from lyntin import ansi, manager, utils, __init__, hooks, exported
from lyntin.modules import modutils


class HighlightData:
  def __init__(self):
    self._highlights = {}
    self._currcolor = list(ansi.DEFAULT_COLOR)
    self._colorleftover = ''

  def __copy__(self):
    hm = HighlightManager()
    for mem in self._highlights.keys():
      hm.addHighlight(self._highlights[mem][0], mem)
    return hm

  def addHighlight(self, style, text):
    """
    Adds a highlight to the dict.

    @param style: the style to highlight the text with
    @type  style: string

    @param text: the text to highlight
    @type  text: string
    """
    style = style.lower()
    markup, compiled = ansi.get_color(style), utils.compile_regexp(text, 0, 1)
    self._highlights[text] = (style, markup, compiled)

  def clear(self):
    """
    Removes all the highlights.
    """
    self._highlights.clear()

  def removeHighlights(self, text):
    """
    Removes highlights from the list.

    Returns a list of tuples of highlight item/highlight that
    were removed.

    @param text: we remove highlights that match this text
    @type  text: string

    @return: list of (text, style)
    @rtype: list of (string, string)
    """
    badhighlights = utils.expand_text(text, self._highlights.keys())

    ret = []
    for mem in badhighlights:
      ret.append((self._highlights[mem][0], mem))
      del self._highlights[mem]

    return ret

  def getHighlights(self):
    """
    Returns the keys of the highlight dict.

    @return: the list of highlight keys--which is the highlight text
    @rtype: list of strings
    """
    listing = self._highlights.keys()
    listing.sort()
    return listing

  def expand(self, text):
    """
    Looks at mud data and performs any highlights.

    It returns the final text--even if there were no highlights.

    @param text: the input text
    @type  text: string

    @return: the finalized text--even if no highlights were expanded
    @rtype: string
    """
    if text:
      faketext = ansi.filter_ansi(text)
      textlist = ansi.split_ansi_from_text(text)
      hlist = self._highlights.keys()
      hlist.sort()
      for mem in hlist:
        miter = self._highlights[mem][2].finditer(faketext)
        for m in miter:
          # we need to loop for multiple instances of the highlight
          begin, end = m.span()
          hl = self._highlights[mem][1]
          textlist = self.highlight(textlist, begin, end - begin, hl)

      # here we sweep through the text string to update our current
      # color and leftover color attributes
      self._currcolor, self._colorleftover = ansi.figure_color(textlist, self._currcolor, self._colorleftover)

      text = string.join(textlist, "")

    return text

  def highlight(self, textlist, place, memlength, hl):
    """
    Takes a bunch of stuff and applies the highlight involved.  
    It's messy.

    @param textlist: the list of strings representing the incoming
        text--this is usually text interspersed with ansi color tokens.
    @type textlist: list of strings

    @param place: the point in the text (skipping over ansi color stuff)
        that marks the beginning of the highlight
    @type  place: int

    @param memlength: the length of the string to be highlighted
    @type  memlength: int

    @param hl: the highlight to apply
    @type  hl: string

    @returns: the newly adjusted textlist
    @rtype: list of strings
    """
    # first we find the place to stick the highlight thingy.
    i = 0
    for i in range(0, len(textlist)):
      if not ansi.is_color_token(textlist[i]):
        if place > len(textlist[i]):
          place -= len(textlist[i])
        else:
          break

    newlist = textlist[:i]
    newlist.append(textlist[i][:place])
    newcolor = ansi.figure_color(newlist, self._currcolor)[0]
    newlist.append(hl)

    # if the string to highlight begins and ends in the
    # same token we deal with that and eject
    if len(textlist[i][place:]) >= memlength:
      newlist.append(textlist[i][place:place + memlength])
      newlist.append(chr(27) + "[0m")
      color = ansi.convert_tuple_to_ansi(newcolor)
      if color:
        newlist.append(color)
      newlist.append(textlist[i][place + memlength:])
      for mem in textlist[i+1:]:
        newlist.append(mem)

      return newlist


    newlist.append(textlist[i][place:])

    # now we have to find the end of the highlight
    memlength -= len(textlist[i][place:])
    j = i+1
    for j in range(i+1, len(textlist)):
      if not ansi.is_color_token(textlist[j]):
        if memlength > len(textlist[j]):
          memlength -= len(textlist[j])
          newlist.append(textlist[j])
        else:
          break
      else:
        newcolor = ansi.figure_color([textlist[j]], newcolor, '')[0]

    newlist.append(textlist[j][:memlength])
    newlist.append(chr(27) + "[0m")
    color = ansi.convert_tuple_to_ansi(newcolor)
    if color:
      newlist.append(color)
    newlist.append(textlist[j][memlength:])

    for mem in textlist[j+1:]:
      newlist.append(mem)

    return newlist

  def getInfo(self, text="", colorize=0):
    """
    Returns information about the highlights in here.

    This is used by #highlight to tell all the highlights involved
    as well as #write which takes this information and dumps
    it to the file.

    @param text: we return info on highlights that match this text
    @type  text: string

    @param colorize: whether (1) or not (0) to colorize the style
        text in the style
    @type  colorize: int

    @return: one big string of all the information
    @rtype: string
    """
    if len(self._highlights.keys()) == 0:
      return ''

    listing = self._highlights.keys()

    if text:
      listing = utils.expand_text(text, listing)

    data = []
    for mem in listing:
      if colorize == 1:
        data.append("%shighlight {%s%s%s} {%s}" % 
                    (__init__.commandchar, 
                     ansi.get_color(self._highlights[mem][0]),
                     self._highlights[mem][0], 
                     ansi.get_color("default"),
                     utils.escape(mem)))
      else:
        data.append("%shighlight {%s} {%s}" % 
                    (__init__.commandchar, self._highlights[mem][0], 
                     utils.escape(mem)))

    return string.join(data, "\n")

  def getStatus(self):
    """
    Returns a one-liner describing this data object

    @return: one liner describing this object
    @rtype: string
    """
    return "%d highlight(s)." % len(self._highlights.keys())


class HighlightManager(manager.Manager):
  def __init__(self):
    self._highlights = {}

  def addHighlight(self, ses, style, text):
    if not self._highlights.has_key(ses):
      self._highlights[ses] = HighlightData()
    self._highlights[ses].addHighlight(style, text)

  def clear(self, ses):
    if self._highlights.has_key(ses):
      self._highlights[ses].clear()

  def removeHighlights(self, ses, text):
    if self._highlights.has_key(ses):
      return self._highlights[ses].removeHighlights(text)
    return []

  def getHighlights(self, ses):
    if self._highlights.has_key(ses):
      return self._highlights[ses].getHighlights()
    return []

  def getInfo(self, ses, text="", colorize=0):
    if self._highlights.has_key(ses):
      return self._highlights[ses].getInfo(text, colorize)
    return ""

  def getStatus(self, ses):
    if self._highlights.has_key(ses):
      return self._highlights[ses].getStatus()
    return "0 highlight(s)."

  def addSession(self, newsession, basesession=None):
    if basesession:
      if self._highlights.has_key(basesession):
        hdata = self._highlights[basesession]
        for mem in hdata._highlights.keys():
          self.addHighlight(newsession, hdata._highlights[mem][0], mem)

  def removeSession(self, ses):
    if self._highlights.has_key(ses):
      del self._highlights[ses]

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

  def mudfilter(self, args):
    """
    mud_filter_hook function for filtering incoming data from the mud.
    """
    ses = args[0]
    text = args[-1]

    if __init__.ansicolor == 0:
      return ansi.filter_ansi(text)
    else:
      if self._highlights.has_key(ses):
        return self._highlights[ses].expand(text)

    return text

commands_dict = {}

def highlight_cmd(ses, args, input):
  """
  With no arguments, prints all highlights.
  With one argument, prints all highlights which match the arg.
  With multiple arguments, creates a highlight.

  Highlights enable you to colorfully "tag" text that's of interest
  to you with the given style.

  Styles available are:
     styles     foreground colors        background colors
     bold       black    grey            b black
     blink      red      light red       b red
     reverse    green    light green     b green
     underline  yellow   light yellow    b yellow
                blue     light blue      b blue
                magenta  light magenta   b magenta
                cyan     light cyan      b cyan
                white    light white     b white

  Highlights handle * at the beginning and end of non-regular expression
  texts.  Highlights will handle regular expression texts as well.  See
  "#help regexp" for more details.

  Note: blink, underline, and reverse may not be available in all ui's.

  examples:
    #highlight {green} {Sven arrives.}
    #highlight {reverse,green} {Sven arrives.}
    #highlight {blue} {r[^.*?says:]}

      which is the same as:

    #highlight {blue} {*says:}

  category: commands
  """
  style = args["style"]
  text = args["text"]
  quiet = args["quiet"]

  if not text and not style:
    data = exported.get_manager("highlight").getInfo(ses, "", 1)
    if not data:
      data = "highlight: no highlights defined."

    exported.write_message("highlights:\n" + data, ses)
    return

  if not text:
    data = exported.get_manager("highlight").getInfo(ses, style, 1)
    if not data:
      data = "highlight: no highlights defined."

    exported.write_message("highlights:\n" + data, ses)
    return
    
  style = style.lower()
  stylelist = style.split(",")
  for mem in stylelist:
    if mem not in ansi.STYLEMAP:
      exported.write_error("highlight: '%s' not a valid style.\n%shelp highlight for more information." % (mem, __init__.commandchar))
      return
    
  exported.get_manager("highlight").addHighlight(ses, style, text)
  if not quiet:
    exported.write_message("highlight: {%s} {%s} added." % (style, text), ses)

commands_dict["highlight"] = (highlight_cmd, "style= text= quiet:boolean=false")


def unhighlight_cmd(ses, args, input):
  """
  Allows you to remove highlights.

  examples:
    #highlight {hello}
    #highlight {blah*}

  category: commands
  """
  func = exported.get_manager("highlight").removeHighlights
  modutils.unsomething_helper(args, func, ses, "highlight", "highlights")

commands_dict["unhighlight"] = (unhighlight_cmd, "str= quiet:boolean=false")


hm = None

def load():
  """ Initializes the module by binding all the commands."""
  global hm
  modutils.load_commands(commands_dict)
  hm = HighlightManager()
  exported.add_manager("highlight", hm)

  hooks.mud_filter_hook.register(hm.mudfilter, 90)
  hooks.write_hook.register(hm.persist)

def unload():
  """ Unloads the module by calling any unload/unbind functions."""
  global hm
  modutils.unload_commands(commands_dict.keys())
  exported.remove_manager("highlight")
  hooks.mud_filter_hook.unregister(hm.mudfilter)
  hooks.write_hook.unregister(hm.persist)

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
