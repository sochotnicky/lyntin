#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: event.py,v 1.4 2003/08/05 13:17:08 willhelm Exp $
#######################################################################
"""
Holds the X{event} structures in Lyntin.  All events inherit from 
Event.  This is pretty standard, nothing really exciting here.
Each event class implements the execute function which gets called
by the event handler thread when it pulls the event object off the
event queue.  You can use the __init__ function to initialize
your event as it is not used in the base Event class.
"""
import string, os, sys, traceback
from lyntin import __init__, exported, constants

class Event:
  """
  This is the basic Event class.  It has an enqueue method
  which enqueues the event in the event queue (in the engine
  module).  It also has an execute method which is executed
  when the event is dequeued and handled.  Override the
  'execute' function for your functionality to get executed.
  """
  def __init__(self):
    """
    Override this to do your event initialization here.
    """
    pass

  def __str__(self):
    """
    This allows us to print out event objects for debugging
    purposes.  Feel free to override this as well.
    """
    ret = str(self.__class__)
    return ret[ret.find(".") + 1:]

  def enqueue(self):
    """
    This enqueues this event into the event queue.
    Don't overload this unless you have to.
    """
    exported.get_engine()._enqueue(self)

  def execute(self):
    """
    Override this.  This gets called by the engine during event handling
    to execute the event.
    """
    pass


class StartupEvent(Event):
  """
  Starts up and initializes Lyntin.

  When Lyntin is started, we try to do as much as we can
  inside of the SstartupEvent and through the startup hook.
  """
  def __init__(self):
    """
    Initialize.  (does nothing)
    """
    pass

  def execute(self):
    """
    This does the following Lyntin startup things:

      1. instantiates and binds the ui.
      2. if there's a .lyntinrc adds that to the readfile list.
      3. loads the dynamically loading Lyntin modules.
      4. reads in all the files in the readfile list.
      5. starts the timer thread.
      6. writes the startup message to the ui and the prompt.
    """
    import utils

    uiinstance = None
    try:
      # instantiate a ui
      uiname = __init__.options['ui']
      modulename = uiname + "ui"

      import ui.base

      uiinstance = ui.base.get_ui(modulename)
      if not uiinstance:
        raise ValueError, "No ui instance."
      exported.get_engine().setUI(uiinstance)
      exported.write_message("UI started.")
    except Exception, e:
      print "Cannot start '%s': %s" % (uiname, e)
      traceback.print_exc()
      if not uiinstance:
        try:
          # if we had problems, we try to instantiate the textui
          uiinstance = ui.base.get_ui("textui")
          if not uiinstance:
            raise ValueError, "No ui instance."
          exported.get_engine().setUI(uiinstance)
          exported.write_message("UI started.")
        except Exception, e2:
          print "Cannot start textui either: %s" % e2
          traceback.print_exc()
          sys.exit(0)
      else:
        sys.exit(0)


    # tests to see if dirs provided exist
    if __init__.options['datadir']:
      if utils.exists_dir(__init__.options['datadir']) == 0:
        exported.write_error("datadir '%s' does not exist." % __init__.options['datadir'])
        __init__.options['datadir'] == ''

    if __init__.options['moduledir']:
      modlist = __init__.options['moduledir']
      for mem in modlist:
        if utils.exists_dir(mem) == 0:
          exported.write_error("moduledir '%s' does not exist." % mem)
          __init__.options['moduledir'].remove(mem)


    # adds the .lyntinrc file to the readfile list if it exists.
    if __init__.options['datadir']:
      lyntinrcfile = __init__.options['datadir'] + ".lyntinrc"
      try:
        test = os.stat(lyntinrcfile)
        # we want the .lyntinrc file read in first, so then other
        # files can overwrite the contents therein
        __init__.options['readfile'].insert(0, lyntinrcfile)
      except OSError, e:
        pass


    # import modules listed in modulesinit
    exported.write_message("Loading Lyntin modules.")

    try:
      import modules.__init__
      modules.__init__.load_modules()
    except:
      exported.write_traceback("Modules did not load correctly.")
      ShutdownEvent().enqueue()

    # spam the startup hook 
    exported.hook_spam("startup_hook", {})

    # handle command files
    for mem in __init__.options['readfile']:
      exported.write_message("Reading in file " + mem)
      # we have to escape windows os separators because \ has a specific
      # meaning in the argparser
      mem = mem.replace("\\", "\\\\")
      exported.lyntin_command("%sread %s" % (__init__.commandchar, mem), internal=1)

    # start the timer thread
    exported.get_engine().startthread("timer", exported.get_engine().runtimer)

    # we're done initialization!
    exported.write_message(constants.STARTUPTEXT)
    exported.get_engine().writePrompt()


