"""
This module defines Events for the Tkui
Becuase of the way he handle threading if you want to do anyting
to the tkui we have to wrap what you want done until the UI
is ready to do it.  Create the Event object, and queue() it up.
The next time the UI updates (milliseconds later) it will get done.
see TitleEvent for a simple event example.
"""

class Event:
  def __init__(self, *args, **opts):
    """define this to pass in all the information you will need to
    do an event.  You will access this when execute() is called
    from the tk thread
    """
    return

  def execute(self, tkui):
    """perform the actual action setup in the constructor"""
    return

class TitleEvent(Event):
  """FIXME, this event is wrong"""
  def __init__(self, title):
    self._title = title
    return
  
  def execute(self, root_window):
    root_window._tk.title(self._title)
    return
  
# anything below is used privately by tkui, don't use these

class _OutputEvent(Event):
  def __init__(self, tksess, text):
    self._text = text
    self._sess = tksess
    return

  def execute(self, tkui):
    self._sess.write_internal(self._text)
    return

class _WriteWindowEvent(Event):
  def __init__(self, windowname, message):
    self._windowname = windowname
    self._message = message

  def execute(self, tkui):
    tkui.writeWindow_internal(self._windowname, self._message)

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
