#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: exported.py,v 1.1 2003/05/05 05:54:19 willhelm Exp $
#######################################################################
"""
This is the X{API} for lyntin internals and is guaranteed to change 
very rarely even though we might change Lyntin's internals.  If
it does change it'll be between major Lyntin versions.
"""
import sys, traceback
import engine, ui.ui, __init__

def lyntin_command(text, internal=0, session=None):
  """
  The best way of executing a Lyntin command as if the user had typed it.

  @param text: the command to execute.  ex. "#help"
  @type  text: string

  @param internal: whether (1) or not (0) to execute the line internally 
      suppressing history and the spamhook.
  @type  internal: boolean

  @param session: the session instance to execute this command in
      (defaults to the current session)
  @type  session: Session
  """
  if session != None:
    get_engine().handleUserData(text, internal, session)
  else:
    get_engine().handleUserData(text, internal)


def add_command(cmd, func, arguments=None, argoptions=None, helptext=""):
  """
  The best way to add commands to Lyntin.

  @param cmd: the command name to add.  ex. "help"
  @type  cmd: string

  @param func: the function to call to handle the command
  @type  func: function

  @param arguments: the argument spec for building the ArgumentParser
  @type  arguments: string

  @param argoptions: the options to give the ArgumentParser to tell it
      how to parse the arguments
  @type  argoptions: string

  @param helptext: the helptext associated with this command to give to
      the HelpManager
  @type  helptext: string
  """
  get_manager("command").addCommand(cmd, func, arguments, argoptions, helptext)

def remove_command(text):
  """
  Removes a command from Lyntin.

  @param text: the name of the command to remove
  @type  text: string

  @return: 0 if no command was found, 1 if the command was removed
      successfully
  @rtype: boolean
  """
  return get_manager("command").removeCommand(text)

def get_commands():
  """
  Returns a list of the commands currently bound.

  @return: the list of commands currently registered with Lyntin
  @rtype: list of strings
  """
  return get_manager("command").getCommands()

def add_manager(name, mgr):
  """
  Registers a manager with the engine.

  @param name: the name of the manager to register with Lyntin
  @type  name: string

  @param mgr: the manager instance being registered
  @type  mgr: manager.Manager
  """
  get_engine().addManager(name, mgr)

def remove_manager(name):
  """
  Removes a manager from the engine.

  @param name: the name of the manager to remove from Lyntin
  @type  name: string

  @return: 0 if nothing happened, 1 if the manager was removed
  @rtype: boolean
  """
  return get_engine().removeManager(name)

def get_manager(name):
  """
  Retrieves a manager from the engine.

  @param name: the name of the manager to retrieve
  @type  name: string

  @return: the manager instance
  @rtype: manager.Manager
  """
  return get_engine().getManager(name)

def add_help(fqn, helptext):
  """
  Adds a help topic to the structure.  See the helpmanager documentation
  for more details as to what the helptext should look like.

  @param fqn: a . delmited string of categories ending
      with a help name
  @type  fqn: string

  @param helptext: the help text
  @type  helptext: string

  @return: the fqn of where the help topic was stored (you can place
      category overrides in the helptext)
  @rtype: string
  """
  return get_manager("help").addHelp(fqn, helptext)

def remove_help(fqn):
  """
  Removes a help topic from Lyntin.

  @param fqn: a . delmited string of categories ending
      with a help name
  @type  fqn: string
  """
  get_manager("help").removeHelp(fqn)

def get_help(fqn):
  """
  Retrieves a help topic via a fully qualified name.

  @param fqn: a . delimited string of categories ending
      with a help name
  @type  fqn: string

  @return: the help topic of that name or None if the topic
      doesn't exist
  @rtype: string
  """
  return get_manager("help").getHelp(fqn)

def expand_ses_vars(text, ses):
  """
  Grabs the variable manager (which we're hoping is using the
  same expand_vars as what's registered--only time will tell)
  and expands variables using the variable manager and its
  varmap.

  @param text: the text to expand variables in
  @type  text: string

  @param ses: the session object to pass to the VariableManager
  @type  ses: session.Session

  @return: the text with variables expanded
  @rtype: string
  """
  vm = get_manager("variable")
  if vm:
    return vm.expand(ses, text)
  return text

def get_session(name):
  """
  Returns a named session or None if the session doesn't exist.

  @param name: the name of the session to retrieve
  @type  name: string

  @return: the session instance or None
  @rtype: session.Session
  """
  return get_engine().getSession(name)

def get_active_sessions():
  """
  Returns a list of the active sessions including the common one.

  @return: the list of active sessions
  @rtype: list of session.Session's
  """
  return get_engine()._sessions.values()

def get_current_session():
  """
  Returns the current session.

  @return: the current session
  @rtype: session.Session
  """
  return get_engine().currentSession()

