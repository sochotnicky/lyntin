#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: variable.py,v 1.3 2003/06/08 16:14:30 willhelm Exp $
#######################################################################
"""
This module defines the VariableManager which handles variables.
It also defines global variables like $TIMESTAMP.
"""
import string, time
from lyntin import manager, utils, __init__, engine, exported
from lyntin.modules import modutils

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

class VariableData:
  def __init__(self):
    self._variables = {}

  def addVariable(self, var, expansion):
    """
    Adds a variable to the dict.

    @param var: the variable name
    @type  var: string

    @param expansion: the variable value which can be anything that
        has __str__ implemented
    @type  expansion: string
    """
    self._variables[var] = expansion

  def clear(self):
    """
    Removes all the variables.
    """
    listing = self._variables.keys()
    for mem in listing:
      del self._variables[mem]

  def removeVariables(self, text):
    """
    Removes variables from the list.

    Returns a list of tuples of variable var/expansion that
    were removed.

    @param text: variables will be removed that match the text
    @type  text: string

    @returns: list of (name, value) tuples of removed variables
    @rtype: list of (string, string)
    """
    badvariables = utils.expand_text(text, self._variables.keys())

    ret = []
    for mem in badvariables:
      ret.append((mem, self._variables[mem]))
      del self._variables[mem]

    return ret

  def expand(self, text):
    """
    Expands variables in the text.

    @param text: the text to expand variables in
    @type  text:

    @returns: the text with variables expanded
    @rtype: string
    """
    return utils.denest_vars(utils.expand_vars(text, self._variables), self._variables)

  def expand_command(self, text):
    """
    Expands variables in the text, does not denest yet since the command
    could get recursed on and over-expand variables.

    @param text: the text to expand variables in
    @type  text: string

    @returns: the text with variables expanded
    @rtype: string
    """
    return utils.expand_vars(text, self._variables)

  def getVariables(self):
    """
    Returns the keys of the variables dict.

    @returns: a list of all the variable names being managed
    @rtype: list of strings
    """
    listing = self._variables.keys()
    listing.sort()
    return listing

  def getVariable(self, name, default=None):
    """
    Returns the value for a given variable.

    @param name: the name of the variable to retrieve
    @type  name: string

    @param default: the default value to return if the variable doesn't
        exist
    @type  default: any

    @returns: the variable value or the default if the variable doesn't
        exist
    @rtype: string (or default)
    """
    if self._variables.has_key(name):
      return self._variables[name]
    else:
      return default

  def defaultResolver(self, command):
    """
    Returns a defaultresolver that will look up potential default values in 
    this session's variables.

    Lookup will be first::

       "default.%s.%s" % (command, argument,)

    then::

       "default.%s" % (argument,)

    to allow for overriding all arguments of a given name, or only arguments 
    for specific commands.

    @param command: the command to look up arguments for
    @type  command: string

    @returns: a function object that will do the desired lookup
    @rtype: function object
    """
    def resolver(argument, vdata=self, command=command):
      output = vdata.getVariable( "default.%s.%s" % (command, argument,))
      if output == None:
        output = vdata.getVariable( "default.%s" % (argument,))
      return output

    return resolver

  def getStatus(self):
    """
    Returns a one-liner as to the status of this data class.

    @returns: the one-liner status as to what this manager is managing
    @rtype: string
    """
    return "%d variable(s)." % len(self._variables)

  def getInfo(self, text=""):
    """
    Returns information about the variables in here.

    This is used by #variable to tell all the variables involved
    as well as #write which takes this information and dumps
    it to the file.

    @param text: variables matching this string will be returned
    @type  text: string

    @returns: one big string with all the information in it
    @rtype: string
    """
    if len(self._variables.keys()) == 0:
      return ''

    if text=='':
      listing = self._variables.keys()
    else:
      listing = utils.expand_text(text, self._variables.keys())

    listing = ["%svariable {%s} {%s}" % (__init__.commandchar, mem, self._variables[mem]) for mem in listing]

    return string.join(listing, "\n")


