#######################################################################
# This file is part of Lyntin
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: lyntincmds.py,v 1.1 2003/05/05 05:56:02 willhelm Exp $
#######################################################################
"""
This module holds commands that are new and unique to Lyntin.
"""
import types, re
from lyntin import net, utils, engine, __init__, exported, hooks
from lyntin.modules import modutils

commands_dict = {}

def bv(bool):
  if bool:
    return "on"
  return "off"

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

def config_cmd(ses, args, input):
  """
  Allows you to set a wide variety of options, some of which are
  session oriented and some of which are global.  Typing "#config"
  by itself will print out all the options it knows about.

  category: commands
  """
  name = args["name"]
  value = args["value"]
  quiet = args["quiet"]

  if not name:

    globmap = {"ansicolor": bv(__init__.ansicolor) + " (boolean)",
               "commandchar": __init__.commandchar + " (char)",
               "mudecho": bv(__init__.mudecho) + " (boolean)",
               "speedwalk": bv(__init__.speedwalk) + " (boolean)",
               "debugmode": bv(__init__.debugmode) + " (boolean)",
               "promptdetection": bv(__init__.promptdetection) + " (boolean)"}

    sesmap = {"ignoreactions": bv(ses._ignoreactions) + " (boolean)",
              "ignoresubs": bv(ses._ignoresubs) + " (boolean)",
              "verbatim": bv(ses._verbatim) + " (boolean)"}

    output = "Commandline:\n"
    output += _fixmap(16, __init__.options) + "\n"

    output += "Global:\n"
    output += _fixmap(16, globmap) + "\n"

    output += "Session:\n"
    output += _fixmap(16, sesmap) + "\n"

    exported.write_message(output, ses)
    return

  # set the variable to this value
  if name in ["ignoreactions", "ignoresubs", "verbatim"]:
    if not value:
      value = getattr(ses, "_%s" % name)
      exported.write_message("config: %s set to %s." % (name, bv(value)), ses)
    else:
      value = utils.convert_boolean(value)
      if value == 1 or value == 0:
        setattr(ses, "_%s" % name, value)
        if not quiet:
          exported.write_message("config: %s set to %s." % (name, bv(value)), ses)
      else:
        exported.write_error("config: '%s' is not a valid boolean value." % (value), ses)
    return

  if name in ["variablechar", "commandchar"]:
    if not value:
      value = getattr(__init__, name)
      exported.write_message("config: %s set to '%s'." % (name, value), ses)
    else:
      if len(value) == 1:
        setattr(__init__, name, value)
        if not quiet:
          exported.write_message("config: %s set to '%s'." % (name, value), ses)
      else:
        exported.write_error("config: '%s' is not a valid %s value." % (value, name), ses)
    return

  if name in ["ansicolor", "speedwalk", "debugmode", "promptdetection"]:
    if not value:
      value = getattr(__init__, name)
      exported.write_message("config: %s set to %s." % (name, bv(value)), ses)
    else:
      value = utils.convert_boolean(value)
      if value == 1 or value == 0:
        setattr(__init__, name, value)
        if not quiet:
          exported.write_message("config: %s set to %s." % (name, bv(value)), ses)
      else:
        exported.write_error("config: '%s' is not a valid boolean value." % (value), ses)
    return

  if name == "mudecho":
    if not value:
      value = __init__.mudecho
      exported.write_message("config: %s set to %s." % (name, bv(value)))
      return

    import event
    old = __init__.mudecho
    value = utils.convert_boolean(value)

    if value == 1:
      event.EchoEvent(1).enqueue() 
    else:
      event.EchoEvent(0).enqueue() 

    if not quiet:
      exported.write_message("config: %s set to %s." % (name, bv(value)), ses)
    return

  exported.write_error("config: did not recognize '%s' as an attribute." % name, ses)
      
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
  message.append(exported.get_engine().getDiagnostics())

  message.append("Hook statii:")
  data = exported.get_engine().getManager("hook").getHookStatus()
  data.sort()
  for mem in data:
    message.append(mem)

  message.append("Thread statii:")
  data = exported.get_engine().checkthreads()
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
 
  message.append("   lyntin: %s" % (__init__.VERSION[:__init__.VERSION.find("\n")]))

  message.append("Lyntin Options:")
  for mem in __init__.options.keys():
    message.append("   %s: %s" % (mem, repr(__init__.options[mem])))

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
