#######################################################################
# copyright (c) Free Software Foundation 2005
#
# UrwidUI is distributed under the GNU General Public License license.
# See http://www.gnu.org/licenses/gpl.txt for distribution details.
#######################################################################
"""
A user interface for Lyntin based on the urwid UI toolkit.

Features:
  + per-session windows with scrollback
  + simple color support (normal and bold colors, black background only)
  + per-session command histories
  + VI-like keybindings
  + non-session windows (windows created by the user & not tied to a session)

To be implemented:
  + underline attribute support
  + granular snoop (one can pick which sessions one wants to snoop on)
  + configurable coloring for lyntin messages
  + configurable scrollback buffer size
  + user defined keybindings
  + per-session keybindings

Credits:
  I stole some code & ideas from textui (general stuff) and
  cursesui (ansi color handling) written by willg & glassnake
  respectively. Everything else was written by davidc (me).

Notes:

  Urwid toolkit issue:

  Due to an issue with urwid 0.8.7 or lower, you have to wait approx.
  one second after you hit <Esc> before urwid decides that you really
  do want to just hit <Esc> and are not entering a control sequence.
  I've talked with the urwid maintainer (ian ward, ian at exess.org)
  and he says that these problems will be fixed in the next release.
  In the mean time, he's released a patch with a rework of urwid's
  input handling that addresses this issue.

    the patch:

       http://excess.org/urwid/patch-0.8.7.2.diff

  UI windows:

  There's no good way to tie the closing of a session associated window,
  to the zapping of one (without modifying/replacing zap), so for now,
  when you zap a session, the window remains, and you have to close it
  separately.

  Currently, the only way one can use use windows in any way other than
  the classical "session window" sense, is to write to it using the
  #window command. I would like to eventually allow text to be redirected
  or copied to windows, but I dont know if I can do that without modifying
  lyntin itself...we'll see (I haven't really looked at it much).

  Other:

  There seems to be some UI lockup bug that I haven't been able to track
  down. It happens sporadically for me...hopefully it wont for you. If
  it does, and you've got some ideas as to what it might be, please let
  me know.

Legal stuff:

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the
Software, and to permit persons to whom the Software is furnished
to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Copyright 2005 Free Software Foundation (http://www.fsf.org)
"""

__author__ = "David Clymer <david@zettazebra.com>"
__version__ = "0.6 (21 May, 2005)"
__description__ = "User interface for Lyntin based on the urwid UI toolkit"
__license__ = "GPL"
__url__ = "http://www.zettazebra.com/files/urwidui.py"

HELP = """
The urwidui is a simple UI for the text terminal.

General keybindings:

  To scroll, use PageUp/PageDown

Commandline editing:

  UrwidUI implements VI-like keybindings (VI is a ubiquitous text editor
  for Unix operating systems) for the purposes of commandline editing.

  To make things easy for those who are not familiar with VI, UrwidUI
  starts out in insert mode (the kind of editing most people expect)

  Insert Mode:

    Use Ctrl-p/Ctrl-n (previous/next) or the up/down arrow keys to
    navigate the command history

    Home/End takes you to the beginning & end of a line

    Enter executes the command you've typed in

    Escape switches to 'command' mode

  Command Mode:

    i switches to 'insert' mode

    k/j (previous/next) navigates the command history

    d[dwb^$] 'd' followed by one of the letters in brackets deletes
    some portion of the current line

    y[dwb^$] 'd' followed by one of the letters in brackets copies
    some portion of the current line

    p pastes the last deleted/copied item at the current cursor position

    x deletes a character at the current cursor position

"""
import sys, time
import base, urwid, urwid.curses_display, types, curses
from lyntin import exported, utils, ansi, event, history
from lyntin.ui import message

import logging

logging.basicConfig(filename='urwidui.log', level=logging.DEBUG)

myui = None

def get_ui_instance():
  logging.debug('UI instance requested.')

  global myui
  if myui == None:
    myui = UrwidUI()
  return myui


