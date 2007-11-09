#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 1999-2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: tkui.py,v 1.29 2007/11/09 20:09:42 willhelm Exp $
#######################################################################
"""
This is a tk oriented user interface for lyntin.  Based on
Lyntin, but largely re-coded in various areas.
"""

from Tkinter import *
from ScrolledText import ScrolledText
import os, tkFont, types, Queue
import locale
import sys
from lyntin import ansi, event, engine, exported, utils, constants, config
from lyntin.ui import base, message


if locale.__dict__.has_key('getpreferredencoding'):
  UNICODE_ENCODING = locale.getpreferredencoding() # python2.3 and later
else:  
  UNICODE_ENCODING = locale.getlocale()[1]

try:
  ''.decode(UNICODE_ENCODING).encode(UNICODE_ENCODING)
except:
  try:
    UNICODE_ENCODING = 'CP' + UNICODE_ENCODING # Kludge for 2.2
    ''.decode(UNICODE_ENCODING).encode(UNICODE_ENCODING)
  except:  
    UNICODE_ENCODING = 'latin-1'


def _decode(text):
    """
    Decodes the text to the unicode representation.
    Tries its best to replace illegal characters.

    @param text: text to convert to unicode
    @type  text: string

    @returns: unicode text
    @rtype: unicode string
    """
    while True:
        try:
            return text.decode(UNICODE_ENCODING)
        except:
            ex_class, ex_info, tb = sys.exc_info()
            if str(ex_class) == 'exceptions.UnicodeDecodeError': # python2.3
                text = text.replace(text[ex_info.start:ex_info.end], '?')
            else: # python2.2
                letters = []
                for char in text:
                    try:
                        letters.append(char.decode(UNICODE_ENCODING))
                    except:
                        letters.append('?'.decode(UNICODE_ENCODING))
                return ''.join(letters)
  

HELP_TEXT = """The tkui uses the Tk widget set and provides a graphical interface 
to Lyntin.  It also has the following additional functionality:

 - numpad bindings (VK_NUMPAD0 through VK_NUMPAD9)
 - function key bindings (VK_F2 through VK_F12)
 - pgup and pgdown scroll back (escape to get rid of the split 
   screen)
 - up and down command line history
 - ctrl-u removal of text
 - ctrl-c copy from the text buffer and ctrl-v paste into the command
   buffer (in Windows)
 - ctrl-t autotyper
 - NamedWindow handling

To bind function key and numpad bindings, create an alias for the
symbol.  For example:

   #alias {VK_NUMPAD2} {south}
"""

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

# this is the default color--it's what we use when the mud hasn't
# specified a color yet.  this might get a little fishy.
# when using DEFAULT make sure you clone it first.
DEFAULT_COLOR = list(ansi.DEFAULT_COLOR)
DEFAULT_COLOR[ansi.PLACE_FG] = 37

myui = None

def get_ui_instance():
  global myui
  if myui == None:
    myui = Tkui()
  return myui

class _Event:
  def __init__(self):
    pass

  def execute(self, tkui):
    pass

class _OutputEvent(_Event):
  def __init__(self, text):
    self._text = text

  def execute(self, tkui):
    tkui.write_internal(self._text)

class _ColorCheckEvent(_Event):
  def execute(self, tkui):
    tkui.colorCheck() 

class _TitleEvent(_Event):
  def __init__(self, tk, title):
    self._tk = tk
    self._title = title

  def execute(self, tkui):
    tkui._tk.title(self._title)

class _WriteWindowEvent(_Event):
  def __init__(self, windowname, message):
    self._windowname = windowname
    self._message = message

  def execute(self, tkui):
    tkui.writeWindow_internal(self._windowname, self._message)

