#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: base.py,v 1.8 2004/04/16 22:05:48 willhelm Exp $
#######################################################################
"""
Holds the base ui class for Lyntin as well as the get_ui function
"""
import string, re, sys, os
from lyntin import exported, utils
from lyntin.ui import message


def get_ui(uiname):
  """
  Attempts to retrieve the ui by that name.

  @param uiname: the name of the ui passed in by the command line
  @type  uiname: string

  @return: a BaseUI subclass instance corresponding to the name
      of the ui the user wants to instantiate.  or None if the ui
      could not be found or instantiated.
  @rtype: BaseUI subclass
  """
  path = "lyntin.ui." + uiname
  try:
    _module = __import__(path)
    _module = sys.modules[path]
  except ImportError:
    raise ValueError("ui '%s' does not exist." % uiname)
  return _module.get_ui_instance()

class BaseUI:
  """
  Base ui class.

  This is the Base UI class which defines the interface between
  the ui's and Lyntin.
  """
  def __init__(self):
    """
    If you have initializations to do, override this class,
    but call this function like this::

      BaseUI.__init__(self)

    then go on to do the initializing you need to do.
    """
    self.shutdownflag = 0
    import lyntin.exported
    lyntin.exported.hook_register("shutdown_hook", self.shutdown)

  def runui(self):
    """
    The engine executes this expecting your mainloop to start and
    you to take control of the main thread of execution.  Put
    whatever other initialization you need to do here and then 
    go into your main loop.
    """
    pass

  def wantMainThread(self):
    """
    This should return 0 (if you don't want the main thread of
    execution for the ui) or a 1 (if you do want the main thread
    of execution for the ui).  This defaults to 0.

    @returns: 0 or 1
    @rtype: boolean
    """
    return 0

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
    pass

  def prompt(self):
    """
    Prints a prompt to the user.  This is mostly for niceties so the 
    user knows that Lyntin is awaiting input.  It should just print
    a prompt.  Prompts only get printed by the common session.
    """
    pass

  def shutdown(self, args):
    """
    Tells the user interface thread to shutdown.  This is 
    registered with the shutdown_hook.  Implement this method
    if you have shutdown stuff to do.

    @param args: it's an empty tuple--we ignore this
    @type  args: tuple of 0 length
    """
    self.shutdownflag = 1

  def flush(self):
    """
    Flushes output to the user.  Currently we don't do any flushing
    and it shouldn't be needed.  I'm not wholly sure why it's here.
    """
    pass

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
    if ses == None or getattr(ses, "_snoop", None) == None \
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
    event.InputEvent(input).enqueue()

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
