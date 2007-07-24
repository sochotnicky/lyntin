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
# $Id: logger.py,v 1.9 2007/07/24 00:39:03 willhelm Exp $
#########################################################################
"""
This module defines the LoggerManager which handles logging.

Logging can be turned on and shut off on a session by session basis.
"""
import string, os, thread
from lyntin import ansi, manager, config, utils, exported, constants
from lyntin.modules import modutils


class LoggerData:
  def __init__(self, session):
    self._logfile = None
    self._session = session
    # whether or not to strip ansi--0 is off, 1 is on
    self._strip_ansi = 0
    # pending user inputs:
    self._user_input = []
    # pending mud prompt:
    self._prompt = None
    self._userprefix = ''

    self._lock = thread.allocate_lock()

  def log(self, input):
    """
    Logs text to a file instance self._logfile and optionally
    filters ansi according to self._strip_ansi.

    @param input: the string to log to the logfile for this session
    @type  input: string
    """
    if self._logfile == None:
      return

    try:
      if self._strip_ansi == 1:
        input = ansi.filter_ansi(input)

      text = utils.filter_cm(input)
      text = text.replace("\n", os.linesep)
      self._logfile.write(text)
      self._logfile.flush()
    except:
      self._logfile = None
      exported.write_traceback("Logfile cannot be written to.", self._session)

  def log_mud(self, input):
    """
    Logs mud output, synchronizing it with user inputs.

    @param input: the string from the mud for this session
    @type  input: string
    """
    try:
      self._lock.acquire()
      
      if not input.endswith("\n"):
        # this is a prompt
        if self._prompt:
          # we already have one pending
          # (I'm not sure if it is possible, but who knows all the muds :)
          self.log(self._prompt[0]+"\n")
          self._prompt = (input, )
        elif self._user_input:
          # we have pending user input:
          self._log_user_input(input)
        else:
          # don't log prompts immediately, 
          # wait for a user input or a mud output
          self._prompt = (input, )
      else:
        # it is ordinal output from mud
        if self._prompt:
          # we have a prompt pending, let's log it first:
          self.log(self._prompt[0]+"\n")
          self._prompt = None
        self.log(input)
    finally:
      self._lock.release()

  def _log_user_input(self, prompt):
    self.log(''.join((prompt, "; ".join(self._user_input), "\n")))
    self._user_input = []

  def log_user(self, input):
    """
    Logs user input, synchronizing it with mud output.

    @param input: the string from user
    @type  input: string
    """
    try:
      self._lock.acquire()
      self._user_input.append(input)
      if self._prompt:
        # There is a prompt pending
        self._log_user_input(self._prompt[0])
        self._prompt = None
      elif self._userprefix: 
        # We have a default prefix, so we won't wait for next prompt;
        # instead we'll log all the user input we have right away
        # prepending it with the default prefix
        self._log_user_input(self._userprefix)
      elif len(self._user_input) > 100:
        # XXX something wrong, the server doesn't send prompts.
        # XXX Let's dump all the input we have into log now.
        # XXX For such a server one should use
        # XXX   #log <filename> userprefix="something"
        self._log_user_input(self._userprefix)
    finally:
      self._lock.release()

  def isLogging(self):
    """
    Tells whether we're logging or not.

    @returns: 1 if we're logging, 0 if not
    @rtype: boolean
    """
    if self._logfile == None:
      return 0
    return 1

  def closeLogFile(self):
    """
    Closes the logfile if it's currently open.
    """
    
    try:
      self._lock.acquire()
      if self._prompt:
        self.log(self._prompt[0]+"\n")
        self._prompt = None
      elif self._user_input:
        self._log_user_input(self._userprefix)
    finally:
      self._lock.release()

    if self._logfile:
      self._logfile.close()
      self._logfile = None

  def openLogFile(self, filename, stripansi=1, userprefix=''):
    """
    Opens a new logfile.

    @param filename: the name of the new file to open in append mode.
    @type  filename: string

    @param stripansi: whether (1) or not (0) to strip ansi from the
        logs
    @type  stripansi: boolean
    """
      
    # FIXME - what happens if we already have a logfile open?
    self.setLogFile(open(filename, "a"), stripansi, userprefix)

  def setLogFile(self, fileob, stripansi=1, userprefix=""):
    """
    Sets the logfile.

    @param fileob: the new File instance
    @type  fileob: File
    """
    self._logfile = fileob
    self._strip_ansi = stripansi
    self._userprefix = userprefix

  def clear(self):
    """
    Stops the logger.
    """
    self.closeLogFile()

  def getStatus(self):
    """
    Returns a one-liner describing this data object

    @return: one liner describing this object
    @rtype: string
    """
    if self._logfile:
      if self._strip_ansi == 1:
        return "logging to '" + self._logfile.name + "' (noansi)"
      else:
        return "logging to '%s'" % self._logfile.name
    else:
      return "logging not enabled"


