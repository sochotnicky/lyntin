#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 1996 - 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: hooks.py,v 1.1 2003/05/05 05:54:19 willhelm Exp $
##################################################################
"""
The engine is augmented by a series of X{hooks} which allow modules to
execute functions without having to change Lyntin's internals.  
Examples of this would be the "startup_hook" and "shutdown_hook".  
Any functions that hook into these hooks will be executed upon 
startup or shutdown of Lyntin.  Lyntin also uses these hooks to 
implement its functionality.

For example, the Tk ui uses the "startup_hook" to register with
the "to_user_hook", add the tkui help topic, and start the ui
user listener thread.

Hooks and the Hook class are defined in the "hooks" module as is
a whole lot of documentation on which hooks exist, and what is
passed to them.  Registering, unregistering, and retrieving Hooks
should be done through the exported module.

@var  FIRST: Used for hook registration priority.
@type FIRST: int

@var  LAST: Used for hook registration priority.
@type LAST: int

@var startup_hook: Allows you to initialize things when Lyntin is
    starting up.  Arg tuple: ()

@var shutdown_hook: Allows you to finalize things when Lyntin is 
    shutting down.  Arg tuple: (quiet:boolean)

@var mudecho_hook: When the mud sends an echo on/off, we spam it to
    this hook.  Arg tuple: (echostate:boolean)

@var bell_hook: When the mud sends a ^G, we spam this hook.  Arg tuple:
    (session:Session)

@var prompt_hook: When the mud sends a IAC+GA/IAC+TELOPT_EOR indicating
    a prompt or they send a string (needs to be set via the 
    buildPromptRegex method of the SocketCommunicator), we spam this hook.
    Arg tuple: (session:Session, text:string)

@var variable_change_hook: When the user changes the value of a variable
    (or it gets changed through some other means), we spam this hook.
    Arg tuple: (session:Session, varname:string, oldvalue:string, 
    newvalue:string)

@var death_hook: When the session dies (i.e. it gets #zap'd), we spam this
    hook.  Arg tuple: (session:Session)

@var connect_hook: When the session gets connected to a mud, we spam this
    hook.  Arg tuple: (session:Session, hostname:string, port:int)

@var disconnect_hook: When the session gets disconnected from a mud, we
    spam this hook.  Arg tuple: (session:Session, hostname:string, port:int)

@var from_user_hook: Everything the user types gets sent through this hook
    prior to getting evaluated.  Arg tuple: (data:string)

@var from_mud_hook: Everything the mud sends gets passed on this hook
    prior to getting evaluated.  Arg tuple: (session:Session, data:string)

@var to_mud_hook: This differs from the from_user_hook in that this is
    everything we send on the socket to the mud.  
    Arg tuple: (session:Session, data:string, tag:varies)

@var to_user_hook: The ui listens on this hook to display things to the
    user.  Data on this hook can come from a variety of sources such
    as Lyntin error messages, Lyntin regular messages, mud data, user
    input...  Arg tuple: (data:string|ui.ui.Message)

@var timer_hook: The timer hook runs every second.  The scheduler uses this
    to know when to wake up and deal with things.  Arg tuple: (ticknumber:int)

@var write_hook: This hook runs whenever someone types "#write <filename>".
    Arg tuple: (session:Session, file:File, quiet:boolean)

@var error_occurred_hook: When an error is kicked up via the event loop.
    The arg tuple is empty--you should check sys.exc_traceback if you're
    interested in the unhandled exception.

@var too_many_errors_hook: When the user_custom variable too_many_errors
    is exceeded.

@var mud_filter_hook: Whenever data comes from the user, it gets split into
    lines and passed through the mud_filter_hook.  Functions should return
    the adjusted text which becomes the filteredtext input to the next 
    function.
    Arg tuple: (session:Session, originaltext:string, filteredtext:string)

@var user_filter_hook: Whenever data comes from the user, it gets passed
    through all the filter functions.  Functions that register with this
    hook should return the adjusted text which gets passed in as the
    adjustedtext input for the next function.
    Arg tuple: (session:session, internal:boolean, verbatim:boolean, 
    originaltext:string, adjustedtext:string)

@var default_resolver_hook: When the command manager needs to get a function
    to produce default arguments for a given command on a given session it
    will call this hook.  Arg tuple: (session:Session, commandname:string)
"""
import session, manager

FIRST = 0
LAST = 99

class StopSpammingException(Exception):
  pass

class DoneSpammingException(Exception):
  def __init__(self, output):
    self.output = output