class Tkui(base.BaseUI):
  """
  This is a ui class which handles the complete Tk user interface.
  """
  def __init__(self):
    """ Initializes."""
    base.BaseUI.__init__(self)

    # internal ui queue
    self._event_queue = Queue.Queue()

    # map of session -> (bold, foreground, background)
    self._currcolors = {}

    # ses -> string
    self._unfinishedcolor = {}

    self._viewhistory = 0
    self._do_i_echo = 1

    # holds a map of window names -> window references
    self._windows = {}

    # instantiate all the widgets
    self._tk = Tk()
    self._tk.geometry("800x600")

    self.settitle()

    fnt = tkFont.Font(family="FixedSys", size=10)

    self._entry = CommandEntry(self._tk, self, fg='white', bg='black',
                               insertbackground='yellow', font=fnt, 
                               insertwidth='2')
    self._entry.pack(side='bottom', fill='both')

    self._topframe = Frame(self._tk)
    self._topframe.pack(side='top', fill='both', expand=1)

    self._txt = ScrolledText(self._topframe, fg='white', 
                             bg='black', font=fnt, height=20)
    self._txt.pack(side='bottom', fill='both', expand=1)


    self._txt.bind("<KeyPress>", self._ignoreThis)
    self._txtbuffer = ScrolledText(self._topframe, fg='white', 
                                   bg='black', font=fnt, height=20)
    self._txtbuffer.bind("<KeyPress-Escape>", self.escape)
    self._txtbuffer.bind("<KeyPress>", self._ignoreThis)


    self._entry.focus_set()
    self._initColorTags()
    self.dequeue()

    exported.hook_register("config_change_hook", self.configChangeHandler)
    exported.hook_register("to_user_hook", self.write)

    # FIXME - fix this explanation.  this is just terrible.
    tc = config.BoolConfig("saveinputhighlight", 0, 1,
         "Allows you to change the behavior of the command entry.  When "
         "saveinputhighlight is off, we discard whatever is on the entry "
         "line.  When it is on, we will retain the contents allowing you "
         "to press the enter key to do whatever you typed again.")
    exported.add_config("saveinputhighlight", tc)

    self._quit = 0

  def runui(self):
    global HELP_TEXT
    exported.add_help("tkui", HELP_TEXT)
    exported.write_message("For tk help type \"#help tkui\".")
    exported.add_command("colorcheck", colorcheck_cmd)

    # run the tk mainloop here
    self._tk.mainloop()

  def wantMainThread(self):
    # The tkui needs the main thread of execution so we return
    # a 1 here.
    return 1

  def quit(self):
    if not self._quit:
      self._quit = 1
      self._topframe.quit()

  def dequeue(self):
    qsize = self._event_queue.qsize()
    if qsize > 10:
      qsize = 10

    for i in range(qsize):
      ev = self._event_queue.get_nowait()
      ev.execute(self)

    self._tk.after(25, self.dequeue)

  def settitle(self, title=""):
    """
    Sets the title bar to the Lyntin title plus the given string.

    @param title: the title to set
    @type  title: string
    """
    if title:
      title = constants.LYNTINTITLE + title
    else:
      title = constants.LYNTINTITLE
    self._event_queue.put(_TitleEvent(self._tk, title))

  def removeWindow(self, windowname):
    """
    This removes a NamedWindow from our list of NamedWindows.

    @param windowname: the name of the window to write to
    @type  windowname: string
    """
    if self._windows.has_key(windowname):
      del self._windows[windowname]

  def writeWindow(self, windowname, message):
    """
    This writes to the window named "windowname".  If the window
    does not exist, we spin one off.  It handles ansi text and
    messages just like writing to the main window.

    @param windowname: the name of the window to write to
    @type  windowname: string

    @param message: the message to write to the window
    @type  message: string or Message instance
    """
    self._event_queue.put(_WriteWindowEvent(windowname, message))

  def writeWindow_internal(self, windowname, message):
    if not self._windows.has_key(windowname):
      self._windows[windowname] = NamedWindow(windowname, self, self._tk)
    self._windows[windowname].write(message)
     
  def _ignoreThis(self, tkevent):
    """ This catches keypresses from the history buffer."""
    # kludge so that ctrl-c doesn't get caught allowing windows
    # users to copy the buffer....
    if tkevent.keycode == 17 or tkevent.keycode == 67:
      return

    self._entry.focus()
    if tkevent.char:
      # we do this little song and dance so as to pass events
      # we don't want to deal with to the entry widget essentially
      # by creating a new event and tossing it in the event list.
      # it only sort of works--but it's the best code we've got
      # so far.
      args = ('event', 'generate', self._entry, "<KeyPress>")
      args = args + ('-rootx', tkevent.x_root)
      args = args + ('-rooty', tkevent.y_root)
      args = args + ('-keycode', tkevent.keycode)
      args = args + ('-keysym', tkevent.keysym)

      self._tk.tk.call(args)

    return "break"

  def pageUp(self):
    """ Handles prior (Page-Up) events."""
    if self._viewhistory == 0:
      self._txtbuffer.pack(side='top', fill='both', expand=1)

      self._viewhistory = 1
      self._txtbuffer.delete ("1.0", "end")
      lotofstuff = self._txt.get ('1.0', 'end')
      self._txtbuffer.insert ('end', lotofstuff)
      for t in self._txt.tag_names():
        taux=None
        tst=0
        for e in self._txt.tag_ranges(t):
          if tst==0:
            taux=e
            tst=1
          else:
            tst=0
            self._txtbuffer.tag_add(t,str(taux),str(e))

      self._txtbuffer.yview('moveto', '1')
      if os.name != 'posix':
        self._txtbuffer.yview('scroll', '20', 'units')
      self._tk.update_idletasks()
      self._txt.yview('moveto','1.0')
      if os.name != 'posix':
        self._txt.yview('scroll', '220', 'units')

    else:
      # yscroll up stuff
      self._txtbuffer.yview('scroll', '-15', 'units')

  def pageDown(self):
    """ Handles next (Page-Down) events."""
    if self._viewhistory == 1:
      # yscroll down stuff
      self._txtbuffer.yview('scroll', '15', 'units')

  def escape(self, tkevent):
    """ Handles escape (Escape) events."""
    if self._viewhistory == 1:
      self._txtbuffer.forget()
      self._viewhistory = 0
    else:
      self._entry.clearInput()

  def configChangeHandler(self, args):
    """ This handles config changes including mudecho. """
    name = args["name"]
    newvalue = args["newvalue"]

    if name == "mudecho":
      if newvalue == 1:
        # echo on
        self._do_i_echo = 1
        self._entry.configure(show='')
      else:
        # echo off
        self._do_i_echo = 0
        self._entry.configure(show='*')

  def _yadjust(self):
    """Handles y scrolling after text insertion."""
    self._txt.yview('moveto', '1')
    # if os.name != 'posix':
    self._txt.yview('scroll', '20', 'units')

  def _clipText(self):
    """
    Scrolls the text buffer up so that the new text written at
    the bottom of the text buffer can be seen.
    """
    temp = self._txt.index("end")
    ind = temp.find(".")
    temp = temp[:ind]
    if (temp.isdigit() and int(temp) > 800):
      self._txt.delete ("1.0", "100.end")

  def write(self, args):
    """
    This writes text to the text buffer for viewing by the user.

    This is overridden from the 'base.BaseUI'.
    """
    self._event_queue.put(_OutputEvent(args))

  def write_internal(self, args):
    mess = args["message"]
    if type(mess) == types.StringType:
      mess = message.Message(mess, message.LTDATA)
    elif "window" in mess.hints:
      self.writeWindow_internal(mess.hints["window"], mess)
      return

    line = mess.data
    ses = mess.session

    if line == '' or self.showTextForSession(ses) == 0:
      return

     
    color, leftover = buffer_write(mess, self._txt, self._currcolors, 
                                   self._unfinishedcolor)

    if mess.type == message.MUDDATA:
      self._unfinishedcolor[ses] = leftover
      self._currcolors[ses] = color

    self._clipText()
    self._yadjust()


  def convertColor(self, name):
    """
    Tk has this really weird color palatte.  So I switched to using
    color names in most cases and rgb values in cases where I couldn't
    find a good color name.

    This method allows me to specify either an rgb or a color name
    and it converts the color names to rgb.

    @param name: either an rgb value or a name
    @type  name: string

    @returns: the rgb color value
    @rtype: string
    """
    if name.startswith("#"):
      return name

    rgb = self._tk._getints(self._tk.tk.call('winfo', 'rgb', self._txt, name))
    rgb = "#%02x%02x%02x" % (rgb[0]/256, rgb[1]/256, rgb[2]/256) 
    print name, "converted to: ", rgb

    return rgb

  def _initColorTags(self):
    """ Sets up Tk tags for the text widget (fg/bg/u)."""
    for ck in fg_color_codes.keys():
      color = self.convertColor(fg_color_codes[ck])
      self._txt.tag_config(ck, foreground=color)
      self._txtbuffer.tag_config(ck, foreground=color)

    for ck in bg_color_codes.keys():
      self._txt.tag_config(ck, background=bg_color_codes[ck])
      self._txtbuffer.tag_config(ck, background=bg_color_codes[ck])

    self._txt.tag_config("u", underline=1)
    self._txtbuffer.tag_config("u", underline=1)

  def colorCheck(self):
    """
    Goes through and displays all the combinations of fg and bg
    with the text string involved.  Purely for debugging
    purposes.
    """
    fgkeys = ['30','31','32','33','34','35','36','37']
    bgkeys = ['40','41','42','43','44','45','46','47']

    self._txt.insert('end', 'color check:\n')
    for bg in bgkeys:
      for fg in fgkeys:
        self._txt.insert('end', str(fg), (fg, bg))
        self._txt.insert('end', str("b" + fg), ("b" + fg, bg))
      self._txt.insert('end', '\n')

      for fg in fgkeys:
        self._txt.insert('end', str(fg), (fg, "b" + bg))
        self._txt.insert('end', str("b" + fg), ("b" + fg, "b" + bg))
      self._txt.insert('end', '\n')

    self._txt.insert('end', '\n')
    self._txt.insert('end', '\n')


