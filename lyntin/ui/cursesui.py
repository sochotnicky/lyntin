#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2003-2007
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
#######################################################################
"""
This is curses based ui module for Lyntin.
"""

__author__ = "glasssnake <glassnake@ok.ru>"
__version__ = "0.5"
__license__ = "GPLv3"


import sys, types, string, thread, select, os
from time import time
from lyntin import ansi, event, utils, exported, config, modules
from lyntin.ui import base, message
import curses, curses.wrapper
from curses import ascii

HELP_TEXT = """
Cursesui - the curses user interface for Lyntin.

Features implemented:
- input line editing with common unix-like keys
- key binding
- input history search
- flood protection
- scrollback

Features which are NOT implemented yet:

- named windows
- turning echo off
- status line

It is simplistic substitution for in-stock Lyntin textui. The Cursesui allows
you to edit input line (it is not so powerful as readline, but basic editing
and history navigation are there) and scroll the text back to look at the
earlier MUD output.

The keys are:
- Left, Right, Home, End, C-E, C-A, C-B, C-F - to navigate in input line;
- C-U - kill input line contents;
- Up, Down - history navigation;
- C-L - force screen to redraw;
- PageUp, PageDown - scroll back ang forth in history window;
- Escape - shut the scrollback window if opened (double escape will do also).

You can configure several cursesui parameters with "config" lyntin command;
look at config parameters that starts with "curses.".

"""

myui = None


##
#
# Key binding dictionaries and user commands:
#
#

# The dictionary has the structure:
# { <keyboard-sequence>:
#       ( <printable-form-of-the-sequence>, <responce> ) }
bindings = {}

#
# Keypress names from the curses module:
#
keytext = {}        # keyname -> keycode
keyvalue = {}       # keycode -> keyname
for key in dir(curses):
  if key.startswith("KEY_"):
    value = getattr(curses, key)
    keytext[value] = key
    keyvalue[ key ] = value
#for key in curses.ascii.controlnames:
#  value = getattr(curses.ascii, key)
#  keyvalue[key] = value
#  if not keytext.has_key(value):
#    keytext[value] = key
  

def curses_bind_cmd(ses, args, input):
  """
  Binds a hotkey to sequence.

  Examples:

  #curses.bind <ESC>q #end
  #curses.bind <ESC>h {reply hello}
  #curses.bind KEY_F1 #help

  If "responce" is missing, then shows the current binding for given key.

  If "key" is missing, then lists all the bindings.
  
  If "curses.keydebug" config parameter is set to 1, then
  you can check keycodes immediately pressing them.
  """
  keyarg = args["key"]
  responce = args["responce"]
  key = ""
  if keyarg:
    # check for KEY_F1 argument form:
    special = keyvalue.get(keyarg)
    if special:
      key = keyarg
    else:
      key = keyarg.replace("<ESC>", "\x1b")
  if responce:
    tuple = (keyarg, responce)
    bindings[key] = tuple
    if not args["quiet"]:
      exported.write_message("Sequence %s is bound to %s" % tuple)
  elif key:
    tuple = bindings.get(key)
    if tuple:
      exported.write_message("%s: %s" % tuple)
    else:
      exported.write_message("Nothing is bound to "+key)
  else:
    data = bindings.values()
    if data:
      exported.write_message("Current bindings:")
      data.sort( lambda x, y: cmp(x[0], y[0]) )
      for tuple in data:
        exported.write_message("%s: %s" % tuple)
    else:    
      exported.write_message("No bindings.")


def curses_unbind_cmd(ses, args, input):
  """
  Unbinds given key, so pressing it will give no (or system default) responce.
  """
  keyarg = args["key"]
  special = keyvalue.get(keyarg)
  if special:
    key = keyarg
  else:
    key = keyarg.replace("<ESC>", "\x1b").replace("<CR>", "\n")
  for (sequence, tuple) in bindings.items():
    if key == tuple[0]:
      del bindings[sequence]
      if not args["quiet"]:
        exported.write_message(key + " is unbound")
      return


