"""
These are some helper text entry widgets derived from the Tk.Entry class
"""

from Tkinter import *
import os, tkFont

UNICODE_ENCODING = "latin-1"
def clean_line(text):
  """force unicode type and remove suprising newline types from a line"""
  # force the unicode type, historical and reduces suprises
  if type(text) == unicode:
    text = text.encode(UNICODE_ENCODING)
  # remove alternate OS newlines
  text = text.replace('\r', '')
  # remove quoted newlines
  text = text.replace('\\n', "\n")
  return text
  
class HistoryEntry(Entry):
  """ This class extends the Basic Tk.Entry by adding history,
  as well as cleaning the input (for unicode and strange linebreaks)
  accepts two options
  input_callback = <function> # Required: call this function when the user hits the enter key
  history_size = <int> # optional, the size of the history buffer.  defaults to 100
  """

  def __init__(self, root, **kw):
    """ Initializes and sets the key-bindings."""
    # strip off our options
    self.callback = kw.pop('input_callback', None)
    self.maxhist = kw.pop('history_size', 100) # how big the size of the history is
    
    # pass everything else to our Tk.Entry parent
    Entry.__init__(self, root, **kw)
    
    self._history = [] # command history
    self._history_index = None # where we are currently browsing in the history, None if we aren't browsing the history

    # what to do when they hit <ENTER>
    self.bind("<KeyPress-Return>", self.handle_input)
    self.bind("<KeyPress-KP_Enter>", self.handle_input)

    # alias history to keys commonly used for history
    self.bind("<KeyPress-Up>", self.history_up)
    self.bind("<Control-KeyPress-Up>", self.history_up)
    self.bind("<Control-KeyPress-p>", self.history_up) # unix shell
    self.bind("<KeyPress-Down>", self.history_down)
    self.bind("<Control-KeyPress-Down>", self.history_down)
    self.bind("<Control-KeyPress-n>", self.history_down) # unix shell

    # I'm not sure what this one immitates, windows or the original tintin maybe?
    self.bind("<Control-KeyPress-u>", self.clear_input)

    # this next line totally hoses win32, so don't uncomment it
    # self.bind("<Destroy>", self.deathHandler)
    return
  
  def handle_input(self, tkevent):
    """ Someone hit the Enter button, cleanup the input and pass it along """
    text = self.get() # raw input
    text = clean_line(text)
    self.add_to_history(text)
    self.clear_input()
    self.callback(text+"\n") # this fails nice and loudly if there is no callback
    return

  def clear_input(self):
    """ Clears the text widget."""
    self.delete(0, 'end')
    return

  def replace_input(self, text):
    """ Replaces what is in the input line with <text> """
    self.clear_input()
    self.insert(0, text)
    return

  def echo_off(self):
    """ Turn off echoing in the entry box """
    self.configure(show='*')
    return

  def echo_on(self):
    """ Turn on echoing in the entry box """
    self.configure(show='')
    return

  def add_to_history(self, text):
    """Add the line to our history and crop the history buffer"""
    self._history.append(text)
    self._history[:-self.maxhist] = [] # crop the history buffer using a slice (doesn't do a copy)
    self._history_index = None # adding to history clears our history browsing position
    return

  def history_up(self, ignored_tkevent):
    # if we weren't already browsing the history    
    if (self._history_index is None):
      unfinished_line = clean_line(self.get())
      if (unfinished_line.strip()): # store what they were typing at the time if it wasn't empty
        self.add_to_history(unfinished_line) # NB, we store without the strip()
        self._history_index = -1 # points at the line just inserted
      else:
        self._history_index = 0 # decremented immediately to point at the last line of history

    self._history_index -= 1
    try:
      old_line = self._history[self._history_index]
      self.replace_input(old_line)
    except IndexError: # we ran out of history
      self._history_index += 1 # reset the index to where it just was
    return

  def history_down(self, ignored_tkevent):
    if (self._history_index is None): # no where to go
      return
    self._history_index += 1
    if (self._history_index >= 0): # back to 'live' typing, tell the index to forget us
      self.clear_input()
      self._history_index = None
      return

    # fetch the line from history
    new_line = self._history[self._history_index]
    self.replace_input(new_line)
    return

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
