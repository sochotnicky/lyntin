"""
scrollers.py has Tk widgets for scrolling text
ScrolledANSI is the hairy beast that lives here now
for the protection of others.
"""

from Tkinter import *
from ScrolledText import ScrolledText
import os, tkFont
import ansi

# the complete list of foreground color codes and what color they
# map to in RGB.
fg_color_codes = {"30": "#000000",
                  "31": "#aa0000",
                  "32": "#00dd00",
                  "33": "#daa520",
                  "34": "#0000aa",
                  "35": "#bb00bb",
                  "36": "#00cccc",
                  "37": "#aaaaaa",
                  "b30": "#666666",
                  "b31": "#ff3333",
                  "b32": "#00ff3f",
                  "b33": "#ffff00",
                  "b34": "#2222ff",
                  "b35": "#ff33ff",
                  "b36": "#70eeee",
                  "b37": "#ffffff" }

# the complete list of background color codes and what color they
# map to in RGB.
bg_color_codes = {"40": "#000000",
                  "41": "#ff0000",
                  "42": "#00ff00",
                  "43": "#daa520",
                  "44": "#0000aa",
                  "45": "#ff00ff",
                  "46": "#00cccc",
                  "47": "#bbbbbb",
                  "b40": "#777777",
                  "b41": "#fa6072",
                  "b42": "#00ff7f",
                  "b43": "#ffff00",
                  "b44": "#2222ff",
                  "b45": "#ee82ee",
                  "b46": "#70eeee",
                  "b47": "#ffffff" }

class TkColor(ansi.ANSIColor):
  """A class with the ANSIColor interface that returns an appropriate
  Tk color tag for the ANSIColor settings.
  Since color tags are produced by this class it will setup any Tk
  widget to _use_ the tags it produces.  Do this to your widget before
  you try to get colors from this class.

  TkColor.setup_tk_color_tags(your_widget)
  color = TkColor(fg='white', bg='black', bold=1)
  your_widget.insert('end', 'Color this text', color.as_tuple())
  
  """
  def as_tuple(self):
    """return a tuple Tk understands that represents our color.
    we could do clever things so that tuple(TkColor()) would work but the
    explicit way is much less magic.
    """
    format = []
    fg = ""
    bg = ""

    # handle reverse
    if (not self.reverse):
      fg = self.fg
      bg = self.bg
    else:
      bg = self.fg
      fg = self.bg
    
    # handle bold
    if (self.bold):
      fg = "b" + str(fg)

    # handle underline
    if (self.underline):
      format.append("u")

    format.append(str(fg))
    if bg:
      format.append(str(bg))

    return tuple(format)
  def __str__(self):
    """We don't have a good string representation, so use a repr of our value"""
    return repr(self.as_tuple())

  def __repr__(self):
    return '<%s fg:%s bg:%s bold:%s underline:%s>' % tuple(map(str, (self.__class__.__name__, self.fg, self.bg, self.bold, self.underline)))
    
  def setup_tk_color_tags(tk_object):
    """ Sets up the Tk widget to understand the tags we make (fg/bg/u)."""
    for (ck, color) in fg_color_codes.items():
      tk_object.tag_config(ck, foreground=color)

    for (ck, color) in bg_color_codes.items():
      tk_object.tag_config(ck, background=color)

    tk_object.tag_config("u", underline=1)
    return
  setup_tk_color_tags = staticmethod(setup_tk_color_tags)
 
class ScrolledANSI(ScrolledText):
  """A ScrolledText widget that can handle ANSI colors"""

  def __init__(self, main_ui, **opts):
    # check our options, removing them from the dict
    self.handles_other_events = opts.pop('transfer_events_to', None)
    self.gets_our_focus = opts.pop('transfer_focus_to', None)

    # setup the tk call options
    # first setup our defaults
    tkdefaults = {'fg':'white', 'bg':'black', 'height':20}
    if os.name == 'posix':
      tkdefaults['font'] = tkFont.Font(family="Courier", size=12)
    else:
      tkdefaults['font'] = tkFont.Font(family="Fixedsys", size=12)
    # then update from the passed in options, these will overwrite our defaults
    tkdefaults.update(opts)
    
    ScrolledText.__init__(self, main_ui, **tkdefaults)

    # setup our default color and our ansi parsing object
    TkColor.setup_tk_color_tags(self)
    default_color = TkColor(fg='white', bg='black')
    self.ansistream = ansi.ANSIStream(default_color, TkColor)

    # DEBUG, remove this crud
    self.bind("<KeyPress>", self._ignoreThis)
    return
     
  def _ignoreThis(self, tkevent):
    """ This catches keypresses from the history buffer."""
    # kludge so that ctrl-c doesn't get caught allowing windows
    # users to copy the buffer....
    if tkevent.keycode == 17 or tkevent.keycode == 67:
      return

    if (self.gets_our_focus is not None):
      self.gets_our_focus.focus()

    if (self.handles_other_events is not None and tkevent.char):
      # we do this little song and dance so as to pass events
      # we don't want to deal with to the entry widget essentially
      # by creating a new event and tossing it in the event list.
      # it only sort of works--but it's the best code we've got
      # so far.
      args = ('event', 'generate', self.handles_other_events, "<KeyPress>")
      args = args + ('-rootx', tkevent.x_root)
      args = args + ('-rooty', tkevent.y_root)
      args = args + ('-keycode', tkevent.keycode)
      args = args + ('-keysym', tkevent.keysym)

      self.handles_other_events.tk.call(args)

    return "break"

  def write(self, text):
    """Convert ANSI to tk colors"""
    # we remove all \\r stuff because it's icky
    text = text.replace("\r", "")

    for (color, text) in self.ansistream.parse(text):
      self.insert('end', text, color.as_tuple())
      
    self._clipText()
    self._yadjust()
    return

  def color_write(self, text, **color_opts):
    color = TkColor(**color_opts)
    self.insert('end', text, color.as_tuple())
    return

  def _yadjust(self):
    """Handles y scrolling after text insertion."""
    self.yview('moveto', '1')
    # if os.name != 'posix':
    self.yview('scroll', '20', 'units')
    return
  
  def _clipText(self):
    """
    Scrolls the text buffer up so that the new text written at
    the bottom of the text buffer can be seen.
    """
    temp = self.index("end")
    ind = temp.find(".")
    temp = temp[:ind]
    if (temp.isdigit() and int(temp) > 800):
      self.delete ("1.0", "100.end")
    return

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
