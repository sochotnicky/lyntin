#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 1999 - 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: tkui.py,v 1.3 2004/05/04 05:02:04 odbrazen Exp $
#######################################################################
"""
This is a tk oriented user interface for lyntin.  Based on
Lyntin, but largely re-coded in various areas.
"""

import Tkinter, tkFont
import os, Queue
import _tkui # all our enhanced Tk classes
import sys, traceback # to print errors
import ansi

# the public interface to tkui

class TkuiSession(object):
  """Handles per-session data for the UI"""
  def __init__(self, tkui, **opts):
    # our run_this_soon() will hand off to the main run_this_soon
    self.__main_run_this_soon = tkui.run_this_soon

    self.hidden = 1 # new ui's always start out hidden
    self.echoing = 1 # should we echo the entry box
    self.scroller_size = (-1, -1) # how big is the scroller, in pixels
    self.size_change = opts.get('size_change_callback', None)
    self.font = tkui.font
    self._entry = tkui._entry # we need this to turn echoing on/off
    
    # create our per-session Frames that will appear in the main UI's frames when we are active
    self.top = Tkinter.Frame(tkui.top)
    self.middle = Tkinter.Frame(tkui.middle)
    self.bottom = Tkinter.Frame(tkui.bottom)
    def print_url(url):
      print "URL ", url
    self._txt = _tkui.ScrolledANSI(tkui._txt,
                                   open_url_command=print_url,
                                   transfer_events_to=tkui._entry,
                                   transfer_focus_to=tkui._entry,
                                  )
    self._txt.bind('<Configure>', self.scroller_grew)
    self.user_opts = None # standard spot for people to store an options object
    self.error_color = {'fg':'blue', 'bg':'white'}
    self.local_color = {'fg':'green', 'bg':'blue'}
    return

  def scroller_grew(self, event):
    """ A Tk event, someone changed the size of our text widget """
    w = event.width
    h = event.height
    print "scroller grew", (w, h)
    if (self.hidden): # ignore it, we're not even visible
      return
    (old_w, old_h) = self.scroller_size
    if (w != old_w or h != old_h):
      self.scroller_size = (w, h)
      # do pixel math to figure how many chars wide/tall we are, hope it is close enough
      char_w = int(w / (float(self.font.measure('abcdeFGHIJ'))/10))
      char_h = int(h / self.font.metrics()['ascent']) # unsure about this one
      if (self.size_change):
        self.size_change(char_w, char_h)
    return

  def run_this_soon(self, func):
    """ Ask for func to be executed soon in the main UI loop"""
    # _tkuisess is added ONLY so we know where to write errors when we pop events
    func._tkuisess = self
    self.__main_run_this_soon(func)
    return

  def echo_change(self, echo_onoff):
    """ update the echo state to echo_onoff """
    print "Hidden? %d, echoing %d => %d" % (self.hidden, self.echoing, echo_onoff)
    self.echoing = echo_onoff
    if (not self.hidden): # doesn't matter if we're not visible
      if (echo_onoff):
        self._entry.echo_on()
      else:
        self._entry.echo_off()
    return
  
  def write(self, text, **this_color):
    """ Write some text in this_color (defaulting to self.local_color)
        to this session's screen
    """
    # define a function to be called from the tk thread
    def write_it():
      color = this_color or self.local_color
      self._txt.color_write(text, **color)
    self.run_this_soon(write_it)
    return

  def write_mud_text(self, text):
    """ Write some text from the mud to this session's screen
        NB: This keeps track of the stream of ANSI code from the mud,
        if you want to write colored text use write() instead
    """
    # define a function to be called from the tk thread
    def write_it():
      self._txt.write(text)
    self.run_this_soon(write_it)
    return

  def write_prompt_text(self, text):
    """ Write a line that isn't newline terminated.
        This is called when we may have a prompt
    """
    def write_it():
      self._txt.write(text+"\n")
    self.run_this_soon(write_it)
    return

  def write_error(self, text):
    """ Write an error message in self.error_color to this session's screen """
    # define a function to be called from the tk thread
    def write_it():
      self._txt.color_write(text, **self.error_color)
    self.run_this_soon(write_it)
    return
  
  def _unhide(self):
    self.middle.pack(side='bottom')
    self.top.pack(side='top')
    self.bottom.pack(side='top')
    self._txt.pack(side='bottom', fill='both', expand=1)
    self._txt._yadjust() # makes sure we're at the bottom of the scroll
    self.hidden = 0
    self.echo_change(self.echoing)
    return

  def _destroy(self):
    self.middle.destroy()
    self.top.destroy()
    self.bottom.destroy()
    self._txt.destroy()
    self.echo_change(self.echoing)
    self.hidden = 1
    return
  
  def _hide(self):
    self.echo_change(self.echoing)
    self.hidden = 1
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
    self._debugger = None # debugging window, if any

    # instantiate all the widgets
    self.__tk = Tkinter.Tk()
    self.__tk.geometry("%dx%d" % (self.__tk.maxsize()))
    
    print self.__tk.geometry()

    self.title() # punt and setup the default title

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

    # kick off our timed queue runner
    self.__run_callback_queue()
    return

  def launch_debugger(self, **use_globals):
    """Start a new window for the debugger,
    The options collected in <use_globals> are used to setup the environment for the debugger
    """
    self._debugger = _tkui.Debugger(self.__tk,
                                    self.run_this_soon,
                                    use_globals,
                                    font = self.font,
                                   )
    return

  def session_ui(self, **opts):
    """create a new TkuiSession instance and return it"""
    sess_ui = TkuiSession(self, **opts)
    return sess_ui

  def run_this_soon(self, func):
    """ Ask for func to be executed soon in the main UI loop"""
    self._event_queue.put(func)
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
    """ run the tk mainloop """
    self.__tk.mainloop()

  def __run_callback_queue(self):
    """run some callbacks added by run_this_soon() """
    if (self.shutdown):
      self.__tk.quit()
    
    qsize = self._event_queue.qsize()
    if qsize > 10: # DEBUG, toy with this and see what happens or maybe come up with a better metric
      qsize = 10

    for i in range(qsize):
      try:
        callback = self._event_queue.get_nowait()
      except Queue.Empty:
        break

      try:
        callback() # try and call it
      except (Exception), e:
        traceback_msg = ''.join(traceback.format_exception(type(e), e, sys.exc_traceback))
        try:
          callback._tkuisess.write_error(traceback_msg)
        except: # likely an error created outside ANY session, use stderr because we're in trouble
          sys.stderr.write(traceback_msg)
    
    self.__tk.after(25, self.__run_callback_queue) # reschedule ourselves to happen again very soon
    return

  def title(self, title="LeanLyn"):
    """ Sets the title bar to the Lyntin title plus the given string. """
    def title_callback():
      self.__tk.title(title)
    self.run_this_soon(title_callback)
    return

  def handle_input(self, text):
    """ handle a line from the command entry box """
    # call the input callback
    try:
      self.input_callback(text)
    except (Exception,), e:
      self.active_session.write_error(''.join(traceback.format_exception(type(e), e, sys.exc_traceback)))
    return