class ShutdownEvent(Event):
  """
  This calls sys.exit(0) which will trigger the Python atexit stuff.
  """
  def __init__(self):
    """ Initialize."""
    pass

  def execute(self):
    """ Execute the shutdown."""
    sys.exit(0)

class EchoEvent(Event):
  """
  Echo events get created when the connected server sends a Telnet
  Echo request--either to tell us that the server is handling echo
  (echo off) or that the server will not handle echo (echo on).
  """
  def __init__(self, onoff):
    """
    Initializes the EchoEvent.

    @param onoff: sets the new echo value.  1 for echo on, 0 for echo off.
    @type  onoff: int
    """
    self._state = onoff

  def execute(self):
    """ Runs the echo event through anything listening."""
    exported.hook_spam("mudecho_hook", {"yesno": self._state})
    __init__.mudecho = self._state


class MudEvent(Event):
  """
  A mud event is when the connected mud sends data to us.  We
  spam that data to the mud event hook.
  """
  def __init__(self, session, input):
    """
    Initializes the MudEvent.

    @param session: the session handling this mud connection
    @type  session: session.Session instance

    @param input: the data sent from the mud that we need to handle
    @type  input: string
    """
    self._session = session
    self._input = input

  def execute(self):
    """ Execute."""
    exported.hook_spam("from_mud_hook", {"session": self._session, "data": self._input})
    exported.get_engine().handleMudData(self._session, self._input)


class InputEvent(Event):
  """
  A user input event is created whenever the user types something
  into their ui and it creates a user event from it.
  """
  def __init__(self, input, internal=0, ses=None):
    """
    Initializes the InputEvent.

    @param input: the data from the user
    @type  input: string

    @param internal: whether this is an internally generated user
        input.  if it is internally generated then we don't record
        it in history.  1 if it's internal, 0 if not.
    @type  internal: int

    @param ses: the session execute the input event in
    @type  ses: session.Session
    """
    self._input = input
    self._internal = internal
    self._ses = ses

    if not self._input:
      self._input = __init__.commandchar + "cr"

  def execute(self):
    """ Execute."""
    if not self._internal:
      exported.write_user_data(self._input)

    exported.lyntin_command(self._input, internal=self._internal, session=self._ses)


class OutputEvent(Event):
  """
  Sometimes it's necessary to put data that's going to the ui
  into an event so that it is displayed in the correct order.
  This event allows you to do that.
  """
  def __init__(self, message):
    """
    Initializes the OutputEvent.

    @param message: the message to go to the ui
    @type  message: string
    """
    self._message = message

  def execute(self):
    """ Execute."""
    exported.write_ui(self._message)


class SpamEvent(Event):
  """
  Certain things can kick off a call to spam a hook.  Rather
  than doing it "inline" so to speak, it's sometimes nice to kick
  it off in its own event.  The timer uses this to handle kicking
  anything that's listening to the timer_hook.
  """
  def __init__(self, *vargs, **nargs):
    """
    Initializes the SpamEvent.
    """
    self._vargs = vargs
    self._nargs = nargs

  def execute(self):
    """ Execute."""
    exported.hook_spam(*(self._vargs), **(self._nargs))

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