class HookManager(manager.Manager):
  """
  Manages creating hooks on demand as well as retrieving
  hooks and such.
  """
  def __init__(self):
    self._hook_map = {}

  def getHookList(self):
    """
    Returns a list of hooks that are currently in existence.

    @returns: the list of hooks in existence
    @rtype: list of strings
    """
    return self._hook_map.keys()

  def getHookStatus(self):
    """
    Returns information about the hooks that have things registered
    to them for #diagnostics output.

    @returns: the diagnostic string
    @rtype: string
    """
    output = []
    for mem in self._hook_map.keys():
      count = self._hook_map[mem].count()
      if count > 0:
        output.append("   " + mem + ": " + str(count))

    return output
    
  def register(self, hookname, func, place=LAST):
    """
    Registers a function with a given hook.  If the hook doesn't
    exist, then it instantiates the hook.

    @param hookname: the name of the hook
    @type  hookname: string

    @param func: the function to call when that hook is spammed
    @type  func: function

    @param place: the function will get this place in the call
        order.  functions with the same place specified will get
        arbitrary ordering.  defaults to LAST.
    @type  place: int
    """
    if not self._hook_map.has_key(hookname):
      self._hook_map[hookname] = Hook()

    self._hook_map[hookname].register(func, place)

  def unregister(self, hookname, func):
    """
    If the hook exists, unregisters the func from the hook.

    @param hookname: the name of the hook
    @type  hookname: string

    @param func: the function to remove from the hook
    @type  func: function
    """
    if self._hook_map.has_key(hookname):
      self._hook_map[hookname].unregister(func)

  def getHook(self, hookname):
    """
    Retrieves a hook by the name of hookname.  If the hook does
    not exist, then it creates the hook.

    @param hookname: the name of the hook
    @type  hookname: string

    @returns: the existing or newly created Hook instance
    @rtype: Hook
    """
    if self._hook_map.has_key(hookname):
      return self._hook_map[hookname]

    self._hook_map[hookname] = Hook()
    return self._hook_map[hookname]

  def addHook(self, hookname, newhook):
    """
    Adds a pre-existing hook to the manager so we can
    manage it.

    @param hookname: the name for the hook
    @type  hookname: string

    @param newhook: the hook to add
    @type  newhook: Hook
    """
    if self._hook_map.has_key(hookname):
      raise ValueError, "Already have a hook by that name."
    self._hook_map[hookname] = newhook


def QueryHook():
  return Hook(mapper=query_mapper, done=query_done)

def FilterHook():
  return Hook(mapper=filter_mapper)

class Hook:
  """
  Represents a (possibly empty) sequence of user-defined
  functions.  Provides users with the opportunity of reacting
  to events internal to Lyntin.  All functions take a single
  argument which is a tuple.

  Read through the hooks.py file for more information on the 
  hooks that come with Lyntin as well as which arguments they 
  take in the arg tuple.
  """
  def __init__(self, mapper=lambda x,y:x, empty=lambda x:x, done=lambda x:x):
    """
    Initializes.

    @param mapper: function whose output will be passed to the next
        function in the hook.  Must take two arguments: the previous 
        arglist and the return from the previous function.
    @type  mapper: function

    @param empty: function to be called when there are no functions in the hook
    @type empty: function

    @param done: function to be called when spamming finished normally
    @type done: function
    """
    # this is the master priority list
    self._functionlist = {}

    # this gets recomputed everytime someone registers or
    # unregisters a hook
    self._orderedlist = []

    self._mapper = mapper

    self._empty = empty

    self._done = done

  def setFilterMapper(self, newmapper):
    """
    Sets the filter mapper to a new mapper.

    @param newmapper: the function whose output will be passed
        to the next function in the hook.  Takes two arguments:
        the previous arglist and the return from the previous 
        function.
    @type  newmapper: function
    """
    self._mapper = newmapper

  def createOrderedList(self):
    """
    Goes through the functionlist and generates the
    orderedlist.  This helps save some cycles every time
    we spam the hook.
    """
    priorities = self._functionlist.keys();
    priorities.sort()

    self._orderedlist = []

    for priority in priorities:
      for mem in self._functionlist[priority]:
        self._orderedlist.append(mem)
    
    
  def spamhook(self, arglist=(), mappingFunction=None, emptyFunction=None, doneFunction=None):
    """
    Sends out input to all the registrants of a hook.

    @param arglist: the list of arguments that gets passed to
        each function in the hook.  the actual arguments differs
        from hook to hook.
    @type  arglist: tuple of arguments

    @param mappingFunction: function whose output will be passed to the next
        function in the hook.  Must take two arguments: the previous 
        arglist and the return from the previous function.
    @type  mappingFunction: function

    @param emptyFunction: Function to be called with arglist if there are no
        objects registered with this hook.  Must take 1 argument, the arglist
        tuple, and return what spamhook should return.
    @type  emptyFunction: function

    @param doneFunction: Functino to be called when spamming finishes normally.
        Should take 1 argument and return what spamhook should return.
    @type  doneFunction: function
        

    @return: arglist
    @rtype:  tuple of arguments
    """
    mappingFunction = mappingFunction or self._mapper
    emptyFunction = emptyFunction or self._empty
    doneFunction = doneFunction or self._done

    try:
      if self._orderedlist:
        for mem in self._orderedlist:
          output = mem(arglist)
          arglist = mappingFunction(arglist, output)
      else:
        arglist = emptyFunction(arglist)
    except StopSpammingException, e:
      return None
    except DoneSpammingException, d:
      return d.output

    return doneFunction(arglist)

  def unregister(self, func):
    """
    Tries to remove a registrant from a hook--does pretty well.

    @param func: the function to unregister
    @type  func: function
    """
    for priority in self._functionlist.keys():
      if func in self._functionlist[priority]:
        self._functionlist[priority].remove(func)
        if len(self._functionlist[priority]) == 0:
          del self._functionlist[priority]

    self.createOrderedList()
        

  def register(self, func, place=LAST):
    """
    Registers a function with a hook.

    hook should be one of the hook constants.  func 
    should be a callable function.  place is optional--it allows 
    you to put yourself earlier in the hook lineup.

    @param func: the function to call when the hook is spammed
    @type  func: function

    @param place: the function will get this place in the call
        order.  functions with the same place specified will get
        arbitrary ordering.  defaults to LAST.
    @type  place: int
    """
    if not callable(func):
      exported.write_error("Function %s not callable." % repr(func))
      return

    if self._functionlist.has_key(place):
      self._functionlist[place].append(func)
    else:
      self._functionlist[place] = [func]

    self.createOrderedList()

  def clear(self):
    """
    Clears the functionlist.
    """
    self._functionlist = {}
    self._orderedlist = []

  def count(self):
    """
    Returns how many functions are registered with this hook.

    @returns: the number of functions registered
    @rtype: int
    """
    return len(self._functionlist)