class Color:
  """
  Handles ANSI color decoding/markup
  """
  def __init__(self, ui):
    logging.debug("Class 'Color' initialized.")

    self.ui = ui
    self.unfinished = ''
    self.color_on = False
    self.colors = [
      'default',
      'black',
      'dark red',
      'dark green',
      'brown',
      'dark blue',
      'dark magenta',
      'dark cyan',
      'light gray',
      'dark gray',
      'light red',
      'light green',
      'yellow',
      'light blue',
      'light magenta',
      'light cyan',
      'white' ]

    if self.ui.s:
        self.colorize()

  def colorize(self):
      if not self.color_on:
          # define the colors that can be used to mark up text
          index = 0
          for fg in self.colors[1:]:
              self.ui.register_palette_entry( index, fg, 'black' )
              index += 1
          self.color_on = True

  def decode(self, text, continue_decode=True):
    """
    Take given ANSI colored text and produce an object usable by UrwidUI
    """
    text_out = []
    attribute = []

    if continue_decode and len(self.unfinished) > 0:
      current_color, leftover_color = self.unfinished
    else:
      leftover_color = ''
      current_color = list(ansi.DEFAULT_COLOR)

    for line in text.splitlines(1):

      # separate the text from the color codes
      tokens = ansi.split_ansi_from_text(leftover_color + line)

      # look at all the pieces
      for t in tokens:

        # it's a color code. figure out what it is
        if ansi.is_color_token(t):
          current_color, leftover_color = ansi.figure_color([t], current_color, leftover_color)

        # it's regular text, prepare it for display
        elif t:

          # does it have some sort of modifying attribute?
          if current_color[ansi.PLACE_BOLD]:
            attribute.append('bold')
          if current_color[ansi.PLACE_UNDERLINE]:
            attribute.append('underline')
          if current_color[ansi.PLACE_REVERSE]:
            attribute.append('reverse')

          foreground = current_color[ansi.PLACE_FG] - 30
          background = current_color[ansi.PLACE_BG] - 40

          text_out.append(self.getMarkup(t, (foreground, background, attribute) ))

          # prevent attributes from carrying over to text with out any set
          attribute = []

    self.unfinished = (current_color, leftover_color)

    return text_out


  def getMarkup(self, text, color):
    """
    Translate ANSI color markup to Urwid markup
    """
    fg, bg, a = color

    # get around the default colorpair -1, which ncurses is complaining about for some reason
    if fg < 0: fg = 7

    # its a bold attribute, so use bold colors
    if len(a) == 1 and a[0] == 'bold':
      fg += (len(self.colors) -1)/2
    # report specified but unsupported attributes to the user
    #elif len(a) > 1:
      # debug
      #logging.debug(' %s %s' % (str(a), text))

    return (fg, text)

class History(history.HistoryManager):
  """
  Text input history
  """
  def __init__(self):
    history.HistoryManager.__init__(self, exported.get_engine())
    logging.debug("Class 'History' initialized.")

    self.cursor = 0

  def setCursor(self, pos=-1):
    """
    Set the position of history cursor to the specified entry index
    """
    if pos > 0 and pos < len(self._history)-1 :
      self.cursor = pos
    else:
      self.cursor = 0

  def next(self):
    """
    Move to the following point in history
    """
    next = self._history[self.cursor]
    self.setCursor(self.cursor -1)
    return next

  def previous(self):
    """
    Move to the previous point in history
    """
    previous = self._history[self.cursor]
    self.setCursor(self.cursor +1)
    return previous

class KeyMode:
  """
  Collection of keys and the commands that each corresponds to
  """
  def __init__(self, keymap={}):
    logging.debug("Class 'Keymode' initialized.")

    self.keymap = keymap
    self.auto_revert = True
    self.command_keys_only = True

class VIkeyModeSet:
  """
  Keymode that emulates VI keybindings
  """
  def __init__(self):
    logging.debug("Class 'VIKeymodeSet' initialized.")

    self.modes = {}
    self.modes['command'] = KeyMode()
    self.modes['command'].keymap = {
     'i': 'mode insert',
     'l': 'move right',
     'h': 'move left',
     '$': 'move to end of line',
     '^': 'move to beginning of line',
     'w': 'move to next beginning of word',
     'b': 'move to previous beginning of word',
     'e': 'move to next end of word',
     'y': 'mode copy',
     'p': 'paste',
     'd': 'mode delete',
     'D': 'delete to end of line',
     'x': 'delete right',
     'k': 'history previous',
     'j': 'history next',
     'enter': 'execute command'
    }
    self.modes['command'].auto_revert = False

    self.modes['insert'] = KeyMode()
    self.modes['insert'].keymap = {
      'left': 'move left',
      'right': 'move right',
      'home': 'move to beginning of line',
      'end': 'move to end of line',
      'up': 'history previous',
      'down': 'history next',
      'ctrl p': 'history previous',
      'ctrl n': 'history next',
      'esc': 'mode command',
      'backspace': 'delete left',
      'delete': 'delete right',
      'enter': 'execute command'
    }
    self.modes['insert'].auto_revert = False
    self.modes['insert'].command_keys_only = False

    self.modes['copy'] = KeyMode()
    self.modes['copy'].keymap = {
     'y': 'copy line',
     '$': 'copy to end of line',
     '^': 'copy to beginning of line',
     'w': 'copy to next beginning of word',
     'b': 'copy to previous beginning of word',
     'e': 'copy to next end of word',
    }

    self.modes['delete'] = KeyMode()
    self.modes['delete'].keymap = {
     'd': 'delete line',
     '$': 'delete to end of line',
     '^': 'delete to beginning of line',
     'w': 'delete to next beginning of word',
     'b': 'delete to previous beginning of word',
     'e': 'delete to next end of word',
    }

