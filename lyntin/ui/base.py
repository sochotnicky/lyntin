#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: base.py,v 1.3 2003/08/01 00:29:41 willhelm Exp $
#######################################################################
"""
Holds the ui components in lyntin as well as the Message
class.  The Message class encapsulates a message to be displayed
to the user through the ui.  Messages have types and the ui
will display the message differently depending on the type.
"""
import string, re, sys
from lyntin import exported, utils
from lyntin.ui import message

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

  def startui(self, args):
    """
    Initializes your user interface.  It's best to do all your 
    initialization logic in startui including the call to start w
    hatever thread will handle polling for user input.
    """
    pass

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

  def run(self):
    """
    The ui's typically have their own thread to poll for user input.
    If so, then you'll implement this method and toss it in a thread.
    Then launch the thread in the startui method.  DON'T do it in 
    __init__ because Lyntin won't have been bootstrapped enough at 
    that point.
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
    attribute, it's the current session, or ses.getSnoop() == 1.

    @param ses: the session we're looking at--if it's None we return a 1
    @type  ses: Session

    @returns: 1 if we should show text, 0 if not
    @rtype: boolean
    """
    if ses == None or getattr(ses, "_snoop", None) == None \
        or exported.get_current_session() == ses or ses.getSnoop() == 1:
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
