#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: session.py,v 1.3 2003/07/14 19:57:15 glasssnake Exp $
#######################################################################
"""
Holds the functionality involved in X{session}s.  Sessions are copied 
from the common session.  Each session encapsulates a socket connection
to a mud--though it should be noted that sessions could also connect
to any other TCP/IP service.
"""
import re, copy, string, os
import exported, engine, utils, ansi, __init__, event

ESC = chr(27)

class Session:
  """
  A session is a nice container of all the stuff that encompasses a 
  user session: aliases, actions, commands...

  All input and output goes through the Session object.
  Almost everything happens through the Session.
  """
  def __init__(self):
    """
    Initialize.
    """
    self._socket = None
    self._name = ""
    self._host = "none"
    self._port = 0
    self._colorbuffer = ''

    self._databuffer = []
    self._databuffersize = 10000

    # allows users to toggle whether we're handling actions.
    # 0 for handling actions, 1 if we're ignoring actions.
    self._ignoreactions = 0

    # allows users to toggle whether we're doing substitutions.
    # 0 for substitutions, 1 if we're ignoring substitutions
    self._ignoresubs = 0

    # tells us whether we're in verbatim mode where we don't
    # do any massaging of user data.
    # 0 if we're massaging stuff, 1 if we're in verbatim mode
    self._verbatim = 0

    # whether or not we show text even when we're not the
    # current session.  it's command-line configurable what
    # the default is.
    # 0 if we don't show text, 1 if we do
    self._snoop = __init__.options['snoopdefault']

    # register with the shutdown hook 
    exported.hook_register("shutdown_hook", self.shutdown)
    exported.hook_register("write_hook", self.getWriteFileInfo)

  def __repr__(self):
    return "session.Session %s" % self._name

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

  def getSnoop(self):
    """
    Returns whether or not we show text when we're not the
    current session.

    @returns: 1 if we show text, 0 if not
    @rtype: boolean
    """
    return self._snoop

  def setSnoop(self, snoop):
    """
    Sets whether or not we show text when we're not the
    current session.

    @param snoop: 1 if we show text, 0 if not
    @type  snoop: boolean
    """
    self._snoop = snoop

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
    if self._snoop == 1:
      data.append("   snoop: on")
    else:
      data.append("   snoop: off")
    data.append("   socket: %s" % repr(self._socket))

    return data

  def getWriteFileInfo(self, args):
    """
    Implements the write_hook.  Persists information about whether
    speedwalking and ansicolor are active.

    @param args: the args tuple for the write_hook
    @type  args: tuple
    """
    ses = args["session"]

    if not ses == self:
      return

    file = args["file"]
    quiet = args["quiet"]
    if quiet == 1:
      quiet = " quiet={true}"
    else:
      quiet = ""

    data = []

    # saves speedwalking state
    if __init__.speedwalk == 1:
      data.append(__init__.commandchar + "config speedwalk on" + quiet)
    else: 
      data.append(__init__.commandchar + "config speedwalk off" + quiet)

    # saves ansi state
    if __init__.ansicolor == 1:
      data.append(__init__.commandchar + "config ansicolor on" + quiet)
    else: 
      data.append(__init__.commandchar + "config ansicolor off" + quiet)

    file.write(string.join(data, "\n") + "\n")

  def clear(self):
    """
    Clears the session (except for connections).  Goes through
    the list of managers registered with the engine and calls
    the clear method with itself.
    """
    engine = exported.get_engine()
    for mem in engine._managers.values():
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
      self._databuffer = self._databuffer[-self._databuffersize:]

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
  ### User input functions
  ### ------------------------------------------------

  def prompt(self):
    """
    Deals with printing a prompt if this is the common session.
    """
    if self.getName() == "common":
      engine.myengine.writePrompt()

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
    spamargs = {"session": self, "internal": internal, "verbatim": self._verbatim, "data": input, "dataadj": input}
    spamargs = exported.hook_spam("user_filter_hook", argmap=spamargs, 
          mappingfunc=exported.filter_mapper)

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

      spamargs = exported.hook_spam("mud_filter_hook", spamargs, mappingfunc=exported.filter_mapper)
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