class CommandModeManager:
  def __init__(self):
    logging.debug("Class 'CommandModeManager' initialized.")

    self.default_mode = 'default'
    self.current_mode = self.default_mode
    self.previous_mode = self.default_mode
    self.modes = {}
    self.changemode_hook = None

  def setDefault(self, name):
    if self.modes.has_key(name):
      if self.current_mode == self.default_mode:
        self.current_mode = name
      if self.previous_mode == self.default_mode:
        self.previous_mode = name

      self.default_mode = name

  def addMode(self, name, keymode=KeyMode()):
    self.modes[name] = keymode

  def removeMode(self, name):
    self.modes.pop(name,None)

  def keyAction(self, key):
    mode = self.modes[self.current_mode]
    if mode.keymap.has_key(key):
      action = mode.keymap[key]
      if action.startswith('mode '):
        self.changeMode(action.split(' ',1)[1].strip())
        return
      else:
        if mode.auto_revert: self.changeMode(self.default_mode)
        return action
    elif not mode.command_keys_only:
      return 'free input'
    else:
      if mode.auto_revert: self.changeMode(self.default_mode)
      return

  def changeMode(self, mode):
    if self.modes.has_key(mode):
      self.current_mode = mode
      if not self.changemode_hook == None:
        self.changemode_hook(self.current_mode)

  def registerChangeModeHook(self, func=None):
    if not func == None:
      self.changemode_hook = func

  def unregisterChangeModeHook(self):
    self.changemode_hook = None