class CommandEntry(Entry):
  """ This class handles the user input area."""

  def __init__(self, master, partk, **kw):
    """ Initializes and sets the key-bindings."""
    self._partk = partk
    self._inputstack = []
    self._autotyper = None
    self._autotyper_ses = None

    Entry.__init__(self, master, kw)

    self.bind("<KeyPress-Return>", self.createInputEvent)

    self.bind("<KeyPress-Up>", self.insertPrevCommand)
    self.bind("<KeyPress-Down>", self.insertNextCommand)
    self.bind("<KeyPress-Tab>", self.do_completion)
    self.bind("<KeyPress-Prior>", self.callPrior)
    self.bind("<KeyPress-Next>", self.callNext)

    self.bind("<Control-KeyPress-t>", self.startAutotyper)
    self.bind("<Control-KeyPress-u>", self.callKillLine)
    self.bind("<Control-KeyPress-Up>", self.callPushInputStack)
    self.bind("<Control-KeyPress-Down>", self.callPopInputStack)
    self.bind("<KeyPress-Escape>", self.callEsc)

    self.bind("<KeyPress-F1>", self.callBinding) # reserved for help

    self.bind("<KeyPress-F2>", self.callBinding)
    self.bind("<KeyPress-F3>", self.callBinding)
    self.bind("<KeyPress-F4>", self.callBinding)
    self.bind("<KeyPress-F5>", self.callBinding)
    self.bind("<KeyPress-F6>", self.callBinding)
    self.bind("<KeyPress-F7>", self.callBinding)
    self.bind("<KeyPress-F8>", self.callBinding)
    self.bind("<KeyPress-F9>", self.callBinding)
    self.bind("<KeyPress-F10>", self.callBinding)
    self.bind("<KeyPress-F11>", self.callBinding)
    self.bind("<KeyPress-F12>", self.callBinding)

    # this next line totally hoses win32
    # self.bind("<Destroy>", self.deathHandler)

    if os.name!="posix":
      self.bind("<KeyPress-8>", self.callKP8)
      self.bind("<KeyPress-6>", self.callKP6)
      self.bind("<KeyPress-4>", self.callKP4)
      self.bind("<KeyPress-2>", self.callKP2)
      self.bind("<KeyPress-9>", self.callKP9)
      self.bind("<KeyPress-7>", self.callKP7)
      self.bind("<KeyPress-5>", self.callKP5)
      self.bind("<KeyPress-3>", self.callKP3)
      self.bind("<KeyPress-1>", self.callKP1)

    else:
      self.bind("<KeyPress-KP_Up>", self.callKP8)
      self.bind("<KeyPress-KP_Right>", self.callKP6)
      self.bind("<KeyPress-KP_Left>", self.callKP4)
      self.bind("<KeyPress-KP_Down>", self.callKP2)
      self.bind("<KeyPress-KP_Prior>", self.callKP9)
      self.bind("<KeyPress-KP_Home>", self.callKP7)
      self.bind("<KeyPress-KP_Begin>", self.callKP5)
      self.bind("<KeyPress-KP_Next>", self.callKP3)
      self.bind("<KeyPress-KP_End>", self.callKP1)
      self.bind("<KeyPress-KP_Enter>", self.createInputEvent)

    self.bind("<KeyPress>", self.reset_completion)

    self.hist_index = -1
    self._partk = partk

  def reset_completion(self, tkevent):
    """ If the key is not Tab, then reset current completion """
    if not tkevent.keysym == "Tab":
      self._partk.reset_completion()

  def createInputEvent(self, tkevent):
    """ Handles the <KeyPress-Return> event."""
    val = fix_unicode(self.get())
    self._partk.handleinput(val)

    # self._inputstack.insert(0, val)
    # if len(self._inputstack) > 30:
    #   self._inputstack = self._inputstack[:-1]

    if exported.get_config("saveinputhighlight") == 1:
      self.selection_range(0, 'end')
    else:
      self.delete(0, 'end')
    self.hist_index = -1

    if val == exported.get_config("commandchar") + "end":
      self._partk._topframe.quit()

  def deathHandler(self, tkevent):
    """
    This catches the event where the window is being closed.
    We can't stop it from closing, but we can try to shut down the app.
    """
    self._partk.handleinput(exported.get_config("commandchar") + "end")

  def _executeBinding(self, binding):
    """ Returns the alias for this keybinding."""
    ses = exported.get_current_session()
    action = exported.get_manager("alias").getAlias(ses, binding)
    if action:
      self._partk.handleinput(action)
      return 1
    else:
      # we're commenting this out since it seems to be more annoying
      # than useful.  it's not a good substitute for good documentation
      # for the tkui.
      # exported.write_error("%s is currently not bound to anything." % binding)
      return 0

  def callBinding(self, tkevent):
    """ Handles arbitrary bindings of function call keypresses."""

    # handle all the function keys except F1
    if tkevent.keysym == "F1":
      self._partk.handleinput(exported.get_config("commandchar") + "help")
      return "break"

    if self._executeBinding("VK_%s" % tkevent.keysym) == 1:
      return "break"

    # these two lines help in debugging stuff we bound
    # but don't know how to handle because I can't seem to
    # find a solid listing of Tk keysyms (grrrrrrr).
    # print repr(tkevent)
    # print repr(tkevent.__dict__)

  def callKP9(self, tkevent):
    if tkevent.keycode == 105 or os.name=='posix':
      if self._executeBinding("VK_NUMPAD9") == 1:
        return "break"

  def callKP8(self, tkevent):
    if tkevent.keycode == 104 or os.name=='posix':
      if self._executeBinding("VK_NUMPAD8") == 1:
        return "break"

  def callKP7(self, tkevent):
    if tkevent.keycode == 103 or os.name=='posix':
      if self._executeBinding("VK_NUMPAD7") == 1:
        return "break"

  def callKP6(self, tkevent):
    if tkevent.keycode == 102 or os.name=='posix':
      if self._executeBinding("VK_NUMPAD6") == 1:
        return "break"

  def callKP5(self, tkevent):
    if tkevent.keycode == 101 or os.name=='posix':
      if self._executeBinding("VK_NUMPAD5") == 1:
        return "break"

  def callKP4(self, tkevent):
    if tkevent.keycode == 100 or os.name=='posix':
      if self._executeBinding("VK_NUMPAD4") == 1:
        return "break"

  def callKP3(self, tkevent):
    if tkevent.keycode == 99 or os.name=='posix':
      if self._executeBinding("VK_NUMPAD3") == 1:
        return "break"

  def callKP2(self, tkevent):
    if tkevent.keycode == 98 or os.name=='posix':
      if self._executeBinding("VK_NUMPAD2") == 1:
        return "break"

  def callKP1(self, tkevent):
    if tkevent.keycode == 97 or os.name=='posix':
      if self._executeBinding("VK_NUMPAD1") == 1:
        return "break"

  def startAutotyper(self, tkevent):
    """
    This will start the autotyper. It will be called if you type <Ctrl>+<t>.
    There can be only one autotyper at a time. The autotyper cannot be started
    for the common session.
    """
    if self._autotyper != None:
      exported.write_error("cannot start autotyper: already started.")
      return
    
    session = exported.get_current_session()
    
    if session.getName() == "common":
      exported.write_error("autotyper cannot be applied to common session.")
      return
    
    self._autotyper = Autotyper(self._partk._tk, self.autotyperDone)
    self._autotyper_ses = session
    
    exported.write_message("autotyper: started.")

  def autotyperDone(self, data):
    """
    This is a callback for the autotyper. It will be called when the autotyper
    is finished.
    
    @param data: the autotyper data--None if the user clicked on "Cancel"
        or closed the autotyper window
    @type  data: string or None
    """
    if data != None:
      self._autotyper_ses.writeSocket(data)
    
    self._autotyper = None
    self._autotyper_ses = None
    
    exported.write_message("autotyper: done.")

  def clearInput(self):
    """ Clears the text widget."""
    self.delete(0, 'end')
        
  def do_completion(self, tkevent):
    """ Handles the <KeyPress-Tab> event, trying to make a completion."""
    (text, position) = self._partk.get_completion(self.get(),
                                                  self.index('insert'))
    self.delete(0, 'end')
    self.insert(0, text)
    self.icursor(position)
    return "break"
        
  def callPrior(self, tkevent):
    """ Handles the <KeyPress-Prior> event."""
    self._partk.pageUp()
        
  def callNext(self, tkevent):
    """ Handles the <KeyPress-Next> event."""
    self._partk.pageDown()
        
  def callEsc(self, tkevent):
    """ Handles the <KeyPress-Escape> event."""
    self._partk.escape(tkevent)
    
  def callKillLine(self, tkevent): 
    """ Handles the <Control-KeyPress-u> event."""
    self.delete(0,'end')

  def callPushInputStack(self, tkevent):
    """ Handles the <Control-KeyPress-Up> event."""
    self._inputstack.append((self.index('insert'),self.get()))
    self.delete(0,'end')

  def callPopInputStack(self,tkevent):
    """ Handles the <Control-KeyPress-Down> event."""
    if len(self._inputstack) < 1:
      return
    poppage = self._inputstack.pop()
    self.delete(0,'end')
    self.insert(0,poppage[1])
    self.icursor(poppage[0])
        
  def insertPrevCommand(self, tkevent):
    """ Handles the <KeyPress-Up> event."""
    hist = exported.get_history()
    if self.hist_index == -1:
      self.current_input = self.get()
    if self.hist_index < len(hist) - 1:
      self.hist_index = self.hist_index + 1
      self.delete(0, 'end')
      self.insert(0, _decode(hist[self.hist_index]))

  def insertNextCommand(self, tkevent):
    """ Handles the <KeyPress-Down> event."""
    hist = exported.get_history()
    if self.hist_index == -1:
      return
    self.hist_index = self.hist_index - 1
    if self.hist_index == -1:
      self.delete(0, 'end')
      self.insert(0, _decode(self.current_input))
            
    else:
      self.delete(0, 'end')
      self.insert(0, _decode(hist[self.hist_index]))

