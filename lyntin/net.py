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
# $Id: net.py,v 1.19 2007/07/24 00:39:03 willhelm Exp $
#########################################################################
"""
This holds the SocketCommunicator class which handles socket
connections with a mud and polling the connection for data.

X{bell_hook}::

   When the mud sends a bell character, we spam this hook.  Typically
   the ui's will register with this hook and handle the bell however
   they see fit.

   Arg mapping: { "session": Session }

   session - the session that received the bell


X{prompt_hook}::

   We try to do some prompt detection and separate prompts into their
   own events (separate from mud data).

   Arg mapping: { "session": Session, "prompt": string }

   session - the Session that this prompt came from

   prompt - the prompt string


X{connect_hook}::

   This hook gets spammed every time we make a successful connection.

   Arg mapping: { "session": Session, "host": String, "port": int }

   session - the Session object for this connection

   host - the host we connected to

   port - the port number for the host


X{net_read_data_filter}::

   This allows you to filter incoming data before it passes through
   Lyntin.  If you were going to write an MCCP module, this is the
   hook it would register with to decompress incoming mud data.

   Functions that register with this hook should return the dataadj
   if they did nothing or the adjusted dataadj if they transformed it.
   Look at the user_filter_hook examples in the alias and speedwalk
   modules.

   Arg mapping: { "session": Session, "data": String, "dataadj": String }

   session - the Session that this data came from

   data - the original data we got from the mud

   dataadj - the data the previous function in the hook returned


X{net_write_data_filter}::

   This allows you to filter outgoing data after it has passed through
   Lyntin and just before it gets sent out on the socket.  If you were 
   going to write an MCCP module, this is the hook it would register 
   with to compress outgoing mud data.

   Functions that register with this hook should return the dataadj
   if they did nothing or the adjusted dataadj if they transformed it.
   Look at the user_filter_hook examples in the alias and speedwalk
   modules.

   Arg mapping: { "session": Session, "data": String, "dataadj": String }

   session - the Session that this data is going to

   data - the original data we wanted to send to the mud

   dataadj - the data the previous function in the hook returned


X{net_handle_telnet_option}::

   There are a series of Telnet options that Lyntin doesn't handle.
   So we allow module writers to handle them if they so desire.
   The data argument is the telnet option string.  So if they
   send us 255 251 24, then that's what you're getting.  We handle
   all the buffering of telnet option stuff--so you needn't worry
   about that.

   We send along the IAC DO TERMTYPE kinds of things as well as the
   IAC SB blah blah IAC SE kinds of things.  This is a handler--so
   if you've handled it, raise an exported.StopSpammingException() .

   Arg mapping: { "session": Session, "data": String }

   session - the Session that this telnet option came from

   data - the telnet option itself

"""
import socket, select, re, os

from lyntin import event, config, exported
from lyntin.ui import message

### --------------------------------------------
### CONSTANTS
### --------------------------------------------

# reverse lookup allowing us to see what's going on more easily
# when we're debugging.
# for a list of telnet options: http://www.freesoft.org/CIE/RFC/1700/10.htm
CODES = {255: "IAC",
         254: "DON'T",
         253: "DO",
         252: "WON'T",
         251: "WILL",
         250: "SB",
         249: "GA",
         240: "SE",
         239: "TELOPT_EOR",
         0:   "<IS>",
         1:   "[<ECHO> or <SEND/MODE>]",
         3:   "<SGA>",
         5:   "STATUS",
         24:  "<TERMTYPE>",
         25:  "<EOR>", 
         31:  "<NegoWindoSize>",
         32:  "<TERMSPEED>",
         34:  "<Linemode>",
         35:  "<XDISPLAY>",
         36:  "<ENV>",
         39:  "<NewENV>",
         85:  "COMPRESS (MCCP)",
         86:  "COMPRESS2 (MCCP)",
         91:  "MXP"}

# more info on 85/86/MCCP: http://www.randomly.org/projects/MCCP/protocol.html
# more info on 91/MXP: http://www.zuggsoft.com/zmud/mxp.htm

