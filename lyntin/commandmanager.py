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
# $Id: commandmanager.py,v 1.8 2007/07/24 00:39:03 willhelm Exp $
#########################################################################
"""
Lyntin comes with a series of X{command}s for manipulating aliases, 
actions, highlights, and various other things.  Both the commands and 
the managers that hold the data are all defined in various Lyntin 
modules in the "modules/" subdirectory and are loaded up at Lyntin 
startup.

Lyntin has an extremely powerful argument parser that allows Lyntin
module writers to worry about the functionality of their command without
having to deal with parsing out the arguments, type-checking, 
raising exceptions with command syntax help, and data conversion.

Commands are stored internally in the "CommandManager".  They are
global to Lyntin--there are no commands that only exist in the session
they were declared in.  Commands, however, are executed in a specific
session.  When they are executed, they are given three arguments:
the session object for the session they were executed in, an argument
dictionary from the argument parser, and the exact input the user
typed.

Look at the modules/lyntincmds.py and modules/tintincmds.py modules for 
command examples.  Additionally, check out the Lyntin module repository
on http://lyntin.sourceforge.net/ for more examples.

X{default_resolver_hook}::

   Allows you to fill in values for arguments the user didn't specify 
   on the command line.  

   Arg mapping: {"session": Session, "commandname", string}

   session - the session this command was executed in.

   commandname - the name of the command that was executed

"""
import inspect, re
from lyntin import manager, exported, argparser, utils

class _CommandData:
  """
  Holds data relating to a command.  It's a helper class.
  """
  def __init__(self):
    self._name = ""
    self._func = None
    self._argparser = None
    self._fqn = ""

  def __repr__(self): return self._name
  def __str__(self): return self._name

  def setName(self, name): self._name = name
  def getName(self): return self._name
  def setNameAdjusted(self, name): self._name_adjusted = name
  def getNameAdjusted(self): return self._name_adjusted
  def setFunc(self, func): self._func = func
  def getFunc(self): return self._func
  def setArgParser(self, ap): self._argparser = ap
  def getArgParser(self): return self._argparser
  def setFQN(self, fqn): self._fqn = fqn
  def getFQN(self): return self._fqn