class CommandEdit(urwid.Edit, History):
  def __init__(self, edit_prompt=''):
    urwid.Edit.__init__(self,edit_prompt)
    History.__init__(self)

    logging.debug("Class 'CommandEdit' initialized.")

    self.keymode = CommandModeManager()
    self.copy_buffer = ''
    self.end = len(self.edit_text)
    self.beginning = 0
    self.function_map = {
      'move right': self.move_right,
      'move left': self.move_left,
      'move to end of line': self.move_to_eol,
      'move to beginning of line': self.move_to_bol,
      'move to next beginning of word': self.move_next_bow,
      'move to previous beginning of word': self.move_prev_bow,
      'move to next end of word': self.move_next_eow,
      'move to previous end of word': self.move_prev_eow,
      'copy line': self.copy_line,
      'copy character': self.copy_right,
      'copy to end of line': self.copy_to_eol,
      'copy to beginning of line': self.copy_to_bol,
      'copy to next beginning of word': self.copy_next_bow,
      'copy to previous beginning of word': self.copy_prev_bow,
      'copy to next end of word': self.copy_next_eow,
      'copy to previous end of word': self.copy_prev_eow,
      'delete line': self.delete_line,
      'delete right': self.delete_right,
      'delete left': self.delete_left,
      'delete to end of line': self.delete_to_eol,
      'delete to beginning of line': self.delete_to_bol,
      'delete to next beginning of word': self.delete_next_bow,
      'delete to previous beginning of word': self.delete_prev_bow,
      'delete to next end of word': self.delete_next_eow,
      'delete to previous end of word': self.delete_prev_eow,
      'paste': self.paste,
      'history next': self.history_next,
      'history previous': self.history_previous,
      'execute command': self.execute_command
    }

  # -- [ utilities ] -- #

  def _find_whitespaces(self, text):
    spaces = []
    n = 0

    for c in text:
      if c.isspace(): spaces.append(n)
      n += 1

    return spaces

  def _find_word_boundaries(self, text):
    word_boundaries = []
    whitespace = self._find_whitespaces(text)
    end = len(text)-1

    # dont bother working on an empty string
    if end > 0:
      # add the first index, if it's not a space
      if not text[0].isspace():
        word_boundaries.append(0)

      # find all the characters on the edges of the whitespace
      for i in whitespace:
        # if an index is both the start and end of a word,
        # it will be added twice. this is important.
        if i != 0 and not text[i-1].isspace():
          word_boundaries.append(i-1)
        if i != end and not text[i+1].isspace():
          word_boundaries.append(i+1)

      # add the last index, if it's not a space
      if not text[end].isspace():
        word_boundaries.append(end)

      logging.debug('word boundaries: %s' % str(word_boundaries))

    return word_boundaries

  def _find_split_word_boundaries(self, text):
    word_boundaries = self._find_word_boundaries(text)
    word_endings = []
    word_beginnings = []
    end = len(word_boundaries)

    # every other boundary has to be a word end
    for x in range(0, end):
      if x % 2 == 0:
        word_beginnings.append(word_boundaries[x])
      else:
        word_endings.append(word_boundaries[x])

    logging.debug('word beginnnings: %s' % str(word_beginnings))
    logging.debug('word ends: %s' % str(word_endings))

    return (word_beginnings, word_endings)


  def _find_nearest_boundary(self, pos,  boundaries, lessthan = False):
    #if pos in boundaries:
    #  return boundaries.index(pos)

    end = len(boundaries)
    lower = 0
    upper = 0
    for x in range(0, end):
      if pos > boundaries[x]:
        lower = boundaries[x]
      elif pos == boundaries[x]:
        upper = boundaries[x]
      elif pos < boundaries[x]:
        upper = boundaries[x]
        break

    # start position is greater than the highest boundary
    if upper < lower:
      lessthan = True

    logging.debug('lower bound: %i, upper bound: %i' % (lower, upper))

    # return either the nearest upper boundary or the nearest lower boundary
    if lessthan:
      return lower
    else:
      return upper

  def _bounds_check(self, index):
    logging.debug('bounds checking index: %i' % index)

    if index < 0:
      logging.debug('index < 0, new index: 0')
      return 0
    elif index > self.end:
      logging.debug('index > %i (length of edit text), new index: %i' % (self.end, self.end))
      return self.end
    else:
      logging.debug('index within bounds')
      return index


  def keypress(self, size, key):
    function = self.keymode.keyAction(key)

    logging.debug("Widget CommandEdit handling key '%s' with function '%s'" % (key,function))

    if self.function_map.has_key(function):
      self.function_map[function]()
    elif function == 'free input':
      # keep from entering unbound meta keys, etc.
      if not len(key) > 1:
        self.insert_move_right(key)

    # debug
    #exported.write_message('[mode %s] %s: %s' % (self.keymode.current_mode,key,function))

  def history_next(self):
    self.set_edit_pos(0)
    self.set_edit_text(self.next())

  def history_previous(self):
    self.set_edit_pos(0)
    self.set_edit_text(self.previous())

  def execute_command(self):
    exported.lyntin_command(self.edit_text)
    self.recordHistory(self.edit_text)
    self.setCursor()
    self.set_edit_text('')

  # -- [ movement ] -- #

  def _move_char(self, increment=1):
    start_pos = self.edit_pos
    end_pos = start_pos + increment
    self.set_edit_pos(end_pos)

    return (start_pos, end_pos)

  def _move_word_boundary(self, increment=1, boundary_type='all'):
    btypes = ['all', 'beginning', 'ending']
    assert boundary_type in btypes, "Boundary type must be one of: %s" % str(btypes)

    start_pos = self.edit_pos
    end_pos = start_pos
    nearest = start_pos
    lessthan = False

    if increment < 0:
      lessthan = True

    if boundary_type == 'all':
      word_boundaries = self._find_word_boundaries(self.edit_text)
    else:
      (word_beginnings, word_endings) = self._find_split_word_boundaries(self.edit_text)

      if boundary_type == 'beginning':
        word_boundaries = word_beginnings
      elif boundary_type == 'ending':
        word_boundaries = word_endings

    logging.debug('start pos: %i, boundaries: %s' % (start_pos, str(word_boundaries)))

    nearest = self._find_nearest_boundary(start_pos, word_boundaries, lessthan)

    # don't allow wrapping
    if increment > 0 and nearest < start_pos:
      nearest = start_pos

    self.set_edit_pos(nearest)

    return (start_pos, nearest)

  def _move_line_boundary(self, increment=1):
    start_pos = self.edit_pos
    end_pos = self.end

    if increment < 0:
      end_pos = self.beginning

    self.set_edit_pos(end_pos)

    return (start_pos, end_pos)

  def move_to_eol(self):
    self._move_line_boundary(1)

  def move_to_bol(self):
    self._move_line_boundary(-1)

  def move_left(self):
    self._move_char(-1)

  def move_right(self):
    self._move_char(1)

  def move_next_bow(self):
    self._move_word_boundary(1, boundary_type='beginning')

  def move_prev_bow(self):
    self._move_word_boundary(-1, boundary_type='beginning')

  def move_next_eow(self):
    self._move_word_boundary(1, boundary_type='ending')

  def move_prev_eow(self):
    self._move_word_boundary(-1, boundary_type='ending')

  def copy_line(self):
    self.copy_buffer = self.edit_text

  def copy_to_eol(self):
    temp = self.edit_pos
    start, end = self._move_line_boundary(1)
    self.copy_buffer = self.edit_text[start:end]
    self.set_edit_pos(temp)

  def copy_to_bol(self):
    temp = self.edit_pos
    start, end = self._move_line_boundary(-1)
    self.copy_buffer = self.edit_text[end:start]
    self.set_edit_pos(temp)

  def copy_left(self):
    temp = self.edit_pos
    start, end = self._move_char(-1)
    self.copy_buffer = self.edit_text[end:start]
    self.set_edit_pos(temp)

  def copy_right(self):
    temp = self.edit_pos
    start, end = self._move_char(1)
    self.copy_buffer = self.edit_text[start:end]
    self.set_edit_pos(temp)

  def copy_next_bow(self):
    temp = self.edit_pos
    start, end = self._move_word_boundary(1, boundary_type='beginning')
    self.copy_buffer = self.edit_text[start:end]
    self.set_edit_pos(temp)

  def copy_prev_bow(self):
    temp = self.edit_pos
    start, end = self._move_word_boundary(-1, boundary_type='beginning')
    self.copy_buffer = self.edit_text[end:start]
    self.set_edit_pos(temp)

  def copy_next_eow(self):
    temp = self.edit_pos
    start, end = self._move_word_boundary(1, boundary_type='ending')
    self.copy_buffer = self.edit_text[start:end]
    self.set_edit_pos(temp)

  def copy_prev_eow(self):
    temp = self.edit_pos
    start, end = self._move_word_boundary(-1, boundary_type='ending')
    self.copy_buffer = self.edit_text[end:start]
    self.set_edit_pos(temp)

  def delete_to_eol(self):
    start, end = self._move_line_boundary(1)
    self.copy_buffer = self.edit_text[start:]
    self.set_edit_pos(start)
    self.set_edit_text(self.edit_text[:start])

  def delete_to_bol(self):
    start, end = self._move_line_boundary(-1)
    self.copy_buffer = self.edit_text[:start]
    self.set_edit_pos(end)
    self.set_edit_text(self.edit_text[:end])

  def delete_left(self):
    start, end = self._move_char(-1)
    self.copy_buffer = self.edit_text[end:start]
    self.set_edit_pos(end)
    self.set_edit_text(self.edit_text[:end] + self.edit_text[start:])

  def delete_right(self):
    start, end = self._move_char(1)
    self.copy_buffer = self.edit_text[start:end]
    self.set_edit_pos(start)
    self.set_edit_text(self.edit_text[:start] + self.edit_text[end:])

  def delete_next_bow(self):
    start, end = self._move_word_boundary(1, boundary_type='ending')
    junk, end = self._move_word_boundary(1, boundary_type='beginning')
    if end == self.end-1:
      end = self.end
    self.copy_buffer = self.edit_text[start:end]
    self.set_edit_pos(start)
    self.set_edit_text(self.edit_text[:start] + self.edit_text[end:])

  def delete_prev_bow(self):
    start, end = self._move_word_boundary(-1, boundary_type='beginning')
    self.copy_buffer = self.edit_text[end:start]
    self.set_edit_pos(end)
    self.set_edit_text(self.edit_text[:end] + self.edit_text[start:])

  def delete_next_eow(self):
    start, end = self._move_word_boundary(1, boundary_type='ending')
    end = self._bounds_check(end+1)
    self.copy_buffer = self.edit_text[start:end]
    self.set_edit_pos(start)
    self.set_edit_text(self.edit_text[:start] + self.edit_text[end:])

  def delete_prev_eow(self):
    start, end = self._move_word_boundary(-1, boundary_type='ending')
    self.copy_buffer = self.edit_text[end:start]
    self.set_edit_pos(end)
    self.set_edit_text(self.edit_text[:end] + self.edit_text[start:])

  def delete_line(self):
    self.copy_buffer = self.edit_text
    self.set_edit_pos(0)
    self.set_edit_text('')

  def insert(self, text):
    start = self.edit_pos
    self.insert_text(text)
    self.set_edit_pos(start)
    self.end = len(self.edit_text)

  def insert_move_right(self, text):
    self.insert_text(text)
    move_len = 0
    if self.edit_pos <= 0:
      move_len = len(text)
    self.end = len(self.edit_text)
    self.set_edit_pos(self.edit_pos + move_len)

  def set_edit_text(self, text):
    urwid.Edit.set_edit_text(self,text)
    self.end = len(self.edit_text)

  def set_edit_pos(self, pos):
    logging.debug('text: %s, old pos: %s, new pos: %s' % (self.edit_text,self.edit_pos, pos))
    self.end = len(self.edit_text)
    super(CommandEdit, self).set_edit_pos(self._bounds_check(pos))

  def paste(self):
    self.insert_move_right(self.copy_buffer)