def set_current_session(ses):
  """
  Changes the current session to another session.

  @param ses: the session instance to set the current session to
  @type  ses: session.Session
  """
  get_engine()._current_session = ses
    
def get_num_errors():
  """
  Returns the total number of errors Lyntin has had thus far.

  @return: the number of unhandled errors Lyntin has encountered so far
  @rtype: int
  """
  return __init__.errorcount
 
def set_num_errors(num):
  """
  Sets the number of errors Lyntin has had thus far.  Do be careful
  when setting this because Lyntin keeps track of errors for a reason.

  @param num: the number of errors to set
  @type  num: int
  """
  __init__.errorcount = num

def write_ui(text):
  """
  Calls engine.myengine.writeUI which writes a message to the ui.
  If there is no engine instance available, it prints it to sysout.

  @param text: the message to write to the ui
  @type  text: string or ui.Message
  """
  if get_engine():
    get_engine().writeUI(text)
  else:
    print text

def write_message(text, ses=None):
  """
  Calls engine.myengine.writeMessage which writes LTDATA message.
  If there is no engine instance available, it prints it to sysout.

  @param text: the message to send
  @type  text: string

  @param ses: the session instance the error data is associated with
  @type  ses: session.Session
  """
  text = str(text)
  if get_engine():
    get_engine().writeUI(ui.ui.Message(text + "\n", ui.ui.LTDATA, ses))
  else:
    print "message:", text

def write_error(text, ses=None):
  """
  Calls engine.myengine.writeError which writes ERROR message.
  If there is no engine instance available, it prints it to sysout.

  @param text: the message to send
  @type  text: string

  @param ses: the session instance the error data is associated with
  @type  ses: session.Session
  """
  text = str(text)
  if get_engine():
    get_engine().writeUI(ui.ui.Message(text + "\n", ui.ui.ERROR, ses))
  else:
    print "error:", text

def write_user_data(text, ses=None):
  """
  Calls engine.myengine.writeUserData which writes a USERDATA message.
  If there is no engine instance available, it prints it to sysout.

  @param text: the message to send
  @type  text: string

  @param ses: the session instance the user data is associated with
  @type  ses: session.Session
  """
  text = str(text)
  if get_engine():
    get_engine().writeUI(ui.ui.Message(text + "\n", ui.ui.USERDATA, ses))
  else:
    print "userdata:", text

def write_mud_data(text, ses=None):
  """
  Calls engine.myengine.writeMudData which writes a MUDDATA message.
  If there is no engine instance available, it prints it to sysout.

  @param text: the message to send
  @type  text: string

  @param ses: the session instance the mud data is associated with
  @type  ses: session.Session
  """
  text = str(text)
  if get_engine():
    get_engine().writeUI(ui.ui.Message(text, ui.ui.MUDDATA, ses))
  else:
    print "muddata:", text

def write_traceback(message="", ses=None):
  """
  Convenience method for grabbing the traceback, formatting it, 
  piping it through write_error, with a message for the user.

  @param message: any message you want to pass to the user--this
      gets printed first
  @type  message: string

  @param ses: the session instance the mud data is associated with
  @type  ses: session.Session
  """
  exc = "".join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]))

  if message:
    message = message + "\n" + exc
  else:
    message = exc
  write_error(message, ses)


def get_history(count=30):
  """
  Retrieves the history as a oldest to youngest list of strings.

  @param count: the number of lines to return
  @type  count: int

  @return: the history oldest to youngest
  @rtype: list of strings
  """
  return get_manager("history").getHistory(count)

def get_engine():
  """
  Nice way of retrieving the engine instance.

  @return: the Engine singleton instance
  @rtype: engine.Engine
  """
  return engine.myengine

def tally_error():
  """
  This adds one to the current error count and checks to see
  if we're over our limit.  If we are, it enqueues a shutdown
  event which will shutdown Lyntin.
  """
  get_engine().tallyError()

def hook_register(hookname, func, place=None):
  """
  Registers a function with a hook.

  @param hookname: the name of the hook
  @type  hookname: string

  @param func: the function to register with the hook
  @type  func: function

  @param place: the function will get this place in the call
      order.  functions with the same place specified will get
      arbitrary ordering.  defaults to hooks.LAST.
  @type  place: int
  """
  if place == None:
    get_manager("hook").register(hookname, func)
  else:
    get_manager("hook").register(hookname, func, place)
    
def hook_unregister(hookname, func):
  """
  If the hook exists, unregisters the func from the hook.

  @param hookname: the name of the hook
  @type  hookname: string

  @param func: the function to remove from the hook
  @type  func: function
  """
  get_manager("hook").unregister(hookname, func)

def get_hook(hookname):
  """
  If the hook exists, returns the hook.  Otherwise it creates
  a new hook and returns that.

  @param hookname: the name of the hook to retrieve
  @type  hookname: string

  @returns: the Hook by the name of hookname
  @rtype: Hook
  """
  return get_manager("hook").getHook(hookname)

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