class CommandManager(manager.Manager):
  """ 
  The CommandManager holds a series of _CommandData objects
  and methods to manipulate and use them.  Lyntin developers
  can add their own commands to Lyntin.

  There should be one instance of the CommandManager and
  the engine should have it.  All CommandManager interaction
  should be done through the exported module.
  """
  def __init__(self, e):
    self._commands = {}
    self._engine = e

  def getCommands(self):
    """
    Returns a list of the commands we have registered.

    @return: all the commands that have been registered
    @rtype:  list of strings
    """
    return self._commands.keys()

  def addCommand(self, name, func, arguments=None, argoptions=None, helptext=""):
    """
    Registers a command.

    @param name: the name of the command to add
    @type  name: string

    @param func: the function that handles the command
    @type  func: function

    @param arguments: the argument spec to create the argparser
    @type  arguments: string

    @param argoptions: options for how the argument spec should be parsed
    @type  argoptions: string

    @param helptext: the help text for this command for the user
    @type  helptext: string

    @raise ValueError: if the function is uncallable
    @raise Exception: if the argument spec for the command is unparseable
    """
    if not callable(func):
      raise ValueError, "%s is uncallable." % name

    cd = _CommandData()

    syntaxline = ""

    # try to figure out the arguments and syntax line stuff
    if arguments != None:
      try:
        cd.setName(name)
        cd.setArgParser(argparser.ArgumentParser(arguments, argoptions))
        syntaxline = utils.wrap_text(cd.getArgParser().syntaxline, 60, 6)
      except Exception, e:
        raise Exception, "Error with arguments for command %s, (%s)" % (name,e)

    cd.setFunc(func)

    # removeCommand tests to see if the command exists already and will
    # remove it if it does.
    self.removeCommand(name)

    # toss the command thing in the dict
    self._commands[name] = cd

    # deal with the help text
    if not helptext:
      if func.__doc__:
        helptext = inspect.getdoc(func)
      else:
        helptext = "\nThis command has no help."

    if name.startswith("^"):
      cd.setNameAdjusted(name[1:])
    else:
      cd.setNameAdjusted(name)

    if syntaxline:
      commandchar = self._engine.getConfigManager().get("commandchar")
      helptext = ("syntax: %s%s %s\n" % 
             (commandchar, cd.getNameAdjusted(), syntaxline) + helptext)

    fqn = exported.add_help(cd.getNameAdjusted(), helptext)
    cd.setFQN(fqn)
        
  def removeCommand(self, name):
    """
    Removes a command (and the help text) for whatever reasons.

    @param name: the name of the command to remove
    @type  name: string

    @return: 0 if no command was found, 1 if the command was removed
        succesfully.
    @rtype: boolean
    """
    if self._commands.has_key(name):
      cd = self._commands[name]
      del self._commands[name]
      try:
        exported.remove_help(cd.getFQN())
      except:
        pass
      return 1
    return 0

  def getCommand(self, name):
    """
    Returns the function for a given command name.

    @param name: the name of the command to retrieve
    @type  name: string

    @return: the function in question or None
    @rtype:  function
    """
    if self._commands.has_key(name):
      return self._commands[name].getFunc()

    if self._commands.has_key("^" + name):
      return self._commands["^" + name].getFunc()

    # this is kind of a kluge to handle the #@ arbitrary
    # python stuff so that it can be in its own module.
    if name.startswith("@") and self._commands.has_key("@"):
      return self._commands["@"].getFunc()

    return None

  def getArgParser(self, name):
    """
    Returns the arguments parser for a given command name.

    @param name: the name of the command whose arguments should be
        retrieved
    @type  name: string

    @return: argument parsing object to convert incoming arguments
        into a dictionary to pass to the command function
    @rtype: ArgParser instance
    """
    if self._commands.has_key(name):
      return self._commands[name].getArgParser()

    return None

  def filter(self, args):
    """
    Takes in user command lines and handles commands that start
    with a Lyntin command character.

    @param args: (session, internal boolean, ..., current input text)
    @type  args: tuple

    @return: None if we handled the input, or the current input text if 
        we didn't
    @rtype:  None or string
    """
    ses = args["session"]
    internal = args["internal"]
    input = args["dataadj"]

    commandchar = self._engine.getConfigManager().get("commandchar")
    if len(input) > 1 and input.startswith(commandchar):
      input = input[1:]

      # splits out the command name from the rest of the command line
      words = input.split(" ",1)

      # We want an empty argument list if there was one, don't want
      # array out-of-bounds issues       
      if len(words) < 2: words.append("")

      # this checks to see if it's a special #@ command.
      if input.startswith("@"):
        self.getCommand("@")(ses, input.split(" "), input)
        if internal==0: ses.prompt()
        return

      # this finds the first matching command and ends there.
      commands = self.getCommands()
      commands.sort()
      for mem in commands:
        command = None
        if mem.startswith("^"):
          if re.compile(mem).search(words[0]):
            command = self.getCommand(mem)
        else:
          if mem.startswith(words[0]):
            command = self.getCommand(mem)

        if command:
          argumentparser = self.getArgParser(mem)
          if argumentparser == None:
            command(ses, input.split(" "), input)
          else:
            # for printing out the error message, we remove the ^
            # from the command name if it's there.
            fixedmem = mem
            if len(fixedmem) > 0 and fixedmem.startswith("^"):
              fixedmem = fixedmem[1:]

            resolver = exported.hook_spam("default_resolver_hook", 
                                {"session": ses, "commandname": mem}, 
                                mappingfunc=exported.query_mapper, 
                                donefunc=exported.query_done)

            try:
              argdict = argumentparser.parse(words[1], resolver)
              argdict["command"]=mem
              command(ses, argdict, input)
            except ValueError, e:
              exported.write_error("%s: %s\nsyntax: %s%s %s" % 
                                   (fixedmem, e, commandchar, fixedmem,
                                    argumentparser.syntaxline))
            except argparser.ParserException, e:
              exported.write_error("%s: %s\nsyntax: %s%s %s" % 
                                   (fixedmem, e, commandchar, fixedmem,
                                    argumentparser.syntaxline))
          if internal == 0:
            ses.prompt()
          break

      else:
        if internal == 0:
          ses.prompt()
        exported.write_error("Not a valid command: %s" % (words[0]))
      return
    return args["dataadj"]

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