class UIWindow:
  """
  Manages output of text to the user
  """
  def __init__(self, ui, header_text=''):
    """
    Initialize the UIWindow
    """
    logging.debug("Class 'UIWindow' initialized.")

    self.ui = ui

    # color management
    self.color = ui.color

    # experimental
    #self.lines = []

    # window elements
    self.header_text = '{ UrwidUI }   %s' % header_text
    self.items = {}
    self.output = urwid.Text('Welcome to Urwid UI for Lyntin.\n')
    self.blank = urwid.Divider('_')
    self.items[0] = self.output
    self.items[1] = self.blank
    self.listbox = urwid.ListBox(self.items)
    self.header = urwid.Text(self.header_text)
    self.frame = urwid.Frame(self.listbox, urwid.AttrWrap(self.header, 'header'))
    widget, pos = self.listbox.get_focus()
    self.listbox.set_focus( pos+2, coming_from='above' )

  def append(self, text):
    """
    Add text to the window

    @param text: string containing a line of text to be added to the window
    """
    text_out = self.color.decode(text)
    #for x in text_out :
    #  self.lines.append(x)

    # limit scrollback length
    #scroll_length = len(self.items)
    #if scroll_length  > 100:
    #  pass
      #exported.write_message('scroll_length: %i, show_len: %i' % (scroll_length, show_len))
      #self.items = self.items[show_len:]

    self.items[len(self.items)-2] = urwid.Text(text_out)
    self.items[len(self.items)-1] = self.blank

    scroll_len = len(self.items)
    if scroll_len % 10 == 0:
      logging.debug('Scrollback buffer length: %i' % scroll_len)

    #widget, pos = self.listbox.get_focus()
    #self.listbox.set_focus( pos+2, coming_from='above' )

  def handleInput(self):
    """
    Handle keystrokes as they are entered
    """
    keys = self.getKeys()
    size = self.getSize()