# telnet control codes
IAC  = chr(255)
DONT = chr(254)
DO   = chr(253)
WONT = chr(252)
WILL = chr(251)
SB   = chr(250)
GA   = chr(249)
NOP  = chr(241)
SE   = chr(240)
TELOPT_EOR = chr(239)
SEND = chr(1)
MODE = chr(1)
FORWARDMASK = chr(2)
IS   = chr(0)

# some nice strings to help with the telnet control code
# negotiation
DD       = DO + DONT
WW       = WILL + WONT
DDWW     = DD + WW

# telnet option codes
ECHO     = chr(1)
SGA      = chr(3)
TERMTYPE = chr(24)
EOR      = chr(25)
NAWS     = chr(31)
LINEMODE = chr(34)
ENV      = chr(39)

BELL     = chr(7)

def _fcc(code):
  if CODES.has_key(ord(code)):
    return CODES[ord(code)]
  return str(code)

def _cc(option):
  """
  Takes in an option string which we peel apart and return a pretty
  string representation of.

  @param option: the option string to convert
  @type  option: string

  @return: the string representation of the code
  @rtype: string
  """
  if len(option) == 3:
    return " ".join([_fcc(m) for m in option])

  return " ".join([_fcc(option[0]), _fcc(option[1]), _fcc(option[2]), 
                   option[3:-2], _fcc(option[-2]), _fcc(option[-1])])