myhookmanager = None

def get_hook_manager():
  """
  HookManager is a singleton and this is the function that should
  be used to retrieve the single instance.

  @returns: HookManager instance
  @rtype: HookManager
  """
  global myhookmanager

  if myhookmanager == None:
    myhookmanager = HookManager()

  return myhookmanager


##################################################################
# Hooks corresponding to events within lyntin
##################################################################

# When lyntin starts up.  This is a good time to initialize things
# like ui's and other things that need a critical mass of things
# to have been imported and instantiated before doing initialization.
#
# arg tuple: ()
startup_hook = get_hook_manager().getHook("startup_hook")

# When lyntin shuts down.
# 
# arg tuple: (boolean)
#  - 0 if we don't have to be quiet, 1 if we should be quiet
shutdown_hook = get_hook_manager().getHook("shutdown_hook")

# When the mud sends an echo on or an echo off.
# 
# arg tuple: (boolean)
#  - new echo state: 1 if on, 0 if off
mudecho_hook = get_hook_manager().getHook("mudecho_hook")

# When the mud sends a ^G character, we kick off a SpamEvent
# which spams the bell_hook.
#
# arg tuple: (Session)
#  - the session the bell was kicked off in
bell_hook = get_hook_manager().getHook("bell_hook")

# Some muds send a GA/TELOPT_EOR character indicating a prompt.  This
# hook allows you to react to those prompts.
#
# arg tuple: (Session, string)
#  - the session the prompt came from
#  - the prompt text
prompt_hook = get_hook_manager().getHook("prompt_hook")

# This hook will get called every time a variable is changed.
#
# arg tuple: (session, string, string, string)
#  - session instance
#  - the variable name
#  - the old value
#  - the new value
variable_change_hook = get_hook_manager().getHook("variable_change_hook")

# When a session dies or ends.
#
# arg tuple: (session)
#  - the session that died
death_hook = get_hook_manager().getHook("death_hook")

# When a session connects to a mud.
#
# arg tuple: (session, string, int)
#  - session instance
#  - hostname
#  - port
connect_hook = get_hook_manager().getHook("connect_hook")

# When a session disconnects from a mud.
#
# arg tuple: (session, string, int)
#  - the session instance that just disconnected
#  - the hostname of where it was connected to
#  - the port at which it was connected
disconnect_hook = get_hook_manager().getHook("disconnect_hook")

# Everything the user types gets sent on the from_user_hook.
#
# arg tuple: (string)
#  - the data the user just entered
from_user_hook = get_hook_manager().getHook("from_user_hook")