class NamedWindow:
  """
  This creates a window for the Tkui which you can then write to 
  programmatically.  This allows modules to spin off new named windows
  and write to them.
  """
  def __init__(self, windowname, master, partk):
    """
    Initializes the window

    @param windowname: the name of the new window
    @type  windowname: string

    @param master: the main tk window
    @type  master: toplevel
    """
    self._parent = master
    self._tk = Toplevel(partk)
    self._windowname = windowname
    
    # map of session -> (bold, foreground, background)
    self._currcolors = {}

    # ses -> string
    self._unfinishedcolor = {}

    self._do_i_echo = 1

    self._tk.geometry("500x300")
    self._tk.title("Lyntin -- " + self._windowname)
    
    self._tk.protocol("WM_DELETE_WINDOW", self.close)
    
    if os.name == "posix":
      fontname = "Courier"
    else:
      fontname = "Fixedsys"
    fnt = tkFont.Font(family=fontname, size=12)
    
    self._txt = ScrolledText(self._tk, fg="white", bg="black", 
                             font=fnt, height=20)
    self._txt.pack(side=TOP, fill=BOTH, expand=1)
    
    # handles improper keypresses
    self._txt.bind("<KeyPress>", self._ignoreThis)

    # initialize color tags
    self._initColorTags()

  def convertColor(self, name):
    """
    Tk has this really weird color palatte.  So I switched to using
    color names in most cases and rgb values in cases where I couldn't
    find a good color name.

    This method allows me to specify either an rgb or a color name
    and it converts the color names to rgb.

    @param name: either an rgb value or a name
    @type  name: string

    @returns: the rgb color value
    @rtype: string
    """
    if name[0] == "#":
      return name

    rgb = self._tk._getints(self._tk.tk.call('winfo', 'rgb', self._txt, name))
    rgb = "#%02x%02x%02x" % (rgb[0]/256, rgb[1]/256, rgb[2]/256) 
    print name, "converted to: ", rgb

    return rgb

  def _initColorTags(self):
    """ Sets up Tk tags for the text widget (fg/bg)."""
    for ck in fg_color_codes.keys():
      color = self.convertColor(fg_color_codes[ck])
      self._txt.tag_config(ck, foreground=color)

    for ck in bg_color_codes.keys():
      self._txt.tag_config(ck, background=bg_color_codes[ck])

    self._txt.tag_config("u", underline=1)

  def _ignoreThis(self, tkevent):
    """
    This catches keypresses to this window.
    """
    return "break"

  def close(self):
    """
    Closes and destroys references to this window.
    """
    self._parent.removeWindow(self._windowname)
    self._tk.destroy()

  def _yadjust(self):
    """Handles y scrolling after text insertion."""
    self._txt.yview('moveto', '1')
    # if os.name != 'posix':
    self._txt.yview('scroll', '20', 'units')

  def _clipText(self):
    """
    Scrolls the text buffer up so that the new text written at
    the bottom of the text buffer can be seen.
    """
    temp = self._txt.index("end")
    ind = temp.find(".")
    temp = temp[:ind]
    if (temp.isdigit() and int(temp) > 800):
      self._txt.delete ("1.0", "100.end")

  def write(self, msg):
    """
    This writes text to the text buffer for viewing by the user.

    This is overridden from the 'base.BaseUI'.
    """
    if type(msg) == types.TupleType:
      msg = msg[0]

    if type(msg) == types.StringType:
      msg = message.Message(msg, message.LTDATA)

    line = msg.data
    ses = msg.session

    if line == '':
      return

    color, leftover = buffer_write(msg, self._txt, self._currcolors, 
                                   self._unfinishedcolor)

    if msg.type == message.MUDDATA:
      self._unfinishedcolor[ses] = leftover
      self._currcolors[ses] = color

    self._clipText()
    self._yadjust()

 