#    function = self.keymode.keyAction(key)
#    if self.function_map.has_key(function):
#      self.function_map[function]()

    for k in keys:
      logging.debug("Widget UIWindow recieved key '%s'" % k)
      self.frame.keypress( size, k )

    return True

  def draw(self):
    """
    Draws the session window
    """
    self.ui.draw_screen( self.getSize(), self.getCanvas() )
    self.ui.s.timeout(0)

  def getCanvas(self):
    return self.frame.render( self.getSize(), self.ui )

  def getSize(self):
    return self.ui.get_cols_rows()

  def getKeys(self):
    keys, raw_keys = self.ui.get_input(raw_keys=True)

    return keys

class UISession(UIWindow):
  """
  Manages input, output, and display for an individual session
  """
  def __init__(self, ui, header_text='', session=None):
    """
    Initialize the UISession
    """
    UIWindow.__init__(self,ui,header_text)

    logging.debug("Class 'UISession' initialized.")

    # session
    self.session = session

    # history managment
    self.history = History()

    # window elements
    self.input = CommandEdit(edit_prompt=('footer','Lyntin >> '))
    self.items[len(self.items)] = urwid.AttrWrap(self.input, 'footer')
    widget, pos = self.listbox.get_focus()
    self.listbox.set_focus( pos+2, coming_from='above' )

    # editing
    self.input.keymode.modes = VIkeyModeSet().modes
    self.input.keymode.registerChangeModeHook(self._changemode_hook)
    self.input.keymode.setDefault('command')
    self.input.keymode.changeMode('insert')

  def append(self, text):
    """
    Add text to the session window

    @param text: string containing a line of text to be added to the session window
    """
    UIWindow.append(self, text)

    self.items[len(self.items)] = self.input
    widget, pos = self.listbox.get_focus()
    self.listbox.set_focus( pos+2, coming_from='above' )

  def _changemode_hook(self, name):
    self.header.set_text('%s [mode %s]' % (self.header_text, name))
    logging.debug('changing to mode %s' % name)


