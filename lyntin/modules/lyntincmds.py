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
# $Id: lyntincmds.py,v 1.11 2007/07/24 00:39:03 willhelm Exp $
#########################################################################
"""
This module holds commands that are new and unique to Lyntin.
"""
import types, re
from lyntin import net, utils, engine, constants, exported, config
from lyntin.modules import modutils

commands_dict = {}

def _fixmap(w, themap):
  keys = themap.keys()
  keys.sort()
  output = []

  for mem in keys:
    if type(themap[mem]) == types.ListType:
      if len(themap[mem]) > 0:
        output.append("   %s %s" % (mem.ljust(w), themap[mem][0]))
        for mem2 in themap[mem][1:]:
          output.append((18 * " ") + mem2)
      else:
        output.append("   %s (None)" % (mem.ljust(w)))
    else:
      output.append("   %s %s" % (mem.ljust(w), themap[mem]))
  return "\n".join(output)


def bv(bool):
  if bool:
    return "on"
  return "off"

def chr_cmd(ses, args, input):
  """
  Allows you to assign arbitrary characters to variables.  For example,
  if you wanted to assign ASCII char 7 to variable ctrlG you could
  do:

    #chr {ctrlG} {7}

  Since this creates a variable, you should remove the variable with
  the unvariable command.

  Note: This won't work if you don't have the variable module loaded.

  category: commands
  """
  var = args["var"]
  ascii = args["ascii"]
  quiet = args["quiet"]

  vm = exported.get_manager("variable")

  if not vm:
    exported.write_error("chr: no variable manager found.")
    return

  if ascii < 0 or ascii > 127:
    exported.write_error("chr: ascii argument out of range of 0 to 127.")
    return

  vm.addVariable(ses, var, chr(ascii))
  if not quiet:
    exported.write_message("chr: variable %s added." % var)

commands_dict["chr"] = (chr_cmd, "var ascii:int quiet:boolean=false")


def config_cmd(ses, args, input):
  """
  Allows you to view and change configuration options that affect
  how Lyntin functions.  Configuration options can be session
  oriented or global to all of Lyntin.

  examples: 
    #config
        displays global configuration and session configuration for the 
        current session

    #a #config
        displays global configuration and session configuration for the 
        session named 'a'

    #config ansicolor
        displays information about the mudecho configuration option

    #config ansicolor on
        sets the ansicolor configuration option to on

  category: commands
  """
  name = args["name"]
  value = args["value"]
  quiet = args["quiet"]

  c = exported.myengine.getConfigManager()

  # if they didn't specify a name, then we print out all the
  # configuration stuff for general and this session
  if not name:
    general = c.getConfigItems(None)
    globmap = {}
    for mem in general:
      globmap[mem._name] = mem.toString()

    seslisting = c.getConfigItems(ses)
    sesmap = {}
    for mem in seslisting:
      sesmap[mem._name] = mem.toString()

    output = "Commandline:\n"
    output += _fixmap(16, config.options) + "\n"

    output += "Global:\n"
    output += _fixmap(16, globmap) + "\n"

    output += "Session:\n"
    output += _fixmap(16, sesmap) + "\n"

    exported.write_message(output, ses)
    return

  # try to find a session item first
  ci = c.getConfigItem(name, ses)
  if not ci:
    ci = c.getConfigItem(name)

  if not ci:
    exported.write_error("config: config manager does not recognize %s as a config item." % name)
    return


  if not value:
    # we print out everything we know about this config item.
    output = "config: %s\n\ncurrent value: %s\n\n%s\n" % \
             (name, ci.toString(), utils.wrap_text(ci._description, wraplength=60))
    exported.write_message(output)
    return


  try:
    try:
      c.change(name, value, ses)
    except:
      c.change(name, value)
    exported.write_message("config: %s set to %s." % (name, value), ses)
  except Exception, e:
    exported.write_error(e)

commands_dict["config"] = (config_cmd, "name= value= quiet:boolean=false")
  
