#######################################################################
# This file is part of Lyntin
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: config.py,v 1.3 2003/08/27 03:19:58 willhelm Exp $
#######################################################################
"""
This module holds the configuration manager as well as a series of
configuration type classes.
"""
import os, os.path, types
from lyntin import exported, utils, manager, constants


class ConfigBase:
  """
  A ConfigDataBase subclass encapsulates a piece of configuration.  It
  encapsulates its type functionality (data checking, et al), its name
  and its value.
  """
  def __init__(self, name, originalvalue, persist, description):
    """
    Sets the name and original value.  Override this if you need
    additional pieces of information in your ConfigDataBase
    subclass.

    @param name: the name of the config item
    @type  name: string

    @param originalvalue: the original value of the config item
    @type  originalvalue: varies

    @param persist: this config item should (1) or should not (0) persist
        via the write command
    @type  persist: boolean

    @param description: a short explanation of what this config item
        is.
    @type  description: string
    """
    self._name = name
    self._value = originalvalue
    self._persist = persist
    self._description = description

  def set(self, newvalue):
    """
    Sets the value.  This should check the value first, and then
    set it if it's ok.

    Override this if you need to provide additional functionality.

    @param newvalue: the new value to set
    @type  newvalue: varies

    @returns: the old value
    @rtype: varies
    """
    if self.check(newvalue) == 1:
      oldvalue = self._value
      self._value = newvalue
      return oldvalue

  def check(self, value):
    """
    Checks the value to verify that it's a valid value for this
    config data item.  Override this so that it checks the incoming
    value and if it's not a valid type, it kicks up a TypeError.
    If it's not a valid value (different than not being a valid 
    type) it kicks up a ValueError.  If everything is ok, it should
    return the converted argument.

    @param value: the value to check (and convert)
    @type  value: string

    @returns: the converted value if everything is kosher
    @rtype: varies

    @raises: TypeError if it's not a valid type
    @raises: ValueError if it's not a valid value
    """
    return value

  def get(self):
    """
    Retrieves the value in question.

    @returns: the value we're holding
    @rtype: varies
    """
    return self._value

  def getDescription(self):
    """
    Gets the description of the config item.

    @returns: the description of the config item
    @rtype: string
    """
    return self._description


class StringConfig(ConfigBase):
  """
  Holds a string.
  """
  def check(self, value):
    if type(value) != types.StringType:
      raise TypeError("Value is not of type string.")
    return value

class CharConfig(ConfigBase):
  """
  Holds a single character.
  """
  def check(self, value):
    if type(value) != types.StringType:
      raise TypeError("Value is not of type string.")

    if len(value) != 1:
      raise ValueError("Value must be only one character.")

    return value

class IntConfig(ConfigBase):
  """
  Holds an int.
  """
  def check(self, value):
    return int(value)
  
class BoolConfig(ConfigBase):
  """
  Holds a boolean value.
  """
  def check(self, value):
    ret = utils.convert_boolean(arg)
    if ret == 1 or ret == 0:
      return ret

    raise ValueError("Invalid boolean value specified: %s" % (value))


class ConfigManager(manager.Manager):
  """
  Holds all the configuration pieces for Lyntin.
  """
  def __init__(self):
    # this is a map of session -> (map of config names -> items)
    self._config = {}

  def add(self, name, configitem, ses=None):
    """
    Adds a new configuration item.

    @param name: the name of the item
    @type  name: string

    @param configitem: the configuration item to add
    @type  configitem: ConfigBase

    @param ses: if this item is session based, then this is the session
        to associate the item with
    @type  ses: Session
    """
    if not self._config.has_key(ses):
      self._config[ses] = {}

    if self._config[ses].has_key(name):
      raise ValueError("Already have a config item of that name.")

    self._config[ses][name] = configitem
    self._configChangeHook(ses, name, None, configitem.get())

  def change(self, name, newvalue, ses=None):
    """
    Changes the value of a configuration item and then (if 
    successful), it spams the config_change_hook with the
    session (or None), name of the config item, the old value 
    and the new value.

    @param name: the name of the item to change
    @type  name: string

    @param newvalue: the new value to change it to
    @type  newvalue: varies (probably a string)

    @param ses: the session (or None if this is not session-scoped)
    @type  ses: Session
    """
    if not self._config.has_key(ses):
      raise ValueError("Session '%s' does not exist." % repr(ses))

    if not self._config[ses].has_key(name):
      raise ValueError("No config item of that name.")

    oldvalue = self._config[ses][name].set(newvalue)
    self._configChangeHook(ses, name, oldvalue, newvalue)

  def get(self, name, ses=None, defaultvalue=constants.NODEFAULTVALUE):
    """
    Gets a value for a config item.  If the default value is
    not specified, then it will raise a ValueError.

    @param name: the name of the item to retrieve the value of
    @type  name: string

    @param ses: the session (or None if this is not session-scoped)
    @type  ses: Session
     
    @param defaultvalue: the value to return if there is no config
        item of that name.  if you don't specify this, then we'll
        raise a ValueError.
    @type  defaultvalue: varies
    """
    if not self._config.has_key(ses):
      if ses == None:
        self._config[None] = {}
      else:
        raise ValueError("Session '%s' does not exist." % repr(ses))

    if not self._config[ses].has_key(name):
      if defaultvalue == constants.NODEFAULTVALUE:
        raise ValueError("No config item of that name")
      else:
        return defaultvalue

    return self._config[ses][name].get()

  def _configChangeHook(self, ses, name, value, newvalue):
    exported.hook_spam("config_change_hook", 
        {"session": ses, "name": name, "oldvalue": value, "newvalue": newvalue })

# the character used to denote variables (FIXME - this is only half true)
variablechar = '$'

# whether (1) or not (0) we're in debug mode which helps us figure out
# how our commands are being evaluated
debugmode = 0

# whether (1) or not (0) we're doing prompt detection.  prompt detection
# is done in net.py when mud data comes in.
promptdetection = 0

# whether (1) or not (0) we do speedwalking checks
speedwalk = 1

# whether (1) or not (0) we whack all the ansi stuff for incoming mud data
ansicolor = 1

# whether (1) or not (0) we're echoing user input to the ui
mudecho = 1

# this holds a list of all the modules Lyntin has dynamically imported
# or have been imported via the #import command.
lyntinmodules = []

# holds the application options--these are adjusted by command-line 
# arguments only
options = {'datadir': '',
           'moduledir': [],
           'readfile': [],
           'snoopdefault': 1,
           'ui': 'text'}

def fixdir(d):
  """
  Takes in a directory (datadir, moduledir, ...) and fixes it (by
  adding an os.sep to the end) as well as verifies that it exists.

  If it does not exist, then it returns a None.  If it does exist,
  then it returns the adjusted directory name.

  @param d: the directory in question
  @type  d: string

  @returns: None or the fixed directory
  @rtype: string
  """
  if not os.path.exists(d):
    return None

  if len(d) > 0 and d[-1] != os.sep:
    d = d + os.sep

  return d

"""
todo - 
build a configurationmanager
add an exported.addConfig, exported.getConfig, exported.setConfig

addConfig takes a Config* object (ConfigInt, ConfigString, ConfigBoolean)

Config* objects allow you to set whether the item is persisted and
what the default value is.

then #config command becomes a front end for all of this.

#write will cause all persisted config options to become persisted

then we have a config_change_hook just like the variable_change_hook.
"""