class UrwidUI(base.BaseUI,urwid.curses_display.Screen):
  """
  User interface for Lyntin based on the urwid UI toolkit
  """
  def __init__(self):
    """
    Initialize the UrwidUI
    """
    base.BaseUI.__init__(self)

    logging.debug("Class 'UrwidUI' initialized.")

    self.WindowWriteError = Exception('Unable to write to specified window.')
    self.WindowNameError = Exception('Window with specified name already exists')
    self.WindowAbsentError = Exception('Window with specified name doest not exist')

    urwid.curses_display.Screen.__init__(self)
    self.register_palette([('header','white','dark red','standout'),('footer','white','dark blue','bold')])

    self.windows = {}
    self.focus=''
    exported.hook_register("session_change_hook", self._session_change)
    exported.hook_register("shutdown_hook", self.shutdown)
    exported.hook_register("to_user_hook", self.write)
    self.shutdownflag = False

    self.color = Color(self)

  def _session_change(self, args):
    new = args['new']
    old = args['previous']

    try:
      self.focus_window(new.getName())
    except self.WindowAbsentError:
      open_window(new.getName(),new)
    except Exception, e:
        logging.exception(e)
        exported.write_error(str(e))

  def screenIsReady(self):
    isReady = True
    if not self.s:
      isReady = False
      logging.debug('screen is not ready')

    return isReady

  def open_window(self, name, ses=None, focus=True):
    if self.windows.has_key(name):
      raise self.WindowNameError
    else:
      logging.debug('Opening window %s' % name)
      if not ses:
        #self.windows[name] = UIWindow(self, 'Window: %s' % name)
        self.windows[name] = UISession(self, 'Window: %s' % name)
      else:
        self.windows[name] = UISession(self, 'Session: %s' % ses.getName())

      if focus:
        self.windows[name].color.colorize()
        self.focus_window(name)

  def close_window(self, name):
    if self.windows.has_key(name):
      ses = exported.get_session(name)

      logging.debug('closing window %s' % name)

      if ses and ses.isConnected():
        exported.write_error("window '%s' still has an active session associated with it." % name)
        exported.write_error("Please close this session before removing its window")
      else:
        if ses:
          exported.get_engine().closeSession(ses)
          exported.write_message('closing session %s' % ses.getName())
          logging.info('closing session %s' % ses.getName())
        exported.write_message('closing window %s' % name)
        self.windows.pop(name)

  def write_to_window(self, name, text, ses=None, focus=True):
    logging.debug('writing to window %s' % name)

    if self.windows.has_key(name):
      self.windows[name].append(text)
    else:
      self.open_window(name, ses, focus)
      self.windows[name].append(text)

  def focus_window(self, name):
    if self.windows.has_key(name):
      if self.focus != name:
        logging.debug('change focus from %s to %s' % (self.focus,name))

      self.focus = name
      # sometimes on startup lyntin writes to the ui before urwid/curses
      # can get set up. lets avoid crashes.
      if self.screenIsReady():
        self.windows[name].draw()
    else:
      raise self.WindowAbsentError

  def runui(self):
    global HELP
    exported.add_help("urwidui", HELP)

    ses = exported.get_current_session()

    if ses == None:
      ses = exported.get_session('common')

    self.focus = ses.getName()

    exported.write_message("For urwidui help, type \"%shelp urwidui\"." % exported.get_config('commandchar', defaultvalue='#'))

    logging.debug('Running UI.')

    try:

      self.run_wrapper(self.main)
      logging.debug('run_wrapper terminated.')
      event.ShutdownEvent().enqueue()

    except SystemExit:
      print 'Thanks for using UrwidUI!'
      exported.write_traceback()
      event.ShutdownEvent().enqueue()

    except Exception, e:
        logging.exception(e)
        exported.write_traceback()
        event.ShutdownEvent().enqueue()

  def main(self):
    """
    Main loop of the UrwidUI

    keystrokes, drawing & updating the screen, and display of the
    appropriate session are all handled here
    """

    while not self.shutdownflag:
      try:
        ses = exported.get_current_session()

        self.focus_window(self.focus)

        if not self.windows[self.focus].handleInput():
          logging.debug('end of main loop')
          self.shutdown(args=None)

      except Exception, e:
          logging.exception(e)
          exported.write_traceback()
          event.ShutdownEvent().enqueue()


  def write(self, args):
    """
    Writes output to the user.  Output can come from the mud,
    Lyntin, or even user input being printed to the screen.  If
    the message argument is a String object rather than a Message
    object, the ui should assume it's Lyntin output.

    This method should be registered with the to_user_hook.

    @param args: either a string or a Message instance--this is
        the thing to be outputted to the user
    @type args: tuple holding either a string or a Message instance
    """
    msg = args["message"]

    if type(msg) == types.StringType:
      msg = message.Message(msg, message.LTDATA)
      logging.debug("ui message: message is a plain string")

    line = msg.data
    ses = msg.session

    pretext = ''
    if msg.type == message.ERROR or msg.type == message.LTDATA or msg.type == message.USERDATA:
      if msg.type == message.ERROR:
        pretext = "error: " + pretext
      else:
        pretext = "lyntin: " + pretext
        if msg.type == message.LTDATA:
          logging.debug("ui message: message is LTDATA")
          pass
        elif msg.type == message.USERDATA:
          logging.debug("ui message: message is USERDATA")
          pass
    elif msg.type == message.MUDDATA:
      logging.debug("ui message: message is MUDDATA")
      pass
    else:
      logging.debug("ui message: message is an unanticipated type: %s" % msg.type)
      pass



    # perhaps we'll let the user turn colors off, if they like
    #line = ansi.filter_ansi(pretext + utils.chomp(line).replace("\n", "\n" + pretext))
    line = pretext + utils.chomp(line).replace("\n", "\n" + pretext)

    # ------------------------------------- #
    # pick window representing this session #
    # ------------------------------------- #

    if ses == None:
      logging.debug("session: Session object is Null.")
      if exported.get_current_session() == None:
        ses = exported.get_session('common')
        logging.debug("session: Current session is Null. Session set to common.")
      else:
        ses = exported.get_current_session()

    self.write_to_window(ses.getName(), line, ses)

  def shutdown(self, args):
    """
    Tells the user interface thread to shutdown.  This is
    registered with the shutdown_hook.  Implement this method
    if you have shutdown stuff to do.

    @param args: it's an empty tuple--we ignore this
    @type  args: tuple of 0 length
    """
    logging.info('shutting down...')
    curses.endwin()
    self.shutdownflag = True


  def showTextForSession(self, ses):
    """
    Returns whether or not we should show text for this session--it's
    a convenience method.

    We return a 1 if the session is None, it doesn't have a _snoop
    attribute, it's the current session, or get_config("snoop", ses) == 1.

    @param ses: the session we're looking at--if it's None we return a 1
    @type  ses: Session

    @returns: 1 if we should show text, 0 if not
    @rtype: boolean
    """
    if ses == None \
        or exported.get_current_session() == ses \
        or exported.get_config("snoop", ses, 1) == 1:
      return 1
    return 0

  def handleinput(self, input):
    """
    Nicely handles enqueuing of input events.  Also deals with things
    like CR and LF.  Call this method with input that's just been
    polled from the user.

    @param input: the raw input from the user
    @type  input: string
    """
    from lyntin import event
    input = utils.chomp(input)
    logging.debug('Recieving input: "%s"' % input)
    event.InputEvent(input).enqueue()