# 
# Loads the command dictionary - it should be done exactly
# at the "startup_hook", not earlier.
#
def startup_hook(args):
  modules.modutils.load_commands( {
    'curses.bind':
        (curses_bind_cmd, 'key= responce= quiet:boolean=false'),
    'curses.unbind':
        (curses_unbind_cmd, 'key quiet:boolean=false')
    } )

#
# Persistance function, for saving of current bindings with #write
#
def bindings_persist(args):
  quiet = args["quiet"]
  values = bindings.values()
  values.sort( lambda x, y: cmp(x[0], y[0]) )
  data = []
  for (seq, responce) in values:
    data.append("curses.bind {%s} {%s}" %
                (seq, responce.replace('\\', '\\\\').replace('$', '\\$')))
  if args["quiet"]:
    data = [x + " quiet=true" for x in data]
  return data  


#
# Kind of hack - ascii.isprint should be enough, but the curses.ascii module
# is broken (not locale-aware).
# 
def is_a_char(ch):
  return (ascii.isprint(ord(ch)) or ch in string.letters)


#
# Shuts curses down
#
def endcurses():
  curses.nl()
  curses.echo()
  curses.noraw()
  curses.endwin()
  

def curses_fore(color):
  return color * 256
  

def curses_back(color):
  return color * 8 * 256
  

def curses_color(fore, back):
  return ( back * 8 + fore ) * 256


color_lookup = {
  'white':  curses.A_BOLD,
  'grey':   curses.A_NORMAL,
  'red':    curses_fore(curses.COLOR_RED),
  'green':  curses_fore(curses.COLOR_GREEN),
  'blue':   curses_fore(curses.COLOR_BLUE),
  'brown':  curses_fore(curses.COLOR_YELLOW),
  'yellow':  curses_fore(curses.COLOR_YELLOW) | curses.A_BOLD,
  'magenta': curses_fore(curses.COLOR_MAGENTA),
  'cyan': curses_fore(curses.COLOR_CYAN)
}


#
# Custom config class for color selection.
#
class ColorConfig(config.StringConfig):
  def check(self, value):
    config.StringConfig.check(self, value)
    if not value in color_lookup.keys():
      raise TypeError("Value is not in set: " + "|".join(color_lookup.keys()))
    return value
    
  def toString(self):
    return "".join((repr(self._value), " (", "|".join(color_lookup.keys()), ")"))
 

_config_items = (
  ("curses.lazy", config.IntConfig, 0, "How lazy the curses redrawing is.\nActual output of text from remote server will be performed either when keyboard will become idle or after 'curses.lazy' lines of output will arrive.  When laziness is 0 (the default) the output will be performed after each portion of data from remote server."),
  ("curses.maxscrollback", config.IntConfig, 1000, "Number of lines that can be scrolled back."),
  ("curses.attr.session", ColorConfig, "magenta", "Another session output notification color."),
  ("curses.attr.user", ColorConfig, "brown", "User input color."),
  ("curses.attr.lyntin", ColorConfig, "green", "Lyntin message prefix color."),
  ("curses.attr.error", ColorConfig, "red", "Error message prefix color."),
  ("curses.compact", config.BoolConfig, 0, "Remove empty lines from output."),
  ("curses.keydebug", config.BoolConfig, 0, "Output keypresses for debugging.")
)

def get_ui_instance():
  global myui
  if myui == None:
    for (name, ctr, default, comment) in _config_items:
      exported.add_config(name, ctr(name, default, 1, comment))
    myui = Cursesui()
  return myui


