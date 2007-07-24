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
# $Id: variable.py,v 1.14 2007/07/24 00:39:03 willhelm Exp $
#########################################################################

"""
This module defines the VariableManager which handles variables.
It also defines global variables like $TIMESTAMP.

X{variable_change_hook}::

   The variable_change_hook allows other modules to be notified when
   variable values change and handle those changes accordingly.  For
   instance, the action module would recompile its regular expression
   triggers based on the new values of the variables.

   Arg mapping: { "session": Session, "variable": string, "oldvalue": string,
                  "newvalue": string }

   session - the session this variable belongs to

   variable - the name of the variable in question

   oldvalue - the old value of the variable

   newvalue - the new value of the variable
"""
import time
from lyntin import manager, utils, config, engine, exported, session
from lyntin.modules import modutils

class DatadirBuiltin:
  """
  Allows us to do dynamic DATADIRs as a global variable.
  """
  def __init__(self): pass
  def __str__(self): return config.options["datadir"]

class TimeStampBuiltin:
  """
  Allows us to do dynamic TIMESTAMPs as a global variable.
  """
  def __init__(self): pass
  def __str__(self): return time.asctime()

class LogTimeStampBuiltin:
  """
  Allows us to do dynamic TIMESTAMPs as a global variable in the
  form yyyymmddhhmmss.  Good for logfiles.
  """
  def __init__(self): pass
  def __str__(self): return time.strftime('%Y%m%d%H%M%S')

class VariableManager(manager.Manager):
  def __init__(self):
    session.Session.global_vars["TIMESTAMP"] = TimeStampBuiltin()
    session.Session.global_vars["LOGTIMESTAMP"] = LogTimeStampBuiltin()
    session.Session.global_vars["DATADIR"] = DatadirBuiltin()

    import os
    if os.environ.has_key("HOME"):
      session.Session.global_vars["HOME"] = os.environ["HOME"]

  def clear(self, ses):
    ses._vars = {}

  def addVariable(self, ses, var, expansion):
    ses.setVariable(var, expansion)

  def removeVariables(self, ses, text):
    d = dict(ses._vars)
    d.update(session.Session.global_vars)
    badvariables = utils.expand_text(text, d.keys())
    ret = []
    for mem in badvariables:
      ret.append( (mem, d[mem]) )
      ses.removeVariable(mem)

    return ret

  def defaultResolver(self, args):
    """
    Returns a defaultresolver that will look up potential default values in 
    this session's variables.

    Lookup will be first::

       "default.%s.%s" % (command, argument,)

    then::

       "default.%s" % (argument,)

    to allow for overriding all arguments of a given name, or only arguments 
    for specific commands.

    @returns: a function object that will do the desired lookup
    @rtype: function object
    """
    ses = args["session"]
    command = args["commandname"]

    def resolver(argument, ses=ses, command=command):
      output = ses.getVariable( "default.%s.%s" % (command, argument,))
      if output == None:
        output = ses.getVariable( "default.%s" % (argument,))
      return output
    return resolver

  def expand(self, ses, text):
    t = utils.expand_vars(text, session.Session.global_vars)
    t = utils.expand_vars(t, ses._vars)
    return utils.denest_vars(t, {})

  def expand_command(self, ses, text):
    t = utils.expand_vars(text, session.Session.global_vars)
    return utils.expand_vars(t, ses._vars)

  def getInfo(self, ses, text=""):
    data = ses._vars.keys()
    if text:
      data = utils.expand_text(text, data)
    data = ["variable {%s} {%s}" % (m, ses._vars[m]) for m in data]
    return data

  def getItems(self):
    return [ "variable" ]

  def getParameters(self, item):
    if item != "variable":
      raise ValueError("%s is not a valid item for this manager." % item)
    return [ ("var", "The variable"), 
             ("expansion", "The thing the variable expands into." ) ]

  def getInfoMappings(self, item, ses):
    if item != "variable":
      raise ValueError("%s is not a valid item for this manager." % item)
    l = []
    for mem in self._vars.keys():
      l.append( {"var": mem, "expansion": ses._vars[mem]} )

    return l
      
  def getStatus(self, ses):
    return "%d variable(s)." % len(ses._vars)

  def addSession(self, newsession, basesession=None):
    self.clear(newsession)

    if basesession:
      for mem in basesession._vars.keys():
        newsession._vars[mem] = basesession._vars[mem]

  def persist(self, args):
    """
    write_hook function for persisting the state of our session.
    """
    ses = args["session"]
    quiet = args["quiet"]

    data = self.getInfo(ses)
    if quiet == 1:
      data = [m + " quiet={true}" for m in data]

    return data

  def denestVars(self, args):
    """
    Handles denesting variables for Lyntin evaluation mode.
    """
    ses = args["session"]
    internal = args["internal"]
    verbatim = args["verbatim"]
    text = args["dataadj"]

    if verbatim == 1:
      return text

    return utils.denest_vars(text, ses._vars)

  def userfilter(self, args):
    """
    user_filter_hook for handling incoming user data.
    """
    ses = args["session"]
    internal = args["internal"]
    verbatim = args["verbatim"]
    text = args["dataadj"]

    if verbatim == 1:
      return text

    varexpansion = self.expand_command(ses, text)

    if varexpansion == text:
      return text
    else:
      exported.lyntin_command(varexpansion, 1, ses)
      return None


