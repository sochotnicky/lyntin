#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2001-2007
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: textui.py,v 1.10 2007/07/24 00:39:03 willhelm Exp $
#######################################################################
"""
Holds the text ui class.
"""
import re, sys, os, select, types
from lyntin import ansi, engine, event, utils, exported, config
from lyntin.ui import base, message


HELP_TEXT = """
The textui is the most basic ui you can get.  It works great over
telnet/ssh, but terrible in the Win32 command window.  At the same 
time, because it's so basic, it tends to be a good testing ui.

To enable GNU readline support (if it's available) use:

   --readline on

at the command line.  It'll look for a "readlinerc" file in your
datadir and set readline options from that.

Also, depending on what terminal you're running Lyntin from, it might 
help to set the TERMTYPE at the commandline.  Lyntin returns "lyntin" 
when asked, but doing something like:

   --term xterm

will kick Lyntin into returning "xterm" as the TERMTYPE.
"""

try:
  import termios
except ImportError:
  pass

myui = None

DEFAULT_COLOR = list(ansi.DEFAULT_COLOR)
DEFAULT_ANSI = chr(27) + "[0m"

def get_ui_instance():
  global myui
  if myui == None:
    myui = Textui()
  return myui

class Textui(base.BaseUI):
  """
  This is the text ui.  It's super basic and should run almost
  anywhere.  It lacks several useful functions that the Tkui
  and the Curses ui (eventually) will have.
  """
  def __init__(self):
    """ Initialize the textui."""
    base.BaseUI.__init__(self)
    exported.hook_register("shutdown_hook", self.shutdown)
    exported.hook_register("to_user_hook", self.write)
    exported.hook_register("config_change_hook", self.configChangeHandler)
    exported.hook_register("bell_hook", self.bell)
    self._currcolors = {}
    self._unfinishedcolor = {}

    self._tio = 0
    self._rline = 0
    self._echo = 1

    # grab the stdin stream at once,
    # enabling it's further redirection by another module
    self._stdin = sys.stdin

  def runui(self):
    global HELP_TEXT
    exported.add_help("textui", HELP_TEXT)
    exported.write_message("For textui help, type \"#help textui\".")

    # termios is the module that allows us to change echo for a terminal
    # but only if the module is present
    try:
      import termios
    except ImportError:
      self._tio = 0
    else:
      self._tio = 1
      echonew = termios.tcgetattr(self._stdin.fileno())
      self._onecho_attr = echonew[3]
      self._offecho_attr = echonew[3] & ~termios.ECHO

    if config.options.has_key("readline"):
      try:
        import readline
      except ImportError:
        self._rline = 0
        exported.write_error("Readline not available for your system.")
      else:
        self._rline = 1

        # we do some stuff to grab the readlinerc file if they have one
        # so the user can set some readline oriented things which makes 
        # things a little nicer for the user.
        d = exported.get_config("datadir")

        try:
          readline.read_init_file(d + "readlinerc")
        except:
          exported.write_error("Note: No readlinerc file available in %s." % d)
        
        exported.write_message("Readline enabled.")

    if self._tio == 0 or self._rline == 1:
      exported.write_error("Warming: echo off is unavailable.  " +
                           "Your password will be visible.")

    # go into the main loop
    self.run()
      
  def shutdown(self, args):
    """ Shuts down the textui and makes sure that we're echoing!"""
    if self._echo == 0:
      self.turnonecho()

  def turnonecho(self):
    """ Turns on echo if termios module is present."""
    if self._tio == 0 or self._rline == 1:
      return
    fd = self._stdin.fileno()
    new = termios.tcgetattr(fd)
    new[3] = self._onecho_attr
    try:
      termios.tcsetattr(fd, termios.TCSADRAIN, new)
      self._echo = 1
    except Exception, e:
      exported.write_error("textui: unable to turn on echo: %s" % e)

  def turnoffecho(self):
    """ Turns off echo if termios module is present."""
    if self._tio == 0 or self._rline == 1:
      return

    fd = self._stdin.fileno()
    new = termios.tcgetattr(fd)
    new[3] = self._offecho_attr
    try:
      termios.tcsetattr(fd, termios.TCSADRAIN, new)
      self._echo = 0
    except Exception, e:
      exported.write_error("textui: unable to turn off echo: %s" % e)


  def bell(self, args):
    """ Handles incoming bell characters."""
    sys.stdout.write('\07')

  def configChangeHandler(self, args):
    """ Handles config changes (including mudecho)."""
    name = args["name"]
    newvalue = args["newvalue"]

    if name == "mudecho":
      if newvalue == 0:
        # echo off
        self.turnoffecho()
      else:
        # echo on
        self.turnonecho()

  def _posix_readline_input(self):
    """
    If the os is posix and the readline module is present, then we 
    use raw_input to grab user input.
    """
    try:
      return raw_input()
    except EOFError:
      pass

  def _posix_input(self):
    """
    If the os is posix and there is no readline module, then we
    use sys.stdin.readline().
    """
    readers,w,e = select.select([self._stdin], [], [])
    if readers:
      for mem in readers:
        try:
          return mem.readline()
        except IOError:
          pass

  def _non_posix_input(self):
    return self._stdin.readline()

  def run(self):
    """ This is the poll loop for user input."""
    try:
      while not self.shutdownflag:
        if os.name == 'posix':
          if self._rline == 1:
            data = self._posix_readline_input()
          else:
            data = self._posix_input()
        else:
          data = self._non_posix_input()

        if data != None:
          self.handleinput(data)

          # FIXME - this is just plain icky.  the issue is that
          # we need to know we're ending _before_ we block for
          # the next input.  otherwise Lyntin will shut down except
          # for this thread which will hang around blocking until
          # the user hits the enter key.
          # 
          # any good ideas for dealing with this are more than welcome.
          if data.find("#end") == 0:
            break


    except select.error, e:
      (errno,name) = e
      if errno == 4:
        exported.write_message("system exit: select.error.")
        event.ShutdownEvent().enqueue()
        return

    except SystemExit:
      exported.write_message("system exit: you'll be back...")
      event.ShutdownEvent().enqueue()

    except:
      exported.write_traceback()
      event.ShutdownEvent().enqueue()


  def write(self, args):
    """
    Handles writing information from the mud and/or Lyntin
    to the user.
    """
    msg = args["message"]

    if type(msg) == types.StringType:
      msg = message.Message(msg, message.LTDATA)

    line = msg.data
    ses = msg.session

    if line == '' or self.showTextForSession(ses) == 0:
      return

    # we prepend the session name to the text if this is not the 
    # current session sending text.
    pretext = ""
    if ses != None and ses != exported.get_current_session():
      pretext = "[" + ses.getName() + "] "

    if msg.type == message.ERROR or msg.type == message.LTDATA:
      if msg.type == message.ERROR:
        pretext = "error: " + pretext
      else:
        pretext = "lyntin: " + pretext

      line = pretext + utils.chomp(line).replace("\n", "\n" + pretext)
      if exported.get_config("ansicolor") == 1:
        line = DEFAULT_ANSI + line
      sys.stdout.write(line + "\n")
      return

    elif msg.type == message.USERDATA:
      # we don't print user data in the textui
      return

    if exported.get_config("ansicolor") == 0:
      if pretext:
        if line.endswith("\n"):
          line = (pretext + line[:-1].replace("\n", "\n" + pretext) + "\n")
        else:
          line = pretext + line.replace("\n", "\n" + pretext)
      sys.stdout.write(line)
      sys.stdout.flush()
      return

    # each session has a saved current color for mud data.  we grab
    # that current color--or user our default if we don't have one
    # for the session yet.
    if self._currcolors.has_key(ses):
      color = self._currcolors[ses]
    else:
      # need a copy of the list and not a reference to the list itself.
      color = list(DEFAULT_COLOR)


    # some sessions have an unfinished color as well--in case we
    # got a part of an ansi color code in a mud message, and the other
    # part is in another message.
    if self._unfinishedcolor.has_key(ses):
      leftover = self._unfinishedcolor[ses]
    else:
      leftover = ""

    lines = line.splitlines(1)
    if lines:
      for i in range(0, len(lines)):
        mem = lines[i]
        acolor = ansi.convert_tuple_to_ansi(color)

        color, leftover = ansi.figure_color(mem, color, leftover)

        if pretext:
          lines[i] = DEFAULT_ANSI + pretext + acolor + mem
        else:
          lines[i] = DEFAULT_ANSI + acolor + mem

      sys.stdout.write("".join(lines) + DEFAULT_ANSI)
      sys.stdout.flush()

    self._currcolors[ses] = color
    self._unfinishedcolor[ses] = leftover


  def prompt(self):
    """ Prints a prompt to the user."""
    sys.stdout.write("> ")
    sys.stdout.flush()

  def flush(self):
    """ Flushes the stdout.  Not sure we really need this
    but it's here."""
    sys.stdout.flush()

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