# 
# Window-like object that can "scroll"
#
class scroller:
  def __init__(self, window, lines):
    self.window_ = window
    self.lines_ = lines
    (self.h_, self.w_) = window.getmaxyx()
    self._set_startline(1000000)
    
  def _set_startline(self, startline):
    self.startline_ = max(0, min( len(self.lines_)-self.h_, startline))
   
  def redraw(self, scroll=0, **kargs):
    #
    # Redraws window with lines from attached list, starting from
    # self.startline_.
    #
    if 'startline' in kargs:
      self._set_startline(kargs['startline'])
    else:
      self._set_startline(self.startline_+scroll)

    current_y = 0
    
    self.window_.erase()

    for lineattrs in self.lines_[self.startline_:self.startline_+self.h_]:

      current_x = 0
    
      if current_y >= self.h_:
        current_y = self.h_ - 1
        self.window_.move(0, 0)
        self.window_.deleteln()

      for (line, attr) in lineattrs:
        line = filter(is_a_char, line)
        rest = self.w_-current_x-1
        current_len = len(line)
        offset = 0
        while current_len >= rest:
          self.window_.addnstr(current_y, current_x, line[offset:], rest, attr)
          current_x = 0
          current_y += 1
          if current_y >= self.h_:
            current_y = self.h_ - 1
            self.window_.move(0, 0)
            self.window_.deleteln()
          offset += rest  
          current_len -= rest
          rest = self.w_-1
        if current_len:  
          self.window_.addstr(current_y, current_x, line[offset:], attr)
          current_x += current_len    
      current_y += 1

    self.window_.noutrefresh()

    return self.startline_
      

class inputbox:

  def __init__(self, ui, win, string=""):
    self.string_ = string

    # index of first visible letter of the string
    self.offset_ = 0

    # current index in string
    self.curx_ = len(string)
    
    self.ui_ = ui

    # self.startx_ = 0
    self.attach(win)
    self._reset()


  def _reset(self):
    self.history_ = []   # history search buffer
    self.ui_.reset_completion()

  def attach(self, window):
    self.window_ = window
    window.keypad(1)
    window.timeout(10) # keyboard polling timeout, milliseconds
    (y, self.width_) = window.getmaxyx()
    self._align(force=1)

  def set(self, string):
    self.string_ = string
    self.curx_ = len(string)
    self.offset_ = 0
    self._align(force=1)

  def get_string(self):
    return self.string_

  def _align(self, force=0):
    maxright = self.width_-1
    if self.curx_ - self.offset_ > maxright:
      self.offset_ = self.curx_ - maxright
      force = 1
    elif self.curx_ < self.offset_:
      self.offset_ = self.curx_
      force = 1
    if force:
      substr = self.string_[self.offset_:(self.offset_+maxright)]
      self.window_.addstr(0, 0, substr)
      self.window_.clrtoeol()
      self.window_.noutrefresh()
    self.window_.move(0, self.curx_-self.offset_)

  def do_command(self, ch):
    if ch == -1:
      pass
    if (ch & ~0xFF)==0 and (ascii.isprint(ch) or chr(ch) in string.letters):
      self.string_ = self.string_[:self.curx_]+chr(ch)+self.string_[self.curx_:]
      self.curx_ += 1
      self._align(1)
      self._reset()
    elif ch in (ascii.BS, ascii.DEL, curses.KEY_BACKSPACE):
      if self.curx_ > 0:
        self.curx_ -= 1
        self.string_ = self.string_[0:self.curx_] + self.string_[self.curx_+1:]
        self._align(1)
      self._reset()  
    elif ch == ascii.HT:
      newtext, newposition = self.ui_.get_completion(self.string_, self.curx_)
      self.set(newtext)
      self.curx_ = newposition
      self._align(1)
    elif ch in (ascii.SOH, curses.KEY_HOME): # ^a
      self.curx_ = 0
      self._align()
      self._reset()  
    elif ch in (ascii.STX, curses.KEY_LEFT): # ^b    
      if self.curx_ > 0:
        self.curx_ -= 1
        self._align()
      self._reset()  
    elif ch in (ascii.ACK, curses.KEY_RIGHT): # ^f
      if self.curx_ < len(self.string_):
        self.curx_ += 1
        self._align()
      self._reset()  
    elif ch in (ascii.EOT, curses.KEY_DC): # ^d
      if self.curx_ < len(self.string_):
        self.string_ = self.string_[0:self.curx_] + self.string_[self.curx_+1:]
        self._align(1)
      self._reset()  
    elif ch in (ascii.ENQ, curses.KEY_END): # ^e
      self.curx_ = len(self.string_)
      self._align()
      self._reset()  
    elif ch in (ascii.DLE, curses.KEY_UP): # ^p
      #
      # search the history back
      #
      if not self.history_:
        self.history_ = filter( lambda x: x.find(self.string_) != -1,
                                exported.get_history(1000) )
      if self.history_:
        found = self.history_[0]
        self.history_[0:1] = []
        self.history_.append(found)
        self.set( found )

    elif ch in (ascii.SO, curses.KEY_DOWN): # ^n
      #
      # search the history forward
      #
      if self.history_:
        self.history_.insert(0, self.history_.pop())
        self.set( self.history_[-1] )
    
    elif ch in (ascii.NAK,): # ^U
      #
      # Kill the line, reset the history search
      #
      self._reset()
      self.set("")

    # elif ch in (ascii.DLE,): # ^r
    #   pass

    elif ch in (ascii.CR, ascii.LF):
      #
      # reset the history search
      #
      self._reset()

    # elif ch == curses.KEY_RESIZE:
    #   pass

    return ch