commands_dict = {}

def variable_cmd(ses, args, input):
  """
  Creates a variable for that session of said name with said value.
  Variables can then pretty much be used anywhere.

  examples:
    #variable {hps} {100}
    #action {HP: %0/%1 } {#variable {hps} {%0}}

  Variables can later be accessed via the variable character
  (which defaults to $) and the variable name.  In the case of the
  above, the variable name would be $hps.  

  We also handle braced closures for denoting variables like ${hps}.  
  If you have a variable hps and a variable hpset, you can explicitly
  specify which one using { }.

  There are also system variables $HOME, $TIMESTAMP, $LOGTIMESTAMP,
  and $DATADIR (must be upper-cased) and global variables.  To set 
  a global variable which can be used in all sessions, it must 
  be preceded by a _.

  examples:
    #variable {_fun} {happy fun ball}
    #showme $_fun
    #showme $TIMESTAMP
    #showme ${TIMESTAMP}

  category: commands
  """
  var = args["var"]
  expansion = args["expansion"]
  quiet = args["quiet"]

  vm = exported.get_manager("variable")

  if not expansion:
    data = vm.getInfo(ses, var)
    if not data:
      data = ["variable: no variables defined."]

    exported.write_message("variables:\n" + "\n".join(data), ses)
    return 

  try:
    vm.addVariable(ses, var, expansion)
    if not quiet:
      exported.write_message("variable: {%s}={%s} added." % (var, expansion), ses)

  except Exception, e:
    exported.write_error("variable: cannot be set. %s" % e, ses)

commands_dict["variable"] = (variable_cmd, "var= expansion= quiet:boolean=false")


def unvariable_cmd(ses, args, input):
  """
  Allows you to remove variables.

  category: commands
  """
  func = exported.get_manager("variable").removeVariables
  modutils.unsomething_helper(args, func, ses, "variable", "variables")

commands_dict["unvariable"] = (unvariable_cmd, "str= quiet:boolean=false")

vm = None


def load():
  """ Initializes the module by binding all the commands."""
  global vm
  modutils.load_commands(commands_dict)
  vm = VariableManager()
  exported.add_manager("variable", vm)

  exported.hook_register("user_filter_hook", vm.userfilter, 10)
  exported.hook_register("user_filter_hook", vm.denestVars, 95)
  exported.hook_register("default_resolver_hook", vm.defaultResolver)
  exported.hook_register("write_hook", vm.persist)

def unload():
  """ Unloads the module by calling any unload/unbind functions."""
  global vm
  modutils.unload_commands(commands_dict.keys())
  exported.remove_manager("variable")

  exported.hook_unregister("user_filter_hook", vm.userfilter)
  exported.hook_unregister("user_filter_hook", vm.denestVars)
  exported.hook_unregister("default_resolver_hook", vm.defaultResolver)
  exported.hook_unregister("write_hook", vm.persist)

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