class Autotyper:
  """
  Autotyper class, it generates the autotyper window, waits for entering text
  and then calls a function to work with the text.
  """
  def __init__(self, master, sendfunc):
    """
    Initializes the autotyper.
    
    @param master: the main tk window
    @type  master: Tk

    @param sendfunc: the callback function
    @type  sendfunc: function
    """
    self._sendfunc = sendfunc
    
    self._frame = Toplevel(master)
    
    # self._frame.geometry("400x300")
    self._frame.title("Lyntin -- Autotyper")
    
    self._frame.protocol("WM_DELETE_WINDOW", self.cancel)
    
    if os.name == "posix":
      fontname = "Courier"
    else:
      fontname = "Fixedsys"
    fnt = tkFont.Font(family=fontname, size=12)
    
    self._txt = ScrolledText(self._frame, fg="white", bg="black", 
                             font=fnt, height=20)
    self._txt.pack(side=TOP, fill=BOTH, expand=1)
    
    self._send_btn = Button(self._frame, text="Send", command=self.send)
    self._send_btn.pack(side=LEFT, fill=X, expand=0)
    
    self._cancel_btn = Button(self._frame, text="Cancel", command=self.cancel)
    self._cancel_btn.pack(side=RIGHT, fill=X, expand=0)
    
  def send(self):
    """
    Will be called when the user clicks on the 'Send' button.
    """
    text = fix_unicode(self._txt.get(1.0, END))
    self._sendfunc(text)
    self._frame.destroy()
  
  def cancel(self):
    """
    Will be called when the user clicks on the 'Cancel' button.
    """
    self._sendfunc(None)
    self._frame.destroy()