class VariableManager(manager.Manager):
  def __init__(self):
    self._variables = {}

    # this handles builtins even when we don't have a VariableData
    # instance for that session
    self._global = VariableData()

    # add built-in variables
    self._global.addVariable("TIMESTAMP", TimeStampBuiltin())
    self._global.addVariable("LOGTIMESTAMP", LogTimeStampBuiltin())
    self._global.addVariable("DATADIR", __init__.options["datadir"])

    import os
    if os.environ.has_key("HOME"):
      self._global.addVariable("HOME", os.environ["HOME"])

  def addVariable(self, ses, var, expansion):
    if not self._variables.has_key(ses):
      self._variables[ses] = VariableData()

    # check to see if it's a global variable
    if var.startswith("_"):
      vdata = self._global
    else:
      vdata = self._variables[ses]

    # save the old value (if any)
    oldvalue = vdata.getVariable(var)

    # set the variable
    vdata.addVariable(var, expansion)

    # spam the hook
    self._varChangeHook(ses, var, oldvalue, expansion)

  def clear(self, ses):
    if self._variables.has_key(ses):
      self._variables[ses].clear()

  def _varChangeHook(self, ses, var, old, new):
    exported.hook_spam("variable_change_hook", 
          {"session": ses, "variable": var, "oldvalue": old, "newvalue": new})

  def removeVariables(self, ses, text):
    vars = []
    if self._variables.has_key(ses):
      vars = self._variables[ses].removeVariables(text)
      for mem in vars:
        self._varChangeHook(ses, mem[0], mem[1], None)
    return vars

  def getVariables(self, ses):
    if self._variables.has_key(ses):
      return self._variables[ses].getVariables()
    return []

  def getVariable(self, ses, name, default=None):
    if self._variables.has_key(ses):
      return self._variables[ses].getVariable(name, default)
    return default

  def defaultResolver(self, tuple):
    ses, command = tuple
    if self._variables.has_key(ses):
      return self._variables[ses].defaultResolver(command)
    return None

  def expand(self, ses, text):
    text = self._global.expand(text)
    if self._variables.has_key(ses):
      return self._variables[ses].expand(text)
    return text

  def expand_command(self, ses, text):
    text = self._global.expand_command(text)
    if self._variables.has_key(ses):
      return self._variables[ses].expand_command(text)
    return text

  def getInfo(self, ses, text=""):
    if self._variables.has_key(ses):
      return self._variables[ses].getInfo(text)
    return ""

  def getStatus(self, ses):
    if self._variables.has_key(ses):
      return self._variables[ses].getStatus()
    return "0 variable(s)."

  def addSession(self, newsession, basesession=None):
    if basesession:
      if self._variables.has_key(basesession):
        varhash = self._variables[basesession]._variables
        for mem in varhash.keys():
          self.addVariable(newsession, mem, varhash[mem])

  def removeSession(self, ses):
    if self._variables.has_key(ses):
      del self._variables[ses]

  def persist(self, args):
    """
    write_hook function for persisting the state of our session.
    """
    ses = args["session"]
    file = args["file"]
    quiet = args["quiet"]

    data = self.getInfo(ses)
    if data:
      if quiet == 1:
        data = data.replace("\n", " quiet={true}\n")
        file.write(data + " quiet={true}\n")
      else:
        file.write(data + "\n")
      file.flush()

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

    return utils.denest_vars(text, self._variables)

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

  There are also system variables $HOME, $TIMESTAMP, and $DATADIR 
  (must be upper-cased) and global variables.  To set a global 
  variable which can be used in all sessions, it must be preceded
  by a _.

  examples:
    #variable {_fun} {happy fun ball}
    #showme $_fun
    #showme $TIMESTAMP

  category: commands
  """
  var = args["var"]
  expansion = args["expansion"]
  quiet = args["quiet"]

  vm = exported.get_manager("variable")

  if not var and not expansion:
    data = vm.getInfo(ses)
    if data == '':
      data = "variable: no variables defined."

    exported.write_message("variables:\n" + data, ses)
    return

  if not expansion:
    data = vm.getInfo(ses, var)
    if data == '':
      data = "variable: no variables defined."

    exported.write_message("variables:\n" + data, ses)
    return 

  try:
    vm.addVariable(ses, var, expansion)
    if not quiet:
      exported.write_message("variable: {%s}={%s} added." % (var, expansion), ses)

  except Exception, e:
    exported.write_error("variable: cannot be set. %s", e, ses)

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
