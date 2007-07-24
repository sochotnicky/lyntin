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
# $Id: testmodule.py,v 1.2 2007/07/24 00:39:03 willhelm Exp $
#########################################################################

import os, glob
import exported, modules.modutils, utils

index = __file__.rfind(os.sep)
if index == -1:
  path = "." + os.sep
else:
  path = __file__[:index]

if not path.endswith(os.sep):
  path += os.sep

commands_dict = {}

buffer = []

def capture_mud_filter(args):
  """
  Captures mud output.
  """
  buffer.append(str(args[1]) + "\n")

def capture_user_filter(args):
  """
  Captures ui output.
  """
  buffer.append(str(args[0]))

  
def runtest_cmd(ses, args, input):
  """
  Runs a test.

  Tests are essentially a commands file with some additional testing
  commands for the tester to handle.  The tester sits on the ui
  hook and copies all the data from when it begins to when it
  ends.  Then it takes this data and compares it against the benchmark
  (or if there is not benchmark, it creates one).  A test is successful
  if the benchmark equals the results of the current test run.

  It's pretty primitive--but it will work for most things.
  """
  global buffer

  test = args["test"]

  if not test:
    exported.write_message("available tests in %s:" % path)
    listing = glob.glob(os.path.join(path, "*.test"))
    listing = [mem.replace(path, "").replace(".test", "") for mem in listing]
    listing.sort()
    exported.write_message(utils.columnize(listing, indent=3))
    return

  exported.write_message("test started.")
  try:
    f = open (path + test + ".test", "r")
    lines = f.readlines()
    f.close()
  except:
    exported.write_traceback("runtest: cannot open test file %s." % test)
    return

  # bind ourselves to the hook so we capture all the data
  buffer = []
  exported.hook_register("to_user_hook", capture_user_filter)
  exported.hook_register("to_mud_hook", capture_mud_filter)

  for mem in lines:
    exported.write_message(">>> " + mem)
    exported.lyntin_command(mem, session=ses)

  exported.hook_unregister("to_user_hook", capture_user_filter)
  exported.hook_unregister("to_mud_hook", capture_mud_filter)

  results = "".join(buffer)

  try:
    f = open(path + test + ".benchmark", "r")
    benchmark = "".join(f.readlines())
    f.close()
  except:
    exported.write_traceback("runtest: cannot open benchmark--trying to save a new one.")
    try:
      f = open(path + test + ".benchmark", "w")
      f.write(results)
      f.close()
      exported.write_message("runtest: benchmark saved.")
    except:
      exported.write_traceback("runtest: could not save benchmark either.")
    return

  import difflib
  d = difflib.Differ()
  exported.write_message("----\n")
  exported.write_message("----\n")
  exported.write_message("diffing....")

  cmpresult = list(d.compare(benchmark.splitlines(1), results.splitlines(1)))
  cmpresult2 = [ mem[2:] for mem in cmpresult ]

  if cmpresult2 != benchmark.splitlines(1):
    exported.write_message("".join(cmpresult))
    exported.write_message("test failed.")
  else:
    exported.write_message("test passed.")

commands_dict["runtest"] = (runtest_cmd, "test=")

def load():
  modules.modutils.load_commands(commands_dict)


def unload():
  modules.modutils.unload_commands(commands_dict)
