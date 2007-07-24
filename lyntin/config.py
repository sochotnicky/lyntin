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
# $Id: config.py,v 1.8 2007/07/24 00:39:03 willhelm Exp $
#########################################################################
"""
This module holds the configuration manager as well as a series of
configuration type classes.  It also holds some global variables
that get computed at boot.

X{config_change_hook}::

   This hook notifies registered functions that the value of a 
   config item has just been changed.

   Arg mapping: { "session": Session, "name": string, "oldvalue": string, "newvalue": string }

   session - The session of the config item that got changed.  If the
             session is None, then this is a global config item.

   name - the name of the config item

   oldvalue - the old value of the config item or None if there was
             no previous value.

   newvalue - the new value of the config item
"""
import types, copy
from lyntin import exported, utils, manager, constants

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

    @returns: the old value (actual value)
    @rtype: varies
    """
    oldvalue = self._value

    # check should raise an Exception if the value is not appropriate.
    # it should also return the adjusted value (string -> whatever we're
    # supposed to store)
    self._value = self.check(newvalue)

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

    @raises TypeError: if it's not a valid type
    @raises ValueError: if it's not a valid value
    """
    return value

  def get(self):
    """
    Retrieves the value in question.

    @returns: the value we're holding
    @rtype: varies
    """
    return self._value

  def toString(self):
    """
    Retrieves a textual representation of the value and the type
    of the config item.

    @returns: string
    @rtype: string
    """
    return repr(self._value) + " (varies)"

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

  def toString(self):
    return repr(self._value) + " (string)"

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

  def toString(self):
    return repr(self._value) + " (char)"


class IntConfig(ConfigBase):
  """
  Holds an int.
  """
  def check(self, value):
    return int(value)
  
  def toString(self):
    return repr(self._value) + " (int)"

def bv(bool):
  if bool:
    return "on"
  return "off"

class BoolConfig(ConfigBase):
  """
  Holds a boolean value.
  """
  def check(self, value):
    ret = utils.convert_boolean(value)
    if ret == 1 or ret == 0:
      return ret

    raise ValueError("Invalid boolean value specified: %s" % (value))

  def toString(self):
    return bv(self._value) + " (bool)"


class ConfigManager(manager.Manager):
  """
  Holds all the configuration pieces for Lyntin.
  """
  def __init__(self, e):
    # this is a map of session -> (map of config names -> items)
    self._config = {}
    self._engine = e

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

    @raises ValueError: if we already have an item in that session with
        that name.
    """
    if not self._config.has_key(ses):
      self._config[ses] = {}

    if self._config[ses].has_key(name):
      raise ValueError("Already have a config item of that name.")

    self._config[ses][name] = configitem
    self._configChangeHook(ses, name, None, configitem.get())

  def remove(self, name, ses=None):
    """
    Allows you to remove a configuration item from the system.

    @param name: the name of the item to remove
    @type  name: string

    @param ses: the session from which to remove the item (None if
        it's a general Lyntin item)
    @type  ses: Session

    @raises ValueError: if the item does not exist
    """
    if not self._config.has_key(ses):
      raise ValueError("That session does not exist.")

    if not self._config[ses].has_key(name):
      raise ValueError("That item does not exist.")

    del self._config[ses][name]
    
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
    self._configChangeHook(ses, name, oldvalue, self._config[ses][name].get())

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

  def getConfigItems(self, ses=None):
    """
    Returns all the configuration items for a given session.

    @param ses: the session to pull items for, or None if it's general
        Lyntin configuration stuff
    @type  ses: Session

    @returns: list of ConfigBase subclass objects
    @rtype: list of ConfigBase subclass objects
    """
    if self._config.has_key(ses):
      return self._config[ses].values()

    return []

  def getConfigItem(self, name, ses=None):
    """
    Retrieves a specific configuration item by name and session.  If
    the ses passed in is None, then we look for lyntin general config
    items.

    @param name: the name of the config item to retrieve
    @type  name: string

    @param ses: the session to retrieve the item from (or None if it's
        a global item)
    @type  ses: Session

    @returns: a ConfigBase item or None if the item doesn't exist
    @rtype: ConfigBase
    """
    if not self._config.has_key(ses):
      return None

    if not self._config[ses].has_key(name):
      return None

    return self._config[ses][name]


  def addSession(self, newsession, basesession):
    # if we have nothing to clone from, then we don't want to
    # worry about this
    if not basesession or not self._config.has_key(basesession):
      return

    x = {}

    for mem in self._config[basesession].values():
      x[mem._name] = copy.deepcopy(mem)

    self._config[newsession] = x

  def removeSession(self, ses):
    if self._config.has_key(ses):
      del self._config[ses]

