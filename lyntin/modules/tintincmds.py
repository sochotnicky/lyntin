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
# $Id: tintincmds.py,v 1.26 2007/07/24 00:39:03 willhelm Exp $
#########################################################################

import os, os.path
from lyntin import net, utils, engine, constants, config, exported, event
from lyntin.modules import modutils

"""
This module holds commands that are derived from Tintin, but don't involve
a manager.  Tintin commands that involve a manager (alias and unalias,
action and unaction, variable and unvariable...) are in their respective
modules along with their manager and any helper functions involved.
"""
commands_dict = {}


def bell_cmd(ses, words, input):
  """
  Kicks off the bell for a given session.  Anything registered
  with the bell_hook will get tickled.

  category: commands
  """
  exported.hook_spam("bell_hook", {"session": ses})

commands_dict["bell"] = (bell_cmd, "")


def clear_cmd(ses, words, input):
  """
  This command clears a session of all session data (except the actual 
  connection).  This covers gags, subs, actions, aliases...

  category: commands
  """
  try:
    ses.clear()
    exported.write_message("clear: session %s cleared." % ses.getName(), ses)
  except Exception, e:
    exported.write_traceback("clear: error in clearing session %s" % ses)

commands_dict["clear"] = (clear_cmd, "")
  

def cr_cmd(ses, args, input):
  """
  This sends a carriage return to the mud.  This is useful in aliases 
  and actions that require a carriage return.

  category: commands
  """
  ses.writeSocket("\n")

commands_dict["^cr"] = (cr_cmd, "")


def end_cmd(ses, args, input):
  """
  Closes all sessions and quits out of Lyntin.

  Note: on most muds this will leave your character in a state of 
  linkdeath--it does not sell all your stuff, return you to town, 
  save your character, tell your friends goodbye, or anything of 
  that nature.

  category: commands
  """
  exported.write_message("end: you'll be back...")
  event.ShutdownEvent().enqueue()

commands_dict["^end"] = (end_cmd, "")


def help_cmd(ses, args, input):
  """
  With no arguments, shows all the help files available.
  With an argument, shows that specific help file or lists the contents
  of that category of help files.

  examples:
    #help                      - lists all help files in the root
    #help help                 - shows help for the help command
    #help commands.substitute  - shows help for the substitute command
    #help commands             - shows help for the commands category

  Items that have a number in parentheses after them are a category.
  The number is how many help topics are below that category.

  example:
    > #help
    lyntin: ::Lyntin Help::
    lyntin:
    lyntin: category: root
    lyntin:
    lyntin:    commands(55)  readme(13)
    lyntin:    textui
    >

  category: commands
  """
  item = args["item"]

  keys = item.split(".")
  data = "::Lyntin Help::\n\n"

  error, breadcrumbs, text = exported.get_help(item)

  if error:
    data += "%s\n\n" % error
  if breadcrumbs:
    data += "category: %s\n\n" % breadcrumbs

  data += text
  exported.write_message(data)

commands_dict["help"] = (help_cmd, "item=")


def history_cmd(ses, args, input):
  """
  #history prints the current history buffer.

  ! will call an item in the history indexed by the number after
  the !.  You can also do replacements via the sub=repl syntax.

  examples:
    #history [count=30]
        prints the last count entries in the history buffer
    !
        executes the last thing you did
    !4
        executes the fourth to last thing you did
    !4 3k=gk
        executes the fourth to last thing you did after replacing
        3k with gk in it

  category: commands
  """
  count = args["count"]
  
  historylist = exported.get_history(count)
  for i in range(0, len(historylist)):
    historylist[i] = "%d %s" % ((i+1), historylist[i])
  historylist.reverse()
  exported.write_message("History:\n" + "\n".join(historylist))

commands_dict["history"] = (history_cmd, "count:int=30")