# When the mud sends data, this will trigger the from_mud_hook.
# 
# If you're looking for a line by line idea of things, use the
# mud_filter_hook.
#
# arg tuple: (session, string)
#  - the session instance data is coming from
#  - the raw data we just got from the mud
from_mud_hook = get_hook_manager().getHook("from_mud_hook")

# This differs from the from_user_hook in that this is everything
# we send on the socket to the mud where the from_user_hook is everything
# the user types--much of it goes to the mud.
#
# arg tuple: (session, string, tag)
#  - the session instance we're sending this data to
#  - the string being sent
#  - the tag used in session.writeSocket (usually None)
to_mud_hook = get_hook_manager().getHook("to_mud_hook")

# The ui's listen on this hook to display stuff.  Data on this hook
# is meant for the user to see as Lyntin output or mud output.
#
# arg tuple: (string | ui.ui.Message)
#  - either a string or a ui.ui.Message instance--this is the data
to_user_hook = get_hook_manager().getHook("to_user_hook")

# The timer hook runs every second.  The tickers for the various sessions
# use this hook to figure out when to tick.
# 
# arg tuple: (int)
#  - the current tick since Lyntin started
timer_hook = get_hook_manager().getHook("timer_hook")

# The write hook runs whenever someone does "#write <filename>".
# This is primarily for session persistence.  Everything registered
# to this hook gets the file object and writes stuff to the file
# object.  Do NOT save the file object or the session object
# for later use!  They may not be there!
# 
# The third argument "quiet" is a flag (0 is no, 1 is yes) indicating 
# whether the user wants the information persisted so that when 
# it's read in with #read it's quiet as to its verbostiy.  For example,
# the AliasManager would persist non-quiet things as:
#
#   #alias {g} {get all}
#
# and quiet things as:
#
#   #alias {g} {get all} quiet={true}
# 
# arg tuple: (session, file object, boolean)
#  - the session instance
#  - the file object we're writing to
#  - whether (1) or not (0) we should be persisting things quietly
write_hook = get_hook_manager().getHook("write_hook")

# When an error is kicked up via the event loop.  The arg tuple
# is empty--you should check sys.exc_traceback if you're interested
# in what just happened.
# 
# arg tuple: ()
error_occurred_hook = get_hook_manager().getHook("error_occurred_hook")

# When the user_custom variable too_many_errors is exceeded.
#
# arg tuple: ()
too_many_errors_hook = get_hook_manager().getHook("too_many_errors_hook")

##################################################################
# Filtered hooks
##################################################################

def filter_mapper(x, y):
  """
  This is the mapping function to use for filter-style hooks.  
  Spamhook should be called as:

    1. spamtuple = hook.spamhook( (session, flags, original, original) )
    2. output = spamtuple[-1]

  Each filter function will get (session, flags, original, filteredoriginal) 
  when it is called.
  """
  if y != None:
    return x[:-1] + (y,)
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

# Whenever data comes back from the mud it will first be passed through
# all filter functions.
# 
# These should return the text that should be processed as if it came from 
# the mud.
# 
# arg tuple: (session, string, string)
#  - the session the mud data came from
#  - the original text the mud sent
#  - the filtered text (this allows people to adjust it as they go along)
# 
# Functions that register with this hook should return the adjusted text.
# For example, the SubstituteManager returns text with substitutions
# expanded.
get_hook_manager().addHook("mud_filter_hook", FilterHook())
mud_filter_hook = get_hook_manager().getHook("mud_filter_hook")

# Whenever data comes from the user it will first be passed through
# all filter functions.
# 
# These should return the text that should be sent to the mud.
# 
# arg tuple: (session, boolean, boolean, string, string)
#  - the session instance
#  - 0 or 1: whether or not the data is internal
#  - 0 or 1: whether or not we're in verbatim mode where we don't adjust
#    the user data at all (from the session)
#  - the original text the user typed
#  - the adjusted text
#
# Functions that register with this hook should return the adjusted text.
# For example, the AliasManager returns text with aliases expanded.
get_hook_manager().addHook("user_filter_hook", FilterHook())
user_filter_hook = get_hook_manager().getHook("user_filter_hook")

# When the command manager needs to get a function to produce default
# arguments for a given command on a given session it will call
# this hook.
#
# arg tuple: (session, commandname)
# output: function that can accept 1 paramter, the argument name, and will 
# return the default string value, or None if no default is present
get_hook_manager().addHook("default_resolver_hook", QueryHook())
default_resolver_hook = get_hook_manager().getHook("default_resolver_hook")


# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
