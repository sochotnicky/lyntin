#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 1999 - 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: tkui.py,v 1.1 2004/04/02 02:18:42 odbrazen Exp $
#######################################################################
"""
This is a tk oriented user interface for lyntin.  Based on
Lyntin, but largely re-coded in various areas.
"""

import Tkinter, tkFont
import os, Queue
import _tkui # all our enhanced Tk classes

# the public interface to tkui

class TkuiSession(object):
  """Handles per-session data for the UI"""
  def __init__(self, main_ui):
    self.master_ui = main_ui
    self._event_queue = main_ui._event_queue # common event queue

    # create our per-session Frames that will appear in the main UI's frames when we are active
    self.top = Tkinter.Frame(main_ui.top)
    self.middle = Tkinter.Frame(main_ui.middle)
    self.bottom = Tkinter.Frame(main_ui.bottom)
    self._txt = _tkui.ScrolledANSI(main_ui._txt,
                                   transfer_events_to=main_ui._entry,
                                   transfer_focus_to=main_ui._entry,
                                  )
    return

  def write(self, text):
    self._event_queue.put(_tkui._OutputEvent(self, text))
    return

  def write_internal(self, text):
    self._txt.write(text)
  
  def _unhide(self):
    self.middle.pack(side='bottom')
    self.top.pack(side='top')
    self.bottom.pack(side='top')
    self._txt.pack(side='bottom', fill='both', expand=1)
    return

  def _destroy(self):
    self.middle.destroy()
    self.top.destroy()
    self.bottom.destroy()
    self._txt.destroy()
    return
  
  def _hide(self):
    self.top.pack_forget()
    self.bottom.pack_forget()
    self.middle.pack_forget()
    self._txt.pack_forget()
    return

class Tkui(object):
  """
  This is a ui class which handles the complete Tk user interface.
  """
  def __init__(self, **opts):
    """ Initializes."""
    defaults = {'input_callback':None, # what to call when the user hits enter
                'shutdown':None, # an object that is true when we should cleanup
               }
    defaults.update(opts) # override with passed in opts
    
    self.input_callback = defaults['input_callback']
    self.shutdown = defaults['shutdown']
    self.active_session = None # TkuiSession instace of the current session
    self._event_queue = Queue.Queue() # internal ui queue
    self._do_i_echo = 1
    self._quit = 0  # true if we should cleanup ASAP
    self._debugger = None # debugging window, if any

    # instantiate all the widgets
    self.__tk = Tkinter.Tk()
    self._tk = self.__tk # MAJOR DEBUG, fix the one or two guys that think this is here
    self.__tk.geometry("%dx%d" % (self.__tk.maxsize()))

    self.settitle() # punt and setup the default title

    # figure out our default font, keep it around for things we create later
    if os.name == 'posix':
      self.font = tkFont.Font(family="Courier", size=12)
    else:
      self.font = tkFont.Font(family="Fixedsys", size=12)

    # setup our frames, by default we have five frames that are top-to-bottom
    #   top:     public (empty)
    #   _txt:    private, where we display scrolling text
    #   middle:  public (empty)
    #   _entry   private, where we accept input
    #   bottom:  public (empty)

    # we actually create them in an odd order, but it works
    self.bottom = Tkinter.Frame(self.__tk)
    self.bottom.pack(side='bottom')
    
    self._entry = _tkui.HistoryEntry(self.__tk, input_callback = self.handle_input,
                                     fg='white', bg='black',
                                     insertbackground='yellow', font=self.font, 
                                     insertwidth='2')
    self._entry.pack(side='bottom', fill='both')

    self.middle = Tkinter.Frame(self.__tk)
    self.middle.pack(side='bottom')

    self.top = Tkinter.Frame(self.__tk)
    self.top.pack(side='top')
    
    self._topframe = Tkinter.Frame(self.__tk)
    self._topframe.pack(side='top', fill='both', expand=1)
    self._txt = Tkinter.Frame(self._topframe)
    self._txt.pack(side='bottom', fill='both', expand=1)

    # DEBUG: I think I might have broken this.  badly.
    self._histwidget = _tkui.ScrolledANSI(self._topframe, fg='white', bg='black', font=self.font, height=20)
    #self._histwidget.bind("<KeyPress-Escape>", self.escape)
    #self._histwidget.bind("<KeyPress>", self._ignoreThis)

    # set focus to the input box
    self._entry.focus_set()

    # handle any pending events
    self.dequeue()
    return

  def launch_debugger(self, **use_globals):
    """Start a new window for the debugger,
    The options collected in <use_globals> are used to setup the environment for the debugger
    """
    self._debugger = _tkui.Debugger(self.__tk,
                                    self._event_queue,
                                    use_globals,
                                    font = self.font,
                                   )
    return

  def session_ui(self):
    """create a new TkuiSession instance and return it"""
    sess_ui = TkuiSession(self)
    return sess_ui

  def queue_event(self, eventob):
    """public interface to add an Event() based object to the event queue"""
    self._event_queue.put(eventob)
    return

  def change_session(self, sessob):
    """Change the active session to the TkuiSession object passed in"""
    # remove the current session from our displays
    if (self.active_session):
      self.active_session._hide()
    sessob._unhide()
    self.active_session = sessob
    return
  
  def run(self):
    """FIXME: alias for runui()"""
    return self.runui()
  
  def runui(self):
    # run the tk mainloop here
    self.__tk.mainloop()

  def wantMainThread(self):
    # The tkui needs the main thread of execution so we return
    # a 1 here.
    return 1

  def quit(self):
    if not self._quit:
      self._quit = 1
      self._topframe.quit()

  def dequeue(self):
    """run some Events that have been passed to us"""
    if (self.shutdown):
      self.quit()
    
    qsize = self._event_queue.qsize()
    if qsize > 10: # DEBUG, toy with this and see what happens or maybe come up with a better metric
      qsize = 10

    for i in range(qsize):
      ev = self._event_queue.get_nowait()
      ev.execute(self)

    self.__tk.after(25, self.dequeue) # reschedule ourselves to happen again very soon
    return

  def settitle(self, title="LeanLyn"):
    """ Sets the title bar to the Lyntin title plus the given string. """
    self._event_queue.put(_tkui.TitleEvent(title))

  def write(self, text):
    """ This writes text to the text buffer for viewing by the user. """
    self._event_queue.put(_tkui._OutputEvent(self.active_session, text))
    return

  def handle_input(self, text):
    self.input_callback(text)
    return
