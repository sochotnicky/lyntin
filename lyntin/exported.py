#########################################################################
# This file is part of Lyntin.
#
# Lyntin is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Lyntin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# copyright (c) Free Software Foundation 2001-2007
#
# $Id: exported.py,v 1.18 2007/07/24 00:39:03 willhelm Exp $
#########################################################################
"""
This is the X{API} for lyntin internals and is guaranteed to change 
very rarely even though we might change Lyntin's internals.  If
it does change it'll be between major Lyntin versions.

X{write_hook}::

   The write_hook allows you to persist data.  Functions that register
   with this hook should return a list of strings.

   For example, the alias plugin would register with this hook and if
   I had an alias vv, it would return:

      [ "alias {vv} {this is my alias}" ]

   as its data.  If quiet == 1, then it would return:

      [ "alias {vv} {this is my alias} quiet={true}" ]

   because "quiet" is an argument for the alias command which quells
   output when it's called (assuming the output isn't error output).

   Arg mapping: {"session": Session, "quiet": boolean }

   session - the session in question

   quiet - whether (1) or not (0) to append an argument that causes
           the command to quell input when it is later read in
"""
import sys, traceback
from lyntin import utils, constants
from lyntin.ui import message

LAST = 99
FIRST = 1

myengine = None

def get_engine():
  """
  This is a helper function provided for backwards compatibility with
  older modules.
  """
  return myengine

class StopSpammingException(Exception):
  """
  This is what you raise when you're implementing a handler hook
  and you've handled the data.  This will cause the hook to stop
  iterating through the rest of the hook functions.
  """
  pass

class DoneSpammingException(Exception):
  def __init__(self, output):
    self.output = output