# -=-=-=-=-=-=-=-=-=-=-=-[ user commands ]-=-=-=-=-=-=-=-=-=-=-=-=- #

commands_dict = {}

def window_cmd(ses, args, input):
  """
  Manages windows

    #window open      - open a new window
    #window close     - close a window
    #window focus     - bring a window to the forefront
    #window unfocus   - switch to the current session
    #window write     - send text to a window

  category: urwidui
  """
  #ui = exported.get_engine().getUI()
  ui = get_ui_instance()
  action = args['action']
  windowname = args['windowname']
  text = args['text']

  if action == 'list':
    exported.write_message('Urwid Windows:')
    for w in ui.windows.keys():
      if exported.get_session(w) != None:
        exported.write_message('  %s (session)' % w)
      else:
        exported.write_message('  %s' % w)
  elif action == 'open':
    if windowname != '':
      ui.open_window(windowname)
  elif action == 'close':
    if windowname != '':
      ui.close_window(windowname)
  elif action == 'focus':
    if windowname != '':
      ui.focus_window(windowname)
  elif action == 'unfocus':
    ui.focus_window(ses.getName())
  elif action == 'write':
    if windowname != '':
      ui.write_to_window(windowname,text,focus=False)
  else:
    exported.write_message('Invalid window action:  %s' % action)

commands_dict["window"] = (window_cmd, 'action windowname= text=')

def zap_cmd(ses, args, input):
  """
  This disconnects from the mud, closes the session, and any
  associated windw.  If no session is specified, it will
  close the current session.

  category: commands
  """
  sesname = args["session"]
  ui = exported.get_engine().getUI()
  if sesname:
    ses = exported.myengine.getSession(sesname)
    if ses == None:
      exported.write_error("zap: session %s does not exist." % sesname)
      return

  if exported.myengine.closeSession(ses):
    # close the session window
    ui.close_window(sesname)
    exported.write_message("zap: session %s zapped!" % ses.getName())
  else:
    exported.write_message("zap: session %s cannot be zapped!" % ses.getName())

commands_dict["zap"] = (zap_cmd, "session=")

def debug_cmd(ses, args, input):
  """
  Toggles debug log

  category: urwidui
  """
  global debugging_enabled

  if debugging_enabled:
    debugging_enabled = False
    exported.write_message('Debugging disabled.')
  else:
    debugging_enabled = True
    exported.write_message('Debugging enabled.')

commands_dict["debug"] = (debug_cmd, '')


def load_commands(args):
  from lyntin.modules import modutils
  modutils.load_commands(commands_dict)

exported.hook_register("startup_hook", load_commands)

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
