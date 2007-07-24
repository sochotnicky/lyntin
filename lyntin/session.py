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
# $Id: session.py,v 1.14 2007/07/24 00:39:03 willhelm Exp $
#########################################################################
"""
Holds the functionality involved in X{session}s.  Sessions are copied 
from the common session.  Each session encapsulates a socket connection
to a mud--though it should be noted that sessions could also connect
to any other TCP/IP service.

X{disconnect_hook}::

   When the connection from Lyntin to the mud ends, we spam this hook.

   Arg mapping: { "session": Session, "host": string, "port": int }

   session - the session that we just lost the connection to

   host - the mud we were connected to

   port - the port we were connected to


X{to_mud_hook}::

   All data that gets sent from Lyntin to the mud gets spammed
   to this hook.  This is different from the from_user_hook
   because this data has already passed through Lyntin's 
   transform mechanisms.

   Arg mapping: { "session": Session, "data": string, "tag": varies }

   session - the session of the mud we're sending the data to

   data - the raw data we're sending

   tag - this allows you to "tag" outgoing data so that you can 
         correlate the outgoing data with incoming data and build
         lock-step mechanisms that track user input and mud output.


X{user_filter_hook}::

   After data has passed on the from_user_hook it gets passed through
   the user_filter_hook which allows the data from the user to
   be transformed.  This includes alias expansion, variable expansion,
   speedwalk expansion and whatever other modules listen to this
   hook.

   Functions that register with this hook should return the dataadj
   if they did nothing or the adjusted dataadj if they transformed it.
   Look at examples in the alias and speedwalk modules.

   Arg mapping: { "session": Session, "internal": boolean, "verbatim": boolean,
                  "data": string, "dataadj": string }

   session - the session this data is associated with

   internal - whether or not this is internally generated.  this affects
              whether we spam the from_user_hook and whether this 
              gets logged in the HistoryManager.

   verbatim - whether or not we should be transforming this user data item.

   data - the original raw user data

   dataadj - the latest adjusted data (which originally was the original
             raw user data)


X{mud_filter_hook}::

   Data that comes from the mud gets passed through the from_mud_hook first.
   Then it passes through the mud_filter_hook where it gets transformed.
   Actions, substitutes, gags, and things of that nature should register
   with this hook.

   Functions that register with this hook should return the dataadj if
   they don't want to adjust the mud data or the adjusted dataadj if they
   do adjust the mud data.  See the action, gag and highlight modules for
   examples.
   
   Arg mapping: { "session": Session, "data": string, "dataadj": string }

   session - the Session associated with the mud this data came from

   data - the original raw data from the mud

   dataadj - the latest adjusted data from the mud
"""
import re, copy, string, os
from lyntin import exported, utils, ansi, config, event

ESC = chr(27)