def lyntin_command(text, internal=0, session=None):
  """
  The best way of executing a Lyntin command as if the user had typed it.

  This executes "#help", doesn't create an entry in the history, and
  doesn't spam the from_user_hook::

    from lyntin.exported import lyntin_command
    lyntin_command("#help", internal=1, session=None)

  This executes "#action {killing blow} {reclaim}", creates an entry
  in the history, spams the from_user_hook, and does it in the session
  named "a"::

    from lyntin.exported import lyntin_command, get_session
    lyntin_command("#action {killing blow} {reclaim}", internal=0, session=get_session("a"))


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
    myengine.handleUserData(text, internal, session)
  else:
    myengine.handleUserData(text, internal)


def add_command(cmd, func, arguments=None, argoptions=None, helptext=""):
  """
  This function allows you to add additional commands to Lyntin.
  Note, if you add a command that has the same name as an existing
  command, we'll first remove the existing command and then add
  the new command (this is done in the CommandManager).

  If you add a E{^} to the beginning of the command name, then the user
  has to type the entire command name for it to kick off.  For
  example, if I specified "E{^}end", then the user has to type "#end"
  to execute that command.  If I had specified "end", then the user
  could type "e", "en", or "end".

  If you don't specify helptext and the function has a doc_string,
  then we'll pull the helptext from the function's doc_string.

  This creates a basic command that has no arguments or argoptions
  and adds it to the CommandManager::

    import os
    from lyntin.exported import add_command

    ht = "This command does an os.system("who") to let you see " + \
         "who's online\\nright now."

    def who_cmd(ses, args, input):
      os.system("who")

    add_command("who", who_cmd, "", None, ht)


  Same thing, but the help text is in the doc_string of the command::

    import os
    from lyntin.exported import add_command

    def who_cmd(ses, args, input):
      \"\"\"
      This command does an os.system("who") to let you see who's
      online right now.
      \"\"\"
      os.system("who")

    add_command("who", who_cmd)


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
  Returns a list of the existing commands in Lyntin.

  @return: the list of commands currently registered with Lyntin
  @rtype: list of strings
  """
  return get_manager("command").getCommands()

def add_manager(name, mgr):
  """
  Registers a manager with the engine.

  example of usage::

     from lyntin.exported import add_manager
     from lyntin import manager

     class MyManager(manager.Manager):
       def __init__(self):
         pass

     add_manager("mymanager", MyManager)


  Managers are pretty straightforward especially considering that
  Lyntin makes great use of them so there are lots of examples.

  @param name: the name of the manager to register with Lyntin
  @type  name: string

  @param mgr: the manager instance being registered
  @type  mgr: manager.Manager
  """
  myengine.addManager(name, mgr)

def remove_manager(name):
  """
  Removes a manager from the engine.

  @param name: the name of the manager to remove from Lyntin
  @type  name: string

  @return: 0 if nothing happened, 1 if the manager was removed
  @rtype: boolean
  """
  return myengine.removeManager(name)

def get_manager(name):
  """
  Retrieves a manager from the engine.

  @param name: the name of the manager to retrieve
  @type  name: string

  @return: the manager instance
  @rtype: manager.Manager
  """
  return myengine.getManager(name)

def get_config(name, ses=None, defaultvalue=constants.NODEFAULTVALUE):
  """
  Gets a value for a config item.  If the default value is
  not specified, then it will raise a ValueError.

  This gets the snoopdefault config value.  Since we're not
  specifying a session, it'll get the global one::

     from lyntin.exported import get_config

     snoopdefault = get_config("snoopdefault", defaultvalue=0)


  This gets the ignoreactions setting for the session named "a"::

     from lyntin.exported import get_config, get_session

     ia = get_config("ignoreactions", get_session("a"), defaultvalue=0)


  @param name: the name of the item to retrieve the value of
  @type  name: string

  @param ses: the session (or None if this is not session-scoped)
  @type  ses: Session
   
  @param defaultvalue: the value to return if there is no config
      item of that name.  if you don't specify this, then we'll
      raise a ValueError.
  @type  defaultvalue: varies
  """
  return myengine.getConfigManager().get(name, ses, defaultvalue)

def add_config(name, configitem, ses=None):
  """
  Adds a new configuration item.  Configuration items allow you to
  present the user with options that they can change which control
  the behavior of your module.  Examples of this abound in Lyntin.

  Here we create a boolean config item to control whether we're
  ignoring actions or not for the session named "a"::

    from lyntin import config
    from lyntin.exported import add_config

    tc = config.BoolConfig("ignoreactions", 0, 1, "Allows you to turn off action handling")
    add_config("ignoreactions", tc, get_session("a"))
   

  @param name: the name of the item
  @type  name: string

  @param configitem: the configuration item to add
  @type  configitem: ConfigBase

  @param ses: if this item is session based, then this is the session
      to associate the item with
  @type  ses: Session

  @raises ValueError: if there is already an item with that name for
      that session
  """
  myengine.getConfigManager().add(name, configitem, ses)

def remove_config(name, ses=None):
  """
  Allows you to remove a configuration item from the system.

  @param name: the name of the item to remove
  @type  name: string

  @param ses: the session from which to remove the item (None if
      it's a general Lyntin item)
  @type  ses: Session

  @raises ValueError: if the item does not exist
  """
  myengine.getConfigManager().remove(name, ses)

def add_help(fqn, helptext):
  """
  Adds a help topic to the structure.  See the helpmanager documentation
  for more details as to what the helptext should look like.

  Note: If you're building commands, the add_command function allows you
  to pass in help text for the command.  If you don't pass in help text
  and the command function has a doc_string, then we'll try to 
  extract the help text from the doc_string.

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

def get_version():
  """
  Returns Lyntin's version number as a tuple.  For example, if
  this were Lyntin version 4.0, the tuple would be (4, 0, 0).
  If this were Lyntin version 55.3.2 the tuple would be
  (55, 3, 2).

  @return: the version number of this installation of Lyntin
  @rtype: tuple of (int, int, int)
  """
  import lyntin.__init__
  return lyntin.__init__.__version_tuple__

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
  return myengine.getSession(name)

def get_active_sessions():
  """
  Returns a list of the active sessions including the common one.

  @return: the list of active sessions
  @rtype: list of session.Session's
  """
  return myengine._sessions.values()

def get_current_session():
  """
  Returns the current session.

  @return: the current session
  @rtype: session.Session
  """
  return myengine._current_session

def set_current_session(ses):
  """
  Changes the current session to another session.

  @param ses: the session instance to set the current session to
  @type  ses: session.Session
  """
  myengine.set_current_session(ses)
    
def get_num_errors():
  """
  Returns the total number of errors Lyntin has had thus far.

  @return: the number of unhandled errors Lyntin has encountered so far
  @rtype: int
  """
  return myengine._errorcount
 
def set_num_errors(num):
  """
  Sets the number of errors Lyntin has had thus far.  Do be careful
  when setting this because Lyntin keeps track of errors for the 
  purposes of shutting down the client in case we get into a runaway
  exception loop.

  @param num: the number of errors to set
  @type  num: int
  """
  myengine._errorcount = num

def write_ui(text):
  """
  Calls engine.myengine.writeUI which writes a message to the ui.
  If there is no engine instance available, it prints it to sysout.

  @param text: the message to write to the ui
  @type  text: string or ui.Message
  """
  if myengine:
    myengine.writeUI(text)
  else:
    print text

def write_message(text, ses=None, **hints):
  """
  Calls engine.myengine.writeMessage which writes LTDATA message.
  If there is no engine instance available, it prints it to sysout.

  @param text: the message to send
  @type  text: string

  @param ses: the session instance the error data is associated with
  @type  ses: session.Session
  """
  text = str(text)
  if myengine:
    myengine.writeUI(message.Message(text + "\n", message.LTDATA, ses, **hints))
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
  if myengine:
    myengine.writeUI(message.Message(text + "\n", message.ERROR, ses))
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
  if myengine:
    myengine.writeUI(message.Message(text + "\n", message.USERDATA, ses))
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
  if myengine:
    myengine.writeUI(message.Message(text, message.MUDDATA, ses))
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

def tally_error():
  """
  This adds one to the current error count and checks to see
  if we're over our limit.  If we are, it enqueues a shutdown
  event which will shutdown Lyntin.
  """
  myengine.tallyError()

def get_hook(hookname):
  """
  If the hook exists, returns the hook.  Otherwise it creates
  a new hook and returns that.

  @param hookname: the name of the hook to retrieve
  @type  hookname: string

  @returns: the Hook by the name of hookname
  @rtype: Hook
  """
  return myengine.getHook(hookname)

def hook_register(hookname, func, place=constants.LAST):
  """
  Registers a function with a hook.

  @param hookname: the name of the hook
  @type  hookname: string

  @param func: the function to register with the hook
  @type  func: function

  @param place: the function will get this place in the call
      order.  functions with the same place specified will get
      arbitrary ordering.  defaults to constants.LAST.
  @type  place: int
  """
  myengine.hookRegister(hookname, func, place)

def hook_unregister(hookname, func):
  """
  If the hook exists, unregisters the func from the hook.

  @param hookname: the name of the hook
  @type  hookname: string

  @param func: the function to remove from the hook
  @type  func: function
  """
  if myengine._hooks.has_key(hookname):
    myengine._hooks[hookname].remove(func)

def hook_spam(hookname, argmap={}, mappingfunc=lambda x,y:x, 
      emptyfunc=lambda x:x, donefunc=lambda x:x):
  """
  Sends out input to all the registrants of a hook.

  @param hookname: the name of the hook to spam
  @type  hookname: string

  @param argmap: the map of arguments that gets passed to
      each function in the hook.  the actual arguments differs
      from hook to hook.
  @type  argmap: dict of arguments

  @param mappingfunc: function whose output will be passed to the next
      function in the hook.  Must take two arguments: the previous 
      arglist and the return from the previous function.
  @type  mappingfunc: function

  @param emptyfunc: Function to be called with arglist if there are no
      objects registered with this hook.  Must take 1 argument, the arglist
      tuple, and return what spamhook should return.
  @type  emptyfunc: function

  @param donefunc: Function to be called when spamming finishes normally.
      Should take 1 argument and return what spamhook should return.
  @type  donefunc: function
        
  @return: argmap
  @rtype:  map of output arguments
  """
  hooklist = get_hook(hookname).getList()
  try:
    if hooklist:
      for mem in hooklist:
        output = mem(argmap)
        argmap = mappingfunc(argmap, output)
    else:
      argmap = emptyfunc(argmap)
  except StopSpammingException, e:
    return None
  except DoneSpammingException, d:
    return d.output

  return donefunc(argmap)

def filter_mapper_hook_spam(hookname, argmap={}, emptyfunc=lambda x:x, 
    donefunc=lambda x:x):
  """
  This is a slightly optimized filter_mapper hook because it's used so
  often in the system.  It incorproates the filter_mapper, but skips
  any exception handling.

  Arguments correspond to hook_spam.
  """
  hooklist = get_hook(hookname).getList()
  if hooklist:
    for mem in hooklist:
      output = mem(argmap)
      if output == None:
        return None

      argmap["dataadj"] = output
  else:
    argmap = emptyfunc(argmap)

  return donefunc(argmap)

def filter_mapper(x, y):
  """
  This is the mapping function to use for filter-style hooks.  
  Spamhook should be called as:

    1. spamargs = {"session": ses, "data": data, "dataadj": data... }
    2. spamargs = exported.hook_spam(... spamargs ...)
    3. output = spamargs["dataadj"]

  Each filter function will get a map with at least the following keys when 
  it is called:

    - session - the session
    - data - the original data
    - dataadj - the adjusted data
  """
  if y != None:
    x["dataadj"] = y
    return x
  else:
    raise StopSpammingException

def query_mapper(x, y):
  """
  This is the mapping function to be used for query-style hooks.
  Spamhook should be called as:

    1. output = hook.spamhook( arguments )

  Each hook function will be called with the arguments until one function
  returns non-None.  That non-None value will be returned from spamhook
  """
  if y != None:
    raise DoneSpammingException(y)
  else:
    return x

def query_done(x):
  """
  This is the done hook function to go with the query mapper for proper 
  behaviour.
  """
  return None


def get_write_data(ses, quiet=0):
  """
  Calls the write_hook and retrieves data from all the functions that
  have registered with the hook.  It passes in the session involved,
  and also the "quiet" argument.

  For example, the alias module might have one alias for session a.  It
  would return::

    [ "alias {vv %1} {evoke %1}" ]

  If quiet was 1, then it would return::

    [ "alias {vv %1} {evoke %1} quiet={true}" ]

  Then this method would take all those lists of strings and generate
  one list of all the strings and return it.

  Exceptions kicked up by poorly written plugins (and bad Lyntin code)
  will get percolated upwards.  i.e. if exceptions are raised, then you
  won't get any return data.

  @param ses: the session to save the data for
  @type  ses: Session

  @param quiet: whether or not to be quiet--this is for when the data
      that is written is eventually read in.  0 if not quiet, 1 if quiet.
  @type  quiet: boolean

  @returns: data as a list of strings
  @rtype: list of strings
  """
  data = []
  def write_mapper(x, y):
    """
    Takes the data from x and sticks it into y so that we continue
    it all the way through.
    """
    data.append(y)
    return x

  hook_spam("write_hook", {"session": ses, "quiet": quiet}, mappingfunc=write_mapper)

  listing = []
  if data:
    for mem in data:
      listing = listing + mem

  return listing


# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