class SocketCommunicator:
  """
  The SocketCommunicator handles all incoming and outgoing data from 
  and to the mud, telnet control codes, and some data transformations.
  """
  def __init__(self, e, ses, host, port):
    self._engine = e
    self._config = e.getConfigManager()

    self._sessionname = ''
    self._host = host
    self._port = port
    self._sock = None
    self._ansimode = 1
    self._nego_buffer = ''
    self._shutdownflag = 0
    self._session = ses

    self._debug = 0

    # this is the prompt regex that we use to split the incoming text.
    self._prompt_regex = self._buildPromptRegex()

    # this is the regex that we use to split the incoming text.
    delimiters = ( IAC+GA, IAC+TELOPT_EOR, "\n" )
    # make a regexp matching any of the delimiters above
    self._line_regex = re.compile("(" + "|".join(delimiters) + ")",
                                  re.MULTILINE | re.DOTALL)

    # "The server can do delimited prompts" flag
    self._good_prompts = 0

    # handle termtype issues
    if config.options.has_key("term"):
      self._termtype = config.options["term"][0]
    elif os.environ.has_key("TERM"):
      self._termtype = os.environ["TERM"]
    else:
      self._termtype = "lyntin"

    # we keep track of all the telnet stuff we're doing here
    # so we can look at it and dump it or whatever
    self._controllog = []

  def _buildPromptRegex(self, prompt=""):
    """
    Builds the prompt regex.  A prompt is IAC+GA or IAC+TELOPT_EOR or
    any string prompt.  Note that prompts eat up the characters.  So if
    the prompt is ">> " those characters will disappear from the stream.

    Note: the prompt is NOT escaped before it is added to the regexp.  It's
    up to you to re.escape the bits that need escaping.

    @param prompt: the text prompt to use (if any)
    @type  prompt: string

    @returns: the compiled regular expression for prompt detection
    @rtype: Regexp object
    """
    if prompt:
      r = "(" + IAC+GA + "|" + IAC+TELOPT_EOR + "|" + prompt + ")"
    else:
      r = "(" + IAC+GA + "|" + IAC+TELOPT_EOR + ")"
    return re.compile(r)

  def __repr__(self):
    return "connection %s %d" % (self._host, self._port)

  def logControl(self, str):
    self._controllog.append(str)

  def setSessionName(self, name):
    """
    Sets the session name.

    @param name: the new session name
    @type  name: string
    """
    self._sessionname = name

  def shutdown(self):
    """
    Shuts down the thread polling the socket connection and the socket
    as well.
    """
    self._shutdownflag = 1

  def connect(self, host, port, sessionname):
    """
    Takes in a host and a port and connects the socket.

    @param host: the host to connect to
    @type  host: string

    @param port: the port to connect at
    @type  port: int

    @param sessionname: the name of the new session
    @type  sessionname: string
    """
    if not self._sock:
      sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      sock.connect((host, port))
      sock.setblocking(1)

      self._host = host
      self._port = port
      self._sock = sock
      self._sessionname = sessionname

      ses = exported.get_session(sessionname)

      exported.hook_spam("connect_hook", \
              {"session": ses, "host": host, "port": port})
    else:
      raise Exception("Connection already exists.")


  def _pollForData(self):
    """
    Polls the socket for data.
    """
    readers, e, w = select.select([self._sock], [], [], .2)
    if readers:
      return readers[0].recv(1024)

    return None

  def _filterIncomingData(self, data):
    """
    run the data through the net_read_data_filter hook which
    allows things like compressors and other data transformation
    mechanisms to do their thing.
    """
    # be careful--this catches both the '' and the None situations
    if not data:
      return data

    spamargs = {"session": self._session, "data": data, "dataadj": data}
    spamargs = exported.hook_spam("net_read_data_filter", 
          argmap=spamargs, mappingfunc=exported.filter_mapper)

    if spamargs == None:
      data = ""
    else:
      data = spamargs["dataadj"]

    return data

  def run(self):
    """
    While the connection hasn't been shut down, we spin through this
    loop retrieving data from the mud, 
    """
    from lyntin import exported
    try:
      data = ''
      while not self._shutdownflag:
        newdata = self._pollForData()

        if newdata:
          newdata = self._filterIncomingData(newdata)
          if newdata == "":
            continue

          last_index = 0
          alldata = (data+newdata).replace("\r","")
          # incrementally walk through each line in the data,
          # adjusting last_index to the end of the previous match
          for (m) in self._line_regex.finditer(alldata):
            oneline = alldata[last_index:m.end()]
            last_index = m.end()
            self.handleData(oneline)
          # keep the remainder (empty if alldata ended with a delimiter)
          data = alldata[last_index:]

        elif newdata == '':
          # if we got back an empty string, then something's amiss
          # and we should dump them.
          if data:
            self.handleData(data)
          if self._shutdownflag == 0 and self._session:
            self._session.shutdown(())
          break

        elif not self._good_prompts and data:
          # Now we have rest of the input which is neither delimited prompt
          # nor complete line, and we yet did not see this server 
          # delimiting it's prompts with telnet GA or EOR option.
          # We'll handle these data because the socket read was timed out.
          self.handleData(data)
          data = ''

    except SystemExit:
      if self._session:
        self._session.shutdown(())

    except:
      exported.write_traceback("socket exception")
      if self._session:
        self._session.shutdown(())

    # if we hit this point, we want to shut down the socket
    try:    self._sock.shutdown(2)
    except: pass

    try:    self._sock.close()
    except: pass

    self._sock = None
    self._session = None

    # sometimes the mud will hose up with echo off--we want to kick it
    # on again.
    self._config.change("mudecho", "on")

    # output message so the user knows what happened.
    event.OutputEvent(message.Message("Lost connection to: %s\n" % self._host)).enqueue()

  def write(self, data, convert=1):
    """
    Writes data to the mud after passing it through net_write_data_filter.

    @param data: the data to write to the socket
    @type  data: string

    @param convert: whether (1) or not (0) we should convert eol stuff to 
        CRLF and IAC to IAC IAC.
    @type  convert: boolean

    @raises Exception: if we have problems sending the data over the
        socket
    """
    if convert:
      data = data.replace("\n", "\r\n")

      if IAC in data:
        data = data.replace(IAC, IAC+IAC)

    if self._shutdownflag == 0:
      # run the data through the net_write_data_filter hook which
      # allows things like compressors and other data transformation
      # mechanisms to do their thing.
      spamargs = {"session": self._session, "data": data, "dataadj": data}
      spamargs = exported.hook_spam("net_write_data_filter", argmap=spamargs, 
            mappingfunc=exported.filter_mapper)

      if spamargs == None:
        return
      else:
        data = spamargs["dataadj"]
 
      try:
        self._sock.send(data)

      except Exception, e:
        if self._shutdownflag == 0 and self._session:
          self._session.shutdown(())
          raise Exception(e)

      return None

  def handleData(self, data):
    """
    Handles incoming data from the mud.  We wrap it in a MudEvent
    and toss it on the queue.

    @param data: the incoming data from the mud
    @type  data: string
    """
    global BELL

    # handle the bell
    count = data.count(BELL)
    for i in range(count):
      event.SpamEvent(hookname="bell_hook", argmap={"session": self._session}).enqueue()
    data = data.replace(BELL, "")

    # handle telnet option stuff
    if IAC in data:
      data = self.handleNego(data)

    if not self._config.get("promptdetection") or data.endswith("\n"):
      event.MudEvent(self._session, data).enqueue() 
    else:
      event.SpamEvent(hookname="prompt_hook", argmap={"session": self._session, "prompt": data}).enqueue()


  def handleNego(self, data):
    """
    Removes telnet negotiation stuff from the stream and handles it.

    @param data: the incoming data from the mud that we need to parse
        for telnet control code stuff
    @type  data: string

    @return: the data without the telnet control codes
    @rtype:  string
    """
    marker = -1
    i = data.find(IAC)

    while (i != -1):
      if i + 1 >= len(data):
        marker = i
        break

      if data[i+1] == NOP:
        data = data[:i] + data[i+2:]
        self.logControl("receive: IAC NOP")

      elif data[i+1] == GA or data[i+1] == TELOPT_EOR:
        data = data[:i] + data[i+2:]
        # if data is a prompt delimited with some telnet option, 
        # then we'll mark the server as "server with good prompting" 
        self._good_prompts = 1

      elif data[i+1] == IAC:
        data = data[:i] + data[i+1:]
        i = i + 1
        self.logControl("receive: IAC IAC")

      else:
        if i + 2 >= len(data):
          marker = i
          break

        # handles DO/DONT/WILL/WONT stuff
        if data[i+1] in DDWW:
          option = data[i:i+3]

          self.logControl("receive: " + _cc(option))
          if option[2] == ECHO:
            if option[1] == WILL:
              self._config.change("mudecho", "off")
            elif option[1] == WONT:
              self._config.change("mudecho", "on")

          elif option[2] == TERMTYPE:
            if option[1] == DO:
              self.write(IAC + WILL + TERMTYPE, 0)
              self.logControl("send: IAC WILL TERMTYPE")
            else:
              self.write(IAC + WONT + TERMTYPE, 0)
              self.logControl("send: IAC WONT TERMTYPE")

          elif option[2] == EOR:
            if option[1] == WILL:
              self.write(IAC + DO + EOR, 0)
              self.logControl("send: IAC DO EOR")

          else:
            args = {"session": self._session, "data": option}
            # this will give us back the args (in the case that no one
            # handled it) or None (in the case that someone handled it
            # and raised a StopSpammingException).
            ret = exported.hook_spam("net_handle_telnet_option", args)

            if ret:
              if option[1] in DD:
                self.write(IAC + WONT + option[2], 0)
                self.logControl("send: " + _cc(IAC + WONT + option[2]))

              elif option[1] in WW:
                self.write(IAC + DONT + option[2], 0)
                self.logControl("send: " + _cc(IAC + DONT + option[2]))

          data = data[:i] + data[i+3:]

        # handles SB...SE stuff
        elif data[i+1] == SB:

          end = data.find(SE, i)
          if end == -1:
            marker = i
            break

          option = data[i:end+1]
          self.logControl("receive: " + _cc(option))

          if option[2] == TERMTYPE and option[3] == SEND:
            self.write(IAC + SB + TERMTYPE + IS + self._termtype + IAC + SE, 0)
            self.logControl("send: IAC SB TERMTYPE IS " + self._termtype + " IAC SE")
          else:
            args = {"session": self._session, "data": option}
            # this will give us back the args (in the case that no one
            # handled it) or None (in the case that someone handled it
            # and raised a StopSpammingException).
            ret = exported.hook_spam("net_handle_telnet_option", args)

          data = data[:i] + data[end+1:]

        # in case they passed us something weird we remove the IAC and 
        # move on
        else:
          data = data[:i] + data[i+1:]

      i = data.find(IAC, i)

    if marker != -1:
      self._nego_buffer = data[marker:]
      data = data[:marker]

    return data

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