class Session:
  """
  A session is a nice container of all the stuff that encompasses a 
  user session: aliases, actions, commands...

  All input and output goes through the Session object.
  Almost everything happens through the Session.
  """
  global_vars = {}

  def __init__(self, engine_instance):
    """
    Initialize.
    """
    self._engine = engine_instance
    self._socket = None
    self._name = ""
    self._host = "none"
    self._port = 0
    self._colorbuffer = ''

    self._databuffer = []
    self._databuffersize = 10000

    # register with the shutdown hook 
    self._engine.hookRegister("shutdown_hook", self.shutdown)

    # session variables
    self._vars = {}

  def __repr__(self):
    return "session.Session %s" % self._name

  def setupCommonSession(self):
    import config
    c = self._engine.getConfigManager()

    if type(config.options["snoopdefault"]) is list:
      config.options["snoopdefault"] = config.options["snoopdefault"][0]

    tc = config.BoolConfig("snoop", utils.convert_boolean(config.options['snoopdefault']), 0,
          "Whether or not you see the data from this session when it's not "
          "active.")
    c.add("snoop", tc, self)
    
    tc = config.BoolConfig("verbatim", 0, 0,
          "Whether we're in verbatim mode where we pass the user text "
          "straight to the mud without massaging it.")
    c.add("verbatim", tc, self)

  def getName(self):
    """
    Returns the name of the session.

    @returns: the name of the session
    @rtype: string
    """
    return self._name

  def setName(self, name):
    """
    Sets the name of the session.

    @param name: the new name
    @type  name: string
    """
    self._name = name
    if self._socket:
      self._socket.setSessionName(name)

  def shutdown(self, args):
    """
    Shuts down the session, shuts down the underlying SocketCommunicator.

    @param args: the args tuple for the shutdown_hook.
    @type  args: tuple
    """
    if len(args) > 0:
      quiet = 1
    else:
      quiet = 0

    # unregister with the shutdown hook
    # exported.hook_unregister("shutdown_hook", self.shutdown)
    if self.getName() != "common":
      if quiet == 0:
        event.OutputEvent("Session %s disconnected.\n\"#zap %s\" to kill the session.\n" % (self._name, self._name)).enqueue()
      exported.hook_spam("disconnect_hook", {"session": self, "host": self._host,  "port": self._port})

      if self._socket:
        self._socket.shutdown()

      self._host = None
      self._port = 0
      self._socket = None

  def getStatus(self):
    """
    Returns status of the session.  Most specifically the session name,
    the socket we're connected to.

    @returns: the status string
    @rtype: string
    """
    data = []
    
    data.append("Session name: %s" % self._name)
    data.append("   socket: %s" % repr(self._socket))

    return data

  def clear(self):
    """
    Clears the session (except for connections).  Goes through
    the list of managers registered with the engine and calls
    the clear method with itself.
    """
    for mem in self._engine._managers.values():
      mem.clear(self)

    self._databuffer = []


  ### ------------------------------------------------
  ### Socket stuff
  ### ------------------------------------------------

  def setSocketCommunicator(self, sc):
    """
    Sets the socket communicator.

    @param sc: the new SocketCommunicator instance
    @type  sc: SocketCommunicator
    """
    self._socket = sc

  def getSocketCommunicator(self):
    """
    Returns the socket communicator.

    @returns: SocketCommunicator instance
    @rtype: SocketCommunicator
    """
    return self._socket

  def isConnected(self):
    """
    Tells you whether (1) or not (0) a session has a connection.

    @returns: 1 if connected, 0 if not
    @rtype: boolean
    """
    return self._socket != None

  def writeSocket(self, message, tag=None):
    """
    Writes data to the socket.

    @param message: the data to be written to the mud
    @type  message: string

    @param tag: Used to tag data being sent to the mud for 
        identification when it comes out of the to_mud_hook.  
        Simply passed through as-is by lyntin internals.
    @type  tag: varies
    """
    for line in message.strip().split("\n"):
      exported.hook_spam("to_mud_hook", {"session": self, "data": line, "tag": tag})

    if self._socket:
      retval = self._socket.write(str(message))
      if retval:
        exported.write_error("socket write: %s" % retval)

    else:
      # if we don't have a socket then we can't do any non-lyntin-command
      # stuff.
      exported.write_error("No connection.  Create a session.\n(See also: #help, #help session)")
      return


  ### ------------------------------------------------
  ### Data buffer stuff
  ### ------------------------------------------------
  def getDataBuffer(self):
    """
    Returns the DataBuffer instance for this session.

    @returns: list of strings
    @rtype: list of strings
    """
    return self._databuffer

  def addToDataBuffer(self, text):
    """
    Adds data to the buffer by thinking about everything
    in terms of lines.
    
    @param text: the text to add to the buffer
    @type  text: string
    """
    text = ansi.filter_ansi(utils.filter_cm(text))
    lines = text.splitlines(1)

    for mem in lines:
      if len(self._databuffer) == 0 or self._databuffer[-1].endswith("\n"):
        self._databuffer.append(mem)
      else:
        self._databuffer[-1] += mem

    if len(self._databuffer) > self._databuffersize:
      self._databuffer[:-self._databuffersize] = []

  def clearDataBuffer(self):
    """ 
    Clears the databuffer.
    """
    self._databuffer = []
  
  def resizeDataBuffer(self, newsize=10000):
    """ 
    Changes the buffer max.

    @param newsize: the new buffer max size
    @type  newsize: int
    """
    self._databuffersize = newsize


  ### ------------------------------------------------
  ### Variable managing stuff
  ### ------------------------------------------------
  def _varChangeHook(self, var, old, new):
    """
    This calls the variable_change_hook.  It allows other modules to
    know when variable values are changed so that they can handle
    those changes accordingly.
    """
    exported.hook_spam("variable_change_hook", 
          {"session": self, "variable": var, "oldvalue": old, "newvalue": new})

  def setVariable(self, var, expansion):
    """
    Sets a variable value.  This also calls the variable_change_hook.

    @param var: the variable name to set
    @type  var: string

    @param expansion: the new value of the variable.  this can be a string
        or a class with a __str__ method.
    @type  expansion: string
    """
    if var.startswith("_"):
      d = Session.global_vars
    else:
      d = self._vars

    oldvalue = d.get(var, None)
    d[var] = expansion

    self._varChangeHook(var, oldvalue, expansion)

  def removeVariable(self, var):
    """
    Removes a variable from the local _vars dict.  This also spams the
    variable_change_hook.

    @param var: the name of the variable to remove
    @type  var: string
    """
    if var.startswith("_"):
      d = Session.global_vars
    else:
      d = self._vars

    if d.has_key(var):
      oldvalue = d[var]
      del d[var]
      self._varChangeHook(var, oldvalue, None)

  def getVariable(self, var, default=None):
    if var.startswith("_"):
      d = Session.global_vars
    else:
      d = self._vars

    return d.get(var, default)

  ### ------------------------------------------------
  ### User input functions
  ### ------------------------------------------------
  def prompt(self):
    """
    Deals with printing a prompt if this is the common session.
    """
    if self.getName() == "common":
      self._engine.writePrompt()

  def handleUserData(self, input, internal=0 ):
    """
    Handles input in the context of this session specifically.

    @param input: the user data
    @type  input: string

    @param internal: whether the command came from interally.
        we won't spam hooks and may at some point prevent
        output for internal stuff too.  1 if internal, 0 if not.
    @type  internal: boolean
    """
    # this is the point of much recursion.  everything is registered
    # as a filter and recurses accordingly.
    spamargs = {"session": self, "internal": internal, 
                "verbatim": exported.get_config("verbatim", self), 
                "data": input, "dataadj": input}
    spamargs = exported.filter_mapper_hook_spam("user_filter_hook", spamargs)

    if spamargs == None:
      return
    else:
      input = spamargs["dataadj"]

    # after this point we don't do any more recursion.  so it's
    # safe to unescape things and such.
    input = input.replace("\\;", ";")
    input = input.replace("\\$", "$")
    input = input.replace("\\%", "%")

    # just regular data to the mud
    self.writeSocket(input + "\n")


  ### ------------------------------------------------
  ### Mud input functions
  ### ------------------------------------------------

  def handleMudData(self, input):
    """
    Handles input coming from the mud.

    @param input: the data coming from the mud
    @type  input: string
    """
    # this sort of handles ansi color codes that get broken 
    # mid-transmission when mud data is chunked and sent across
    # the network.
    if self._colorbuffer:
      input = self._colorbuffer + input
      self._colorbuffer = ''

    index = input.rfind(ESC)
    if index != -1 and input.find("m", index) == -1:
      self._colorbuffer = input[index:]
      input = input[:index]

    # we add the new input to the databuffer
    self.addToDataBuffer(input)

    # we split the input into a series of lines and operate on
    # those
    inputlines = input.splitlines(1)

    for i in range(0, len(inputlines)):
      mem = inputlines[i]
      # call the pre-filter hook
      spamargs = {"session": self, "data": mem, "dataadj": mem}

      spamargs = exported.filter_mapper_hook_spam("mud_filter_hook", spamargs)
      if spamargs != None:
        mem = spamargs["dataadj"]
      else:
        mem = ""

      inputlines[i] = mem

    exported.write_mud_data("".join(inputlines), self)


# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