class Cursesui(base.BaseUI):
  #
  # This is the curses ui.
  # 
  def __init__(self):
    base.BaseUI.__init__(self)
    
    exported.hook_register("startup_hook", startup_hook)
    exported.hook_register("to_user_hook", self.write)
    exported.hook_register("config_change_hook", self.config_changed)
    exported.hook_register("bell_hook", lambda x: sys.stdout.write('\07'))
    exported.hook_register("prompt_hook",
      lambda x: self.write( {
        'message': message.Message(x["prompt"], message.MUDDATA, x["session"])
        } ) )
    exported.hook_register("write_hook", bindings_persist)

    self.unfinished_ = {}

    self.prompt_ = [("", curses.A_NORMAL)]
    self.lines_ = [ self.prompt_ ]
    self.prompt_index_ = 0

    self.running_ = 1

    self.cfg_lazy_ = exported.get_config("curses.lazy")
    self.cfg_maxscrollback_ = exported.get_config("curses.maxscrollback")
    self.cfg_keydebug_ = exported.get_config("curses.keydebug")
    self.cfg_compact_ = exported.get_config("curses.compact")
    self.cfg_echo_ = exported.get_config("mudecho")

    global color_lookup
    self.attr_error_= color_lookup[exported.get_config("curses.attr.error")]
    self.attr_session_= color_lookup[exported.get_config("curses.attr.session")]
    self.attr_lyntin_= color_lookup[exported.get_config("curses.attr.lyntin")]
    self.attr_user_= color_lookup[exported.get_config("curses.attr.user")]

    self.output_ = os.pipe()  # MUD output signalling pipe

    
  def prompt(self):
    # I don't want any prompt
    pass
    

  def shutdown(self, args):
    self.running_ = 0
      

  def config_changed(self, args):
    name = args["name"]
    newvalue = args["newvalue"]
    if name == "mudecho":
      self.cfg_echo_ = newvalue
    elif name == "curses.lazy":
      self.cfg_lazy_ = newvalue
    elif name == "curses.maxscrollback":
      self.cfg_maxscrollback_ = min(1000, newvalue)
    elif name == "curses.attr.user":
      self.attr_user_ = color_lookup[newvalue]
    elif name == "curses.attr.session":
      self.attr_session_ = color_lookup[newvalue]
    elif name == "curses.attr.error":
      self.attr_error_ = color_lookup[newvalue]
    elif name == "curses.attr.lyntin":
      self.attr_lyntin_ = color_lookup[newvalue]
    elif name == "curses.compact":
      self.cfg_compact_ = newvalue
    elif name == "curses.keydebug":
      self.cfg_keydebug_ = newvalue


  def _append(self, line):
    #
    # Appends the line to screen redraw buffer
    #
    lines = self.lines_
    lines.append(line)
    llen = len(lines) - self.cfg_maxscrollback_
    if llen > 0:
      lines[0:llen] = []
      self.prompt_index_ -= llen
    os.write(self.output_[1], '0') 
      
    
  def _decode_colors(self, ses, default_attr, line, pretext=[]):
    if self.unfinished_.has_key(ses):
      (currentcolor, leftover) = self.unfinished_[ses]
    else:
      currentcolor = list(ansi.DEFAULT_COLOR)
      leftover = ''
      
    for single in line.splitlines(1):
      current = []
      tokens = ansi.split_ansi_from_text(leftover + single)
      leftover = ''
      lasttok = ''
      for tok in tokens:
        if ansi.is_color_token(tok):
          currentcolor, leftover = ansi.figure_color([tok], currentcolor, leftover)
        elif tok:
          attr = default_attr
          if currentcolor[ansi.PLACE_BOLD]:
            attr |= curses.A_BOLD
          if currentcolor[ansi.PLACE_UNDERLINE]:
            attr |= curses.A_UNDERLINE
          if currentcolor[ansi.PLACE_BLINK]:
            attr |= curses.A_BLINK
          if currentcolor[ansi.PLACE_REVERSE]:
            attr |= curses.A_REVERSE
          foreground = currentcolor[ansi.PLACE_FG] - 30  
          if 0 <= foreground and foreground <= 7:
            attr += curses_fore(foreground)
          background = currentcolor[ansi.PLACE_BG] - 40
          if  0 <= background and background <= 7:
            attr += curses_back(background)
          lasttok = tok  
          current.append( (tok, attr) )
      if current:
        lines = self.lines_
        current[:0] = pretext
        if not lasttok.endswith("\n"): # it is a prompt
          #
          # Append newline to prompts coming from another sessions
          if ses != exported.get_current_session():
            current.append( ("\n", curses.A_NORMAL) )
          else:
            if self.cfg_compact_ and self.prompt_ == current:
              #
              # Remove the identical prompt from previous output buffer:
              #
              lines[self.prompt_index_:self.prompt_index_+1] = []
            else:
              self.prompt_ = current
            self.prompt_index_ = len(lines)
          self._append(current)

        # eliminating empty lines:
        elif current[0][0] != "\n" or not self.cfg_compact_:
          self._append(current)

    self.unfinished_[ses] = (currentcolor, leftover)

  def write(self, args):
    """
    Handles writing information from the mud and/or Lyntin
    to the user.
    """
    msg = args["message"]
  
    if type(msg) == types.StringType:
      msg = message.Message(msg, message.LTDATA)
    elif msg.type == message.USERDATA:
      return

    line = msg.data
    ses = msg.session

    if line == '' or self.showTextForSession(ses) == 0:
      return

    line = line.replace("\t", "    ")

    pretext = []
    if ses != None and ses != exported.get_current_session():
      attr = self.attr_session_
      pretext = [ ("[", attr),
                  (ses.getName(), attr | curses.A_BOLD),
                  ("] ", attr ) ]

    default_attr = curses.A_NORMAL
    if msg.type == message.ERROR:
      pretext[:0] = [ ("! ", self.attr_error_) ]
    elif msg.type == message.LTDATA:
      pretext[:0] = [ ("@ ", self.attr_lyntin_) ]

    self._decode_colors(ses, default_attr, line, pretext)


  def handleinput(self, line, internal=0):
    self._append( [ (line+"\n", self.attr_user_) ] )
    if internal:
      exported.lyntin_command(line, internal=1)
    else:  
      base.BaseUI.handleinput(self, line)


  def runui(self):
    # 
    # This is the loop for user input polling and for mud output.
    #
    global HELP_TEXT
    
    exported.add_help("cursesui", HELP_TEXT)

    stdscr = curses.initscr()
    try:
    
      if curses.has_colors():
        curses.start_color()
        for i in xrange(1,64):
          curses.init_pair(i, i%8, i/8)
      curses.raw()
      curses.noecho()
      curses.nonl()
      curses.meta(1)

      out = None
      edit = None
      scrollback = None

      lines = self.lines_

      exported.write_message("For Cursesui help, type \"#help cursesui\".")
      exported.write_message("For some commands help, type \"#help curses\".")

      dirty_count = 0
      timestamp = 0
      output_count = 0

      hotkey_buffer = ''
      keyboard_buffer = []

      select_timeout = 100
      keyboard_fd = sys.stdin.fileno()
      output_pipe_fd = self.output_[0]
      select_input_list = [ keyboard_fd, output_pipe_fd ]

      while self.running_:

        #
        # set output windows:
        #
        if not out:
          stdscr = curses.initscr()
          (screen_h, screen_w) = stdscr.getmaxyx()
          win = curses.newwin(1, screen_w, screen_h-1, 0)
          if edit:
            edit.attach(win)
          else:  
            edit = inputbox(self, win)
          if not scrollback:
            out = scroller(curses.newwin(screen_h-1, screen_w, 0, 0), lines)
          else:
            scroll_h = screen_h/3*2
            out_h = (screen_h - 2) - scroll_h 
            scrollback = scroller(curses.newwin(scroll_h, screen_w, 0, 0),
                                  lines[:])
            scrollback.redraw()
            wborder = curses.newwin(1, screen_w, scroll_h, 0)
            wborder.bkgd(curses.ACS_HLINE)
            wborder.erase()
            wborder.noutrefresh()
            out = scroller(curses.newwin(out_h, screen_w, scroll_h+1, 0), lines)
          out.redraw()

        edit._align()

        if keyboard_buffer and not hotkey_buffer:
          ch = keyboard_buffer.pop()
        else: 
          ch = win.getch()
          if ch == curses.ERR:
          
            # drop the hotkey buffer when the keyboard goes idle
            hotkey_buffer = ''

            # enter idle mode:
            try:
                (i, o, x) = select.select(select_input_list, [], [], select_timeout)
            except:
                # It's probably stray EINTR - further investigation is needed
                (i, o, x) = (None, None, None)

            if not i:
              # timeout was hit:
              out.redraw(self.cfg_maxscrollback_)
              select_timeout = 100
              dirty_count = 0
              continue
            else:    
              
              if keyboard_fd in i:
                ch = win.getch()
 
              if output_pipe_fd in i:  
                line=os.read(output_pipe_fd, 1024)
                dirty_count += len(line)
                
              if ch == curses.ERR:
                timestamp_now = time()
                if ((timestamp_now - timestamp) > 0.2) or (dirty_count > self.cfg_lazy_):
                  out.redraw(self.cfg_maxscrollback_)
                  select_timeout = 100
                  dirty_count = 0
                  output_count = 0
                else:  
                  select_timeout = 0.2
                  output_count += 1
                timestamp = timestamp_now
                continue

          keyboard_buffer.insert(0, ch)
          if ch < 256:
            keycodename = chr(ch)
            hotkey_buffer += keycodename
            
            if self.cfg_keydebug_:
              if is_a_char(keycodename):
                exported.write_message(keycodename)
              elif ch==0x1b:
                exported.write_message("<ESC>")

            binding = bindings.get(hotkey_buffer)
            if binding:
              hotkey_buffer = ''
              keyboard_buffer = []
              self.handleinput(binding[1], internal=1)
              continue
            elif not filter(lambda x: x.startswith(hotkey_buffer), bindings.keys()):
              hotkey_buffer = ''
            continue
          else:
            keycodename = keytext.get(ch)
            if keycodename:
              if self.cfg_keydebug_:
                exported.write_message(keycodename)
              binding = bindings.get(keycodename)
              if binding:
                self.handleinput(binding[1], internal=1)
                keyboard_buffer.pop() # get it back
            hotkey_buffer = ''
            continue

        if ch == curses.KEY_PPAGE:
          if not scrollback:
            scrollback = 1 # create scrollback window at next iteration
            out = None
          else: 
            scrollback.redraw( scroll = -(scroll_h/2+1) )
          continue
        if ch == curses.KEY_NPAGE:
          if scrollback:
            scrollback.redraw( scroll = scroll_h/2+1 )
          continue

        if ch == curses.ascii.ESC and scrollback:
          scrollback = None
          out = None
          continue

        ch = edit.do_command(ch)    

        if ch in (curses.ascii.CR, curses.ascii.LF):
          edit_string = edit.get_string()
          if edit_string.strip() == "#end":
            break
          self.handleinput( edit_string )
          edit.set("")

        elif ch in (curses.KEY_RESIZE, curses.ascii.FF): # force screen redraw
          out = None
          continue

        elif ch == curses.ascii.ETX:    # Ctrl-C
          break

    finally:
      endcurses()



# vim:ts=2:sw=2:et:ft=python