def buffer_write(msg, txtbuffer, currentcolor, unfinishedcolor):
  """
  Handles writing messages to a Tk Text widget taking into accound
  ANSI colors, message types, session scoping, and a variety of
  other things.

  @param msg: the ui.message.Message to write to the buffer
  @type  msg: ui.message.Message

  @param txtbuffer: the Tk Text buffer to write to
  @type  txtbuffer: Text

  @param currentcolor: the current color that we should start with
  @type  currentcolor: color (list of ints)

  @param unfinishedcolor: the string of unfinished ANSI color stuff
      that we'll prepend to the string we're printing
  @type  unfinishedcolor: string

  @returns: the new color and unfinished color
  @rtype: list of ints, string
  """
  global myui
  line = msg.data
  ses = msg.session

  if msg.type == message.ERROR:
    if line.endswith("\n"):
      line = "%s%s%s\n" % (ansi.get_color("b blue"), 
                          line[:-1], 
                          ansi.get_color("default"))
    else:
      line = "%s%s%s" % (ansi.get_color("b blue"), 
                        line[:-1], 
                        ansi.get_color("default"))

  elif msg.type == message.USERDATA:
    if myui._do_i_echo == 1:
      if line.endswith("\n"):
        line = "%s%s%s\n" % (ansi.get_color("b blue"), 
                            line[:-1], 
                            ansi.get_color("default"))
      else:
        line = "%s%s%s" % (ansi.get_color("b blue"), 
                          line[:-1], 
                          ansi.get_color("default"))
    else:
      # if echo is not on--we don't print this
      return currentcolor, unfinishedcolor

  elif msg.type == message.LTDATA:
    if line.endswith("\n"):
      line = "# %s\n" % line[:-1].replace("\n", "\n# ")
    else:
      line = "# %s" % line.replace("\n", "\n# ")


  # now we go through and handle writing all the data
  index = 0
  start = 0

  # we prepend the session name to the text if this is not the 
  # current session sending text and if the Message is session
  # scoped.
  if (ses != None and ses != exported.get_current_session()):
    pretext = "[%s]" % ses.getName()

    if line.endswith("\n"):
      line = (pretext + line[:-1].replace("\n", "\n" + pretext) + "\n")
    else:
      line = pretext + line.replace("\n", "\n" + pretext) + "\n"


  # we remove all \\r stuff because it's icky
  line = line.replace("\r", "")

  tokens = ansi.split_ansi_from_text(line)

  # each session has a saved current color for MUDDATA.  we grab
  # that current color--or use our default if we don't have one
  # for the session yet.  additionally, some sessions have an
  # unfinished color as well--in case we got a part of an ansi 
  # color code in a mud message, and the other part is in another 
  # message.
  if msg.type == message.MUDDATA:
    color = currentcolor.get(ses, list(DEFAULT_COLOR))
    leftover = unfinishedcolor.get(ses, "")

  else:
    color = list(DEFAULT_COLOR)
    leftover = ""


  for mem in tokens:
    if ansi.is_color_token(mem):
      color, leftover = ansi.figure_color([mem], color, leftover)

    else:
      format = []
      fg = ""
      bg = ""

      # handle reverse
      if color[ansi.PLACE_REVERSE] == 0:
        if color[ansi.PLACE_FG] == -1:
          fg = "37"
        else:
          fg = str(color[ansi.PLACE_FG])

        if color[ansi.PLACE_BG] != -1:
          bg = str(color[ansi.PLACE_BG])

      else:
        if color[ansi.PLACE_BG] == -1:
          fg = "30"
        else:
          fg = str(color[ansi.PLACE_BG] - 10)

        if color[ansi.PLACE_FG] == -1:
          bg = "47"
        else:
          bg = str(color[ansi.PLACE_FG] + 10)

      # handle bold
      if color[ansi.PLACE_BOLD] == 1:
        fg = "b" + fg

      # handle underline
      if color[ansi.PLACE_UNDERLINE] == 1:
        format.append("u")

      format.append(fg)
      if bg:
        format.append(bg)

      # insert the text using the formatting tuple we just generated
      txtbuffer.insert('end', _decode(mem), tuple(format))

  return color, leftover


def fix_unicode(text):
  """
  Unicode to standard string translation--fixes unicode bug.
  """
  if type(text) == unicode:
    return text.encode(UNICODE_ENCODING)
  else:
    return text

def colorcheck_cmd(ses, args, input):
  """
  Prints out all the colors so you can verify that things are working
  properly.
  """
  myengine = exported.myengine
  myengine._ui._event_queue.put(_ColorCheckEvent())

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