def if_cmd(ses, args, input):
  """
  Allows you to do some boolean logic based on Lyntin variables
  or any Python expression.  If this expression returns a non-false
  value, then the action will be performed otherwise the elseaction
  (if there is one) will be peformed.

  examples:
    #if {$myhpvar < 100} {#showme PANIC!}
    #if {$myhpvar < 100 and $myspvar < 100} {#showme PANIC!}
    #if {'$name' == 'Joe'} {#showme That joe is a jerk.}

  When you're comparing variable values with other strings, make sure 
  to put them in quotes becuase variable expansion happens before
  the if command is evaluated.

  examples:
    WRONG: #if {$name == Joe} {#showme Joe is a jerk.}
    RIGHT: #if {'$name' == 'Joe'} {#showme Joe is a jerk.}

  category: commands
  """
  # original if_cmd code contributed by Sebastian John

  expr = args["expr"]
  action = args["action"]
  elseaction = args["elseaction"]

  try:
    if eval(expr):
      exported.lyntin_command(action, 1, ses)
    elif elseaction:
      exported.lyntin_command(elseaction, 1, ses)
  except SyntaxError:
    exported.write_error("if: invalid syntax / syntax error.", ses)
  except Exception, e:
    exported.write_error("if: exception: %s" % e, ses)

commands_dict["if"] = (if_cmd, "expr action elseaction=")


def info_cmd(ses, args, input):
  """
  Prints all the information about the active session: 
  actions, aliases, gags, highlights, variables, ticker, verbose, 
  speedwalking, and other various things.

  category: commands
  """
  data = exported.myengine.getStatus(ses)
  data = "\n".join(data)
  exported.write_message(data, ses)

commands_dict["info"] = (info_cmd, "")


def killall_cmd(ses, args, input):
  """
  Clears all sessions of session oriented stuff: aliases,
  substitutions, gags, variables, so on so forth.

  category: commands
  """
  for mem in exported.get_active_sessions():
    mem.clear()
    exported.write_message("killall: session %s cleared." % mem.getName())

commands_dict["^killall"] = (killall_cmd, "")


def loop_cmd(ses, args, input):
  """
  Executes a given command replacing %0 in the command with
  the range of numbers specified in <from> and <to>.

  example:
    #loop {1,4} {reclaim %0.corpse}

  will execute:
    reclaim 1.corpse
    reclaim 2.corpse
    reclaim 3.corpse
    reclaim 4.corpse

  Additionally, it can iterate over a comma-separated string of items:

  example:
    #loop {joe,harry,fred,pete} {say hi, %0.} range=no

  will execute:

    say hi, joe.
    say hi, harry.
    say hi, fred.
    say hi, pete.

  A better way to execute a command a number of times without regard
  to an index, would be:

    #4 {reclaim corpse}

  which will send "reclaim corpse" to the mud 5 times.

  category: commands
  """
  loop = args["fromto"]
  command = args["comm"]
  r = args["range"]

  # split it into parts
  loopitems = loop.split(',')

  if r:
    if len(loopitems) != 2:
      exported.write_error("syntax: #loop <from,to> <command>", ses)
      return

    # remove trailing and leading whitespace and convert to ints
    # so we can use them in a range function
    ifrom = int(loopitems[0].strip())
    ito = int(loopitems[1].strip())

    # we need to handle backwards and forwards using the step
    # and need to adjust ito so the range is correctly bounded.
    if ifrom > ito:
      step = -1
    else:
      step = 1

    if ito > 0:
      ito = ito + step
    else:
      ito = ito - step

    loopitems = range(ifrom, ito, step)
    loopitems = [repr(m) for m in loopitems]
    # for i in range(ifrom, ito, step):
    #   loopcommand = command.replace("%0", repr(i))
    #   exported.lyntin_command(loopcommand, internal=1, session=ses)

  for mem in loopitems:
    mem = mem.strip()
    loopcommand = command.replace("%0", mem)
    exported.lyntin_command(loopcommand, internal=1, session=ses)

commands_dict["loop"] = (loop_cmd, "fromto comm range:boolean=true")


def math_cmd(ses, args, input):
  """
  Implements the #math command which allows you to manipulate
  variables above and beyond setting them.

  examples:
    #math {hps} {$hps + 5}

  category: commands
  """
  var = args["var"]
  ops = args["operation"]
  quiet = args["quiet"]

  try:
    rvalue = eval(ops)
    varman = exported.get_manager("variable")
    if varman:
      varman.addVariable(ses,var, str(rvalue))
    if not quiet:
      exported.write_message("math: %s = %s = %s." % (var, ops, str(rvalue)), ses)
  except Exception, e:
    exported.write_error("math: exception: %s\n%s" % (ops, e), ses)

commands_dict["math"] = (math_cmd, "var operation quiet:boolean=false")


def nop_cmd(ses, args, input):
  """
  nop stands for "no operation".  So anything after a #nop
  and before a ; (unless it's escaped) will be ignored.

  This was quite possibly the easiest command to program ever.

  category: commands
  """
  return