def grep_cmd(ses, args, input):
  """
  Similar to the unix grep command, this allows you to extract 
  information from the session's data buffer using regular expressions.

  It prints matching lines in their entirety.

  examples:
    #grep {says:} 1000

    Greps the last 1000 lines of the databuffer for lines that have
    "says:" in them.

  category: commands
  """
  if (ses.getName() == "common"):
    exported.write_error("grep cannot be applied to common session.", ses)
    return

  pattern = args["pattern"]
  size = args["size"]
  context = args["context"]
  buffer = ses.getDataBuffer()

  ret = []
  cpattern = re.compile(pattern)
  for i in range(max(len(buffer)-size,0), len(buffer)):
    mem = buffer[i]
    if cpattern.search(mem):
      if context > 0:
        mem = []
        if i > 0:
          bound = i - context
          if bound < 0: bound = 0
          for j in range(bound, i):
            mem.append("  " + buffer[j])

        mem.append("+ " + buffer[i])

        if i < len(buffer):
          bound = i+context+1
          if bound > len(buffer)-1: bound = len(buffer)-1
          for j in range(i+1, bound):
            mem.append("  " + buffer[j])
        mem = "".join(mem)

      ret.append(mem)

  if context == 0:
    splitter = ""
  else:
    splitter = "---\n"
  exported.write_message("grep %s results:\n%s" % (pattern, splitter.join(ret)), ses)

commands_dict["grep"] = (grep_cmd, "pattern size:int=300 context:int=0")


def diagnostics_cmd(ses, args, input):
  """
  This is very useful for finding out all the information about Lyntin
  while it's running.  This will print out operating system information,
  Python version, what threads are running (assuming they're registered
  with the ThreadManager), hooks, functions connected to hooks, and
  #info for every session.  It's very helpful in debugging problems that
  are non-obvious or are platform specific.  It's also invaluable in
  bug-reporting.

  It can take a filename argument and will copy the #diagnostics output
  to that file.  This allows you easier method of submitting diagnostics
  output along with bug reports.

  Note: Windows users should either use two \\'s or use / to separate
  directory names.

  category: commands
  """
  import os, sys
  message = []
  message.append("Diagnostics:")
  message.append(exported.myengine.getDiagnostics())

  message.append("Hook statii:")
  data = exported.myengine.checkHooks()
  data.sort()
  for mem in data:
    message.append(mem)

  message.append("Thread statii:")
  data = exported.myengine.checkthreads()
  data.sort()
  for mem in data:
    message.append(mem)
      
  message.append("OS/Python information:")
  try: 
    message.append("   sys.version: %s" % sys.version)
  except:
    message.append("   sys.version not available.")

  try: 
    message.append("   os.name: %s" % os.name)
  except:
    message.append("   os.name not available.")
 
  message.append("   lyntin: %s" % (constants.VERSION[:constants.VERSION.find("\n")]))

  message.append("Lyntin Options:")
  for mem in config.options.keys():
    message.append("   %s: %s" % (mem, repr(config.options[mem])))

  exported.write_message("\n".join(message))
  exported.write_message("This information can be dumped to a "
        "file by doing:\n   #diagnostics dumpfile.txt")

  logfile = args["logfile"]
  if logfile:
    import time
    try:
      f = open(logfile, "w")
      f.write("This file was created on: %s" % time.asctime())
      f.write(os.linesep + os.linesep)
      f.write(os.linesep.join(message))
      f.close()
      exported.write_message("diagnostics: written out to file %s." % logfile)
    except Exception, e:
      exported.write_error("diagnostics: Error writing to file %s. %s" 
                            % (logfile, e))

commands_dict["diagnostics"] = (diagnostics_cmd, "logfile=")


def raw_cmd(ses, args, input):
  """
  Sends input straight to the mud.

  category: commands
  """
  if (ses.getName() == "common"):
    exported.write_error("raw: cannot send raw data to the common session.", ses)
    return

  ses.writeSocket(args["input"] + "\n")
  
commands_dict["raw"] = (raw_cmd, "input=", "limitparsing=0")


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