class LoggerManager(manager.Manager):
  def __init__(self):
    self._loggers = {}

  def clear(self, ses):
    if self._loggers.has_key(ses):
      self._loggers[ses].clear()

  def getStatus(self, ses):
    if self._loggers.has_key(ses):
      return self._loggers[ses].getStatus()
    return "logging not enabled"

  def removeSession(self, ses):
    if self._loggers.has_key(ses):
      self._loggers[ses].closeLogFile()
      del self._loggers[ses]

  def getLogData(self, ses):
    if self._loggers.has_key(ses):
      return self._loggers[ses]

    logger = LoggerData(ses)
    self._loggers[ses] = logger
    return logger

  def mudfilter(self, args):
    """
    mud_filter_hook function for filtering incoming data from the mud.
    """
    ses = args["session"]
    text = args["dataadj"]

    logger = self._loggers.get(ses)
    if logger:
      logger.log_mud(text)

    return text

  def promptfilter(self, args):
    """
    prompt_filter_hook function for filtering incoming prompt from the mud.
    """
    logger = self._loggers.get(args["session"])
    text = args["prompt"]
    if logger:
      logger.log_mud(text)

    return text

  def tomudfilter(self, args):
    """
    to_mud_hook function for logging user input.
    """
    session = args["session"]
    text = args["data"]

    logger = self._loggers.get(session)
    if logger:
      logger.log_user(text)

    return text  


commands_dict = {}

def log_cmd(ses, args, input):
  """
  Will start or stop logging to a given filename for that session.
  Each session can have its own logfile.

  If USERPREFIX is set, then every line from the user will be 
  prepended with this prefix and immediately written into log file. 
  If USERPREFIX is omitted, then the user input will be attached to 
  mud prompts before logging.

  category: commands
  """
  logfile = args["logfile"]
  databuffer = args["databuffer"]
  stripansi = args["stripansi"]
  userprefix = args["userprefix"]

  if not ses.isConnected():
    exported.write_error("log: You must have a session to log.", ses)
    return

  lm = exported.get_manager("logger")
  loggerdata = lm.getLogData(ses)

  if not logfile:
    exported.write_message(loggerdata.getStatus(), ses)
    return

  # handle stopping logging
  if loggerdata.isLogging() == 1:
    try:
      logname = loggerdata._logfile.name
      loggerdata.closeLogFile()
      exported.write_message("log: stopped logging to '%s'." % logname, ses)
    except Exception, e:
      exported.write_error("log: logfile cannot be closed (%s)." % (e), ses)
    return

  # handle starting logging
  try:
    if os.sep not in logfile:
      logfile = config.options["datadir"] + logfile

    if databuffer:
      f = open(logfile, "w")
      buffer = "".join(ses.getDataBuffer())
      f.write(buffer)
      exported.write_message("log: dumped %d lines of databuffer to logfile" % buffer.count("\n"), ses)
      loggerdata.setLogFile(f, stripansi, userprefix)

    else:
      loggerdata.openLogFile(logfile, stripansi, userprefix)
    if stripansi:
      stripansimessage = " stripping ansi"
    else:
      stripansimessage = ""

    exported.write_message("log: starting logging to '%s'%s." % (logfile, stripansimessage), ses)
  except Exception, e:
    exported.write_error("log: logfile cannot be opened for appending. %s" % (e), ses)

commands_dict["log"] = (log_cmd, 'logfile= databuffer:boolean=false stripansi:boolean=true userprefix=')



lm = None

def load():
  """ Initializes the module by binding all the commands."""
  global lm
  modutils.load_commands(commands_dict)
  lm = LoggerManager()
  exported.add_manager("logger", lm)

  exported.hook_register("to_mud_hook", lm.tomudfilter, constants.LAST+1)
  exported.hook_register("mud_filter_hook", lm.mudfilter, 30)
  exported.hook_register("prompt_hook", lm.promptfilter, 30)

def unload():
  """ Unloads the module by calling any unload/unbind functions."""
  global lm
  modutils.unload_commands(commands_dict.keys())
  exported.remove_manager("logger")

  exported.hook_unregister("to_mud_hook", lm.tomudfilter)
  exported.hook_unregister("mud_filter_hook", lm.mudfilter)
  exported.hook_unregister("prompt_hook", lm.promptfilter)

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