commands_dict["nop"] = (nop_cmd, "input=", "limitparsing=0")


def read_cmd(ses, args, input):
  """
  Reads in a file running each line as a Lyntin command.  This is the
  opposite of #write which allows you to save session settings and
  restore them using #read.

  You can also read in via the commandline when you start Lyntin:

    lyntin --read 3k

  And read can handle HTTP urls:

    lyntin --read http://lyntin.sourceforge.net/lyntinrc

    #read http://lyntin.sourceforge.net/lyntinrc

  Note: the first non-whitespace char is used to set the Lyntin
  command character.  If you use non Lyntin commands in your file,
  make sure the first one is a command char.  If not, use #nop .
  It will skip blank lines.

  If you don't specify a directory, Lyntin will look for the file
  in your datadir.

  category: commands
  """
  filename = args["filename"]

  import os
  if os.sep not in filename and not filename.startswith("http://"):
    filename = config.options["datadir"] + filename

  if filename.startswith("~"):
    filename = os.path.expanduser(filename)

  try:
    # http reading contributed by Sebastian John
    if filename.startswith("http://"):
      contents = utils.http_get(filename).split("\n")
    else:
      f = open(filename, "r")
      contents = f.readlines()
      f.close()
  except Exception, e:
    exported.write_error("read: file %s cannot be opened.\n%s" % (filename, e), ses)
    return

  contents = [m for m in contents if len(m.strip()) > 0]

  if len(contents) == 0:
    exported.write_message("read: %s had no data." % filename, ses)
    return

  c = exported.get_config("commandchar")
  if not contents[0].startswith(c):
    exported.lyntin_command("%sconfig commandchar %s" % (c, contents[0][0]), internal=1, session=ses)

  command = ""
  continued = 0
  # FIXME - should this be a config setting?
  esc = "\\"

  for mem in contents:
    mem = mem.strip()
    if len(mem) > 0:
      # handle multi-line commands
      if mem.endswith(esc):
        mem = mem.rstrip(esc)
        continued = 1
      else:
        continued = 0

    command = command + mem
    if not continued:
      exported.lyntin_command(command, internal=1, session=ses)
      command = ""

  exported.write_message("read: file %s read." % filename, ses)

commands_dict["read"] = (read_cmd, "filename")


def session_cmd(ses, args, input):
  """
  This command creates a connection to a specific mud.  When you create
  a session, that session becomes the active Lyntin session.

  To create a session to 3k.org named "3k":

    #session 3k www.3k.org 5000

  To create a session and initialize it with commands from a specific
  file:

    #session 3k www.3k.org 5000 /home/david/3k/3k.lyntin

  Then to create another session to another mud:

    #session eto gytje.pvv.unit.no 4000

  Then if 3k was your active session, you could do things on the eto
  session by prepending your command with "#eto ":

    #eto say hello

  or switch to the eto session by typing just "#eto".

  category: commands
  """
  name = args["sessionname"]
  host = args["host"]
  port = args["port"]
  filename = args["filename"]

  if not name and not host and (not port or port == -1):
    data = "Sessions available:\n"
    for mem in exported.get_active_sessions():
      data += "   %s: %r\n" % (mem.getName(), mem._socket)

    exported.write_message(data[:-1])
    return

  if not name or not host or port == -1:
    exported.write_error("syntax: #session <sesname> <host> <port>")
    return

  if name.isdigit():
    exported.write_error("session: session name cannot be all numbers.")
    return

  e = exported.myengine
  ses = e.getSession(name)

  if ses != None:
    preexistingsession = 1
  else:
    preexistingsession = 0

  if preexistingsession == 1 and ses.isConnected():
    exported.write_error("session: session of that name already exists.")
    return

  try:
    # create and register a session for this connection....
    if ses == None:
      ses = e.createSession(name)

    sock = net.SocketCommunicator(e, ses, host, port)
    ses.setSocketCommunicator(sock)

    ses._host = host
    ses._port = port

    e.changeSession(name)

    # connect to the mud...
    # this might take a while--we block here until this is done.
    sock.connect(host, port, name)

    # start the network thread
    e.startthread("network", sock.run)

  except:
    exported.write_traceback("session: had problems creating the session.")
    ses.setSocketCommunicator(None)

    if preexistingsession == 0:
      try:    e.unregisterSession(ses)
      except: pass

      try:    e.closeSession(name)
      except: pass

  # populate the session using the specified file
  if filename:
    read_cmd(ses, args, '')

