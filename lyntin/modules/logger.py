#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: logger.py,v 1.1 2003/05/05 05:56:02 willhelm Exp $
#######################################################################
"""
This module defines the LoggerManager which handles logging.

Logging can be turned on and shut off on a session by session basis.
"""
import string, os
from lyntin import ansi, manager, __init__, utils, hooks, exported
from lyntin.modules import modutils


class LoggerData:
  def __init__(self):
    self._logfile = None
    # whether or not to strip ansi--0 is off, 1 is on
    self._strip_ansi = 0

  def log(self, ses, input):
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
      exported.write_traceback("Logfile cannot be written to.", ses)

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
    if self._logfile:
      self._logfile.close()
      self._logfile = None

  def openLogFile(self, filename, stripansi=1):
    """
    Opens a new logfile.

    @param filename: the name of the new file to open in append mode.
    @type  filename: string

    @param stripansi: whether (1) or not (0) to strip ansi from the
        logs
    @type  stripansi: boolean
    """
    self._strip_ansi = stripansi
    # FIXME - what happens if we already have a logfile open?
    self._logfile = open(filename, "a")

  def setLogFile(self, fileob, stripansi=1):
    """
    Sets the logfile.

    @param fileob: the new File instance
    @type  fileob: File
    """
    self._logfile = fileob
    self._strip_ansi = stripansi

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

    logger = LoggerData()
    self._loggers[ses] = logger
    return logger

  def mudfilter(self, args):
    """
    mud_filter_hook function for filtering incoming data from the mud.
    """
    ses = args[0]
    text = args[-1]

    if self._loggers.has_key(ses):
      self._loggers[ses].log(ses, text)

    return text

  def fromuser(self, args):  
    """
    from_user_hook function for logging user input.
    """
    ses = exported.get_current_session()
    text = args[0]

    if self._loggers.has_key(ses):
      self._loggers[ses].log(ses, text+"\n")

    return text


commands_dict = {}

def log_cmd(ses, args, input):
  """
  Will start or stop logging to a given filename for that session.
  Each session can have its own logfile.

  category: commands
  """
  logfile = args["logfile"]
  databuffer = args["databuffer"]
  stripansi = args["stripansi"]

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
      logfile = __init__.options['datadir'] + logfile

    if databuffer:
      f = open(logfile, "w")
      buffer = "".join(ses.getDataBuffer())
      f.write(buffer)
      exported.write_message("log: dumped %d lines of databuffer to logfile" % buffer.count("\n"), ses)
      loggerdata.setLogFile(f, stripansi)

    else:
      loggerdata.openLogFile(logfile, stripansi)

    if stripansi:
      stripansimessage = " stripping ansi"
    else:
      stripansimessage = ""

    exported.write_message("log: starting logging to '%s'%s." % (logfile, stripansimessage), ses)
  except Exception, e:
    exported.write_error("log: logfile cannot be opened for appending. %s" % (e), ses)

commands_dict["log"] = (log_cmd, "logfile= databuffer:boolean=false stripansi:boolean=true")



lm = None

def load():
  """ Initializes the module by binding all the commands."""
  global lm
  modutils.load_commands(commands_dict)
  lm = LoggerManager()
  exported.add_manager("logger", lm)
  hooks.from_user_hook.register(lm.fromuser, 30)
  hooks.mud_filter_hook.register(lm.mudfilter, 30)

def unload():
  """ Unloads the module by calling any unload/unbind functions."""
  global lm
  modutils.unload_commands(commands_dict.keys())
  exported.remove_manager("logger")
  hooks.from_user_hook.unregister(lm.fromuser)
  hooks.mud_filter_hook.unregister(lm.mudfilter)

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
