#######################################################################
# This file is part of Lyntin
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: tintincmds.py,v 1.9 2003/08/28 01:46:48 willhelm Exp $
#######################################################################
import string, os
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
  exported.write_message("History:\n" + string.join(historylist, "\n"))

commands_dict["history"] = (history_cmd, "count:int=30")


def if_cmd(ses, args, input):
  """
  Allows you to do some boolean logic based on Lyntin variables
  or any Python expression.  If this expression returns a non-false
  value, then the action will be performed.

  Strings should be in single quotes:

  examples:
    #if {$myhpvar < 100} {#showme PANIC!}
    #if {$myhpvar < 100 && $myspvar < 100} {#showme PANIC!}
    #if {'$name' == 'Joe'} {#showme That joe is a jerk.}

  category: commands
  """
  # original if_cmd code contributed by Sebastian John

  expr = args["expr"]
  action = args["action"]
  elseaction = args["elseaction"]

  expr = expr.replace("&&", " and ")
  expr = expr.replace("||", " or ")

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
  data = exported.get_engine().getStatus(ses)
  data = string.join(data, "\n")
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

  A better way to execute a command a number of times without regard
  to an index, would be:

    #4 {reclaim corpse}

  which will send "reclaim corpse" to the mud 5 times.

  category: commands
  """
  loop = args["fromto"]
  command = args["comm"]

  # split it into parts
  looprange = loop.split(',')

  if len(looprange) != 2:    
    exported.write_error("syntax: #loop <from,to> <command>", ses)
    return

  # remove trailing and leading whitespace and convert to ints
  # so we can use them in a range function
  ifrom = int(looprange[0].strip())
  ito = int(looprange[1].strip())

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

  for i in range(ifrom, ito, step):
    loopcommand = command.replace("%0", repr(i))
    exported.lyntin_command(loopcommand, internal=1, session=ses)

commands_dict["loop"] = (loop_cmd, "fromto comm")


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

  If you don't specify a directory, Lyntin will look for the file
  in your datadir.

  category: commands
  """
  filename = args["filename"]

  if os.sep not in filename and not filename.startswith("http://"):
    filename = exported.get_config("datadir") + filename

  try:
    # http reading contributed by Sebastian John
    if filename.startswith("http://"):
      file = utils.http_get(filename)
    else:
      file = open(filename, "r")
  except Exception, e:
    exported.write_error("read: file %s cannot be opened.\n%s" % (filename, e), ses)
    return
    
  contents = file.readlines()

  # we want to get rid of initial blank lines and make sure
  # the file has content in it
  while len(contents) > 0 and len(contents[0].strip()) == 0:
    contents = contents[1:]

  if len(contents) == 0:
    exported.write_message("read: %s had no data." % filename, ses)
    return

  c = exported.get_config("commandchar")
  if not contents[0].startswith(c):
    exported.lyntin_command("%sconfig commandchar %s" % (c, contents[0][0]), internal=1, session=ses)

  for mem in contents:
    mem = mem.strip()
    if len(mem) > 0:
      exported.lyntin_command(mem, internal=1, session=ses)

  exported.write_message("read: file %s read." % filename, ses)

commands_dict["read"] = (read_cmd, "filename")


def session_cmd(ses, args, input):
  """
  This command creates a connection to a specific mud.  When you create
  a session, that session becomes the active Lyntin session.

  To create a session to 3k.org named "3k":

    #session 3k www.3k.org 5000

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

  e = exported.get_engine()
  ses = e.getSession(name)

  if ses != None:
    preexistingsession = 1
  else:
    preexistingsession = 0

  if preexistingsession == 1 and ses.isConnected():
    exported.write_error("session: session of that name already exists.")
    return

  try:
    # create a SocketCommunicator
    sock = net.SocketCommunicator(e)

    # create and register a session for this connection....
    if ses == None:
      ses = e.createSession(name)

    ses.setSocketCommunicator(sock)
    ses._host = host
    ses._port = port
    sock.setSession(ses)

    e.changeSession(name)

    # connect to the mud...
    # this might take a while--we block here until this is done.
    sock.connect(host, port, name)

    # start the network thread
    e.startthread("network", sock.run)

    # spam the hook
    exported.hook_spam("connect_hook", {"session": ses, "host": host, "port": port})

  except:
    exported.write_traceback("session: had problems creating the session.")
    ses.setSocketCommunicator(None)

    if preexistingsession == 0:
      try:    e.unregisterSession(ses)
      except: pass

      try:    e.closeSession(name)
      except: pass


commands_dict["session"] = (session_cmd, "sessionname= host= port:int=-1")


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


def snoop_cmd(ses, args, input):
  """
  Sets the session specified into or out of snooping mode.  When
  a session is in snoop mode, you will see mud data from that session
  regardless of what session is the current session.

  examples:
    #snoop a          -- tells you whether a is in snoop mode
    #snoop a on       -- sets snoop mode for a

  category: commands
  """
  snoopsession = args["session"]
  mode = args["mode"]

  ses = exported.get_session(snoopsession)
  if ses == None:
    exported.write_error("snoop: session '%s' does not exist." % snoopsession)
    return

  if mode != None:
    ses.setSnoop(mode)

  if ses.getSnoop() == 1:
    exported.write_message("snoop: snooping is enabled for %s." % snoopsession)
  else:
    exported.write_message("snoop: snooping is disabled for %s." % snoopsession)


commands_dict["snoop"] = (snoop_cmd, "session mode:booleanornone=")

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
    filename = exported.get_config("datadir") + filename
   
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

  c = exported.get_engine().getConfigManager().get("commandchar")

  if os.sep not in filename:
    filename = exported.get_config("datadir") + filename

  data = []
  def write_mapper(x, y):
    """
    Takes the data from x and sticks it into y so that we continue
    it all the way through.
    """
    data.append(y)
    return x

  exported.hook_spam("write_hook", {"session": ses, "quiet": quiet}, mappingfunc=write_mapper)

  if data:
    listing = []
    for mem in data:
      listing = listing + mem

    try:
      f = open(filename, "w")
      f.write(c + ("\n" + c).join(listing))
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
    ses = exported.get_engine().getSession(sesname)
    if ses == None:
      exported.write_error("zap: session %s does not exist." % sesname)
      return

  if exported.get_engine().closeSession(ses):
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