commands_dict["session"] = (session_cmd, "sessionname= host= port:int=-1 filename=")


def showme_cmd(ses, args, input):
  """
  Will display {text} on your screen.  Doesn't get sent to the mud--
  just your screen.

  examples:
    #action {^%0 annihilates you!} {#showme {EJECT! EJECT! EJECT!}}

  category: commands
  """
  input = args["input"]
  if not input:
    exported.write_error("syntax: requires a message.", ses)
    return

  input = input.replace("\\;", ";")
  input = input.replace("\\$", "$")
  input = input.replace("\\%", "%")

  exported.write_message(input, ses)
     
commands_dict["showme"] = (showme_cmd, "input=", "limitparsing=0")

def wshowme_cmd(ses, args, input):
  """
  Writes the text into the named window, if the current ui supports named window
s.
  If named windows are unsupported, writes the text into the main window.

  examples:
    #action {^%0 annihilates you!} {#wshowme Alert {EJECT! EJECT! EJECT!}}

  category: commands
  """
  exported.write_message(args["text"], ses, window=args["window"])

commands_dict['wshowme'] = ( wshowme_cmd, "window= text=" )


def textin_cmd(ses, args, input):
  """
  Takes the contents of the file and outputs it directly to the mud
  without processing it (like #read does).

  If you don't specify a directory, Lyntin will look for the file in
  the datadir.

  category: commands
  """
  if (ses.getName() == "common"):
    exported.write_error("textin cannot be applied to common session.", ses)
    return

  filename = args["file"]

  if os.sep not in filename:
    filename = config.options["datadir"] + filename
   
  try:
    f = open(filename, "r")
    contents = f.readlines()
    f.close()
    for mem in contents:
      mem = utils.chomp(mem)
      ses.getSocketCommunicator().write(mem + "\n")
    exported.write_message("textin: file %s read and sent to mud." % filename, ses)

  except IOError:
    exported.write_error("textin: file %s is not readable." % filename, ses)
  except Exception, e:
    exported.write_error("textin: exception thrown %s." % e, ses)

commands_dict["textin"] = (textin_cmd, "file")


def version_cmd(ses, args, input):
  """
  Displays the version number, contact information, and web-site for
  Lyntin.

  category: commands
  """
  exported.write_message(constants.VERSION)

commands_dict["version"] = (version_cmd, "")


def write_cmd(ses, args, input):
  """
  Writes all aliases, actions, gags, etc to the file specified.
  You can then use the #read command to read this file in and
  restore your session settings.

  The quiet argument lets you specify whether you want command data
  to be written to the file so that when you read it back in with #read,
  the commands are executed quietly.

  If you don't specify a directory, it will be written to your datadir.

  Note: Windows users should either use two \\'s or use / to separate
  directory names.

  category: commands
  """
  filename = args["file"]
  quiet = args["quiet"]

  f = None

  c = exported.myengine.getConfigManager().get("commandchar")

  if os.sep not in filename:
    filename = config.options["datadir"] + filename

  data = exported.get_write_data(ses, quiet)

  if data:
    try:
      f = open(filename, "w")
      f.write(c + ("\n" + c).join(data))
      f.close()
      exported.write_message("write: file %s has been written for session %s." % 
                             (filename, ses.getName()), ses)
    except Exception:
      exported.write_traceback("write: error writing to file %s." % filename, ses)
      try:
        f.close()
      except:
        pass
    return

  exported.write_message("write: no data to write.")

commands_dict["write"] = (write_cmd, "file quiet:boolean=false")


def zap_cmd(ses, args, input):
  """
  This disconnects from the mud and closes the session.  If no
  session is specified, it will close the current session.

  category: commands
  """
  sesname = args["session"]
  if sesname:
    ses = exported.myengine.getSession(sesname)
    if ses == None:
      exported.write_error("zap: session %s does not exist." % sesname)
      return

  if exported.myengine.closeSession(ses):
    exported.write_message("zap: session %s zapped!" % ses.getName())
  else:
    exported.write_message("zap: session %s cannot be zapped!" % ses.getName())

commands_dict["zap"] = (zap_cmd, "session=")


def load():
  """ Initializes the module by binding all the commands."""
  modutils.load_commands(commands_dict)


def unload():
  """ Unloads the module by calling any unload/unbind functions."""
  modutils.unload_commands(commands_dict.keys())

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
