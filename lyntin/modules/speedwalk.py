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
# $Id: speedwalk.py,v 1.8 2007/07/24 00:39:03 willhelm Exp $
#########################################################################
"""
This module defines the speedwalking code.  Speedwalking is highly
configurable and it's actually less like speedwalking in other mudclients
and more like alias shorthand that allows you to quickly do things
a number of times.

First you want to create maps from a character or characters to
an expansion using #swdir.  Then every instance of this character/characters
gets expanded to the expansion.

For example::

  #swdir {n} {north}
  #swdir {s} {south}

"nnsss" will expand to "north;north;south;south;south".

Similarly, "2n3s" will expand to "north;north;south;sout;south".

To handle instances where certain combinations will get expanded, but we
really don't want them to be, we use #swexclude::

  #swexclude {news}
"""

# Originally written 2002 by Sebastian John

import re, string
from lyntin import manager, utils, exported
from lyntin.modules import modutils

class SpeedwalkHash:
  def __init__(self):
    self._dirs = {}
    self.compileRegexp()
    self._excludes = []
  
  def __copy__(self):
    sm = SpeedwalkManager()
    for mem in self._dirs.keys():
      sm.addDir(mem, self._dirs[mem])

    for mem in self._excludes:
      sm.addExclude(mem)
    return sm

  def clearDirs(self):
    """
    Clears all stored speedwalking dirs from the manager.
    """
    self._dirs = {}
    self.compileRegexp()
  
  def addDir(self, alias, dir):
    """
    Adds a speedwalking direction alias to the manager.
    
    @param alias: the speedwalking alias
    @type  alias: string

    @param dir: the expansion for the speedwalking alias
    @type  dir: string

    @raises ValueError: if there exists another alias where the dir is a
        substring.  for example if dir was "n" and there was an alias "ln",
        that would raise a ValueError.
    """
    for mem in self._dirs.keys():
      if mem.find(dir) != -1:
        raise ValueError, "possible ambiguity"
    self._dirs[alias] = dir
    self.compileRegexp()
  
  def removeDirs(self, alias):
    """
    Removes the speedwalking alias and only this one (no wildcard patterns
    are possible).
    
    @param alias: speedwalking aliases that match the alias will be removed
    @type  alias: string

    @returns: a list of (alias, dir) tuples of removed speedwalking aliases.
    @rtype: list of (string, string)
    """
    try:
      dir = self._dirs[alias]
      del self._dirs[alias]
    except KeyError:
      return []
    else:
      self.compileRegexp()
      return [(alias, dir)]
  
  def getDirs(self):
    """
    Returns a list of all the speedwalking aliases currently defined.
    
    @returns: the list of (alias, dir) tuples consisting of all the
        speedwalking aliases we're managing
    @rtype: list of (string, string)
    """
    dirs = self._dirs.items()
    dirs.sort()
    return dirs
  
  def getDirsInfo(self, text=""):
    """
    Returns information about the speedwalking aliases in here.
    
    This is used by #swdir to tell all the speedwalking aliases involved as
    well as #write which takes this information and dumps it to the file.
    
    @param text: the text to expand on to find aliases that the user is
        interested in
    @type  text: string
    
    @returns: list of strings where each string represents a speedwalk alias
    @rtype: list of strings
    """
    listing = self._dirs.keys()
    if text:
      listing = utils.expand_text(text, listing)
    
    listing = ["swdir {%s} {%s}" % (mem, self._dirs[mem]) for mem in listing]
    
    return listing

  def getDirsInfoMappings(self):
    l = []
    for mem in self._dirs.keys():
      l.append( { "alias": mem, "dir": self._dirs[mem] } )

    return l
  
  def getDirStatus(self):
    """
    Returns a one liner about dirs.

    @returns: a one-line about the dirs managed.
    @rtype: string
    """
    return "%d dir(s)." % len(self._dirs)
  
  def compileRegexp(self):
    """
    Compiles the actual speedwalking pattern.
    Also maintains self._aliases the default excludes.
    """
    if self._dirs:
      keys = "|".join(self._dirs.keys())
      regexp = "^(\\d*(%s))+$" % (keys)
      self._regexp = re.compile(regexp)
      self._aliases = self._dirs.values()
      self._dirs_available = self._dirs.keys()
    else:
      self._regexp = None
      self._aliases = []
      self._dirs_available = []
  
  def clearExcludes(self):
    """
    Clears the list of excludes (things we don't want to expand speedwalking
    on).
    """
    self._excludes = []
  
  def addExclude(self, exclude):
    """
    Adds a speedwalking exclude to the manager.
    
    @param exclude: the exclude to add
    @type  exclude: string
    """
    if exclude not in self._excludes:
      self._excludes.append(exclude)
  
  def removeExcludes(self, exclude):
    """
    Removes a speedwalking exclude (and only one, no wildcards or the like)
    from the manager.
    
    @param exclude: the exclude to remove (we don't accept wildcards here)
    @type  exclude: string

    @returns: list of the excludes removed
    @rtype: list of strings
    """
    badexcludes = utils.expand_text(exclude, self._excludes)

    for mem in badexcludes:
      self._excludes.remove(mem)

    return badexcludes
  
  def getExcludes(self):
    """
    Returns the exclude list we are managing.
    
    @return: the sorted list of excludes being managed
    @rtype: list of strings
    """
    self._excludes.sort()
    return self._excludes
  
  def getExcludesInfo(self, text=""):
    """
    Returns information about the speedwalking excludes in here.
    
    This is used by #swexcl to tell all the excludes involved as well as
    #write which takes this information and dumps it to the file.
    
    @param text: the text to expand on to find excludes that the user
        is interested in
    @type  text: string

    @returns: list of strings where each string represents an exclude
    @rtype: list of strings
    """
    listing = self._excludes
    if text:
      listing = utils.expand_text(text, listing)
    
    listing = ["swexclude {%s}" % mem for mem in listing]
    
    return listing
  
  def getExcludesInfoMappings(self):
    l = []
    for mem in self._excludes:
      l.append( { "exclude": mem } )
    return l

  def getExcludeStatus(self):
    """
    Returns a one-line string describing how many excludes we have.

    @returns: a one liner describing how many excludes we have
    @rtype: string
    """
    return "%d exclude(s)." % len(self._excludes)

  def clear(self):
    """
    Clears both speedwalking dir aliases and excludes.
    """
    self.clearDirs()
    self.clearExcludes()
  

class SpeedwalkManager(manager.Manager):
  def __init__(self):
    self._hashes = {}

  def clearDirs(self, ses):
    if self._hashes.has_key(ses):
      self._hashes[ses].clearDirs()

  def addDir(self, ses, alias, dir):
    if not self._hashes.has_key(ses):
      self._hashes[ses] = SpeedwalkHash()
    self._hashes[ses].addDir(alias, dir)

  def removeDirs(self, ses, alias):
    if self._hashes.has_key(ses):
      return self._hashes[ses].removeDirs(alias)
    return []

  def getDirs(self, ses):
    if self._hashes.has_key(ses):
      return self._hashes[ses].getDirs()
    return []

  def getDirsInfo(self, ses, text=""):
    if self._hashes.has_key(ses):
      return self._hashes[ses].getDirsInfo(text)
    return []

  def getStatus(self, ses):
    if self._hashes.has_key(ses):
      sdata = self._hashes[ses]
      return "%s %s" % (sdata.getDirStatus(), sdata.getExcludeStatus())
    return "0 dir(s). 0 exclude(s)."

  def addExclude(self, ses, exclude):
    if not self._hashes.has_key(ses):
      self._hashes[ses] = SpeedwalkHash()
    self._hashes[ses].addExclude(exclude)

  def removeExcludes(self, ses, exclude):
    if self._hashes.has_key(ses):
      return self._hashes[ses].removeExcludes(exclude)
    return []

  def getExcludesInfo(self, ses):
    if self._hashes.has_key(ses):
      return self._hashes[ses].getExcludesInfo()
    return []

  def getItems(self):
    return ["swdir", "swexclude"]

  def getParameters(self, item):
    if item == "swdir":
      return [ ("alias", "The speedwalk alias."),
               ("dir", "The speedwalk direction expansion.") ]
    if item == "swexclude":
      return [ ("exclude", "The word to exclude from swdir expansion.") ]

    raise ValueError("%s is not a valid item for this manager." % item)

  def getInfoMappints(self, item, ses):
    if item not in ["swexclude", "swdir"]:
      raise ValueError("%s is not a valid item for this manager." % item)

    if not self._hashes.has_key(ses):
      return []

    if item == "swdir":
      return self._hashes.getDirsInfoMappings()
    
    return self._hashes.getExcludesInfoMappings()

  def getInfo(self, ses):
    if self._hashes.has_key(ses):
      myhash = self._hashes[ses]
      return myhash.getDirsInfo() + myhash.getExcludesInfo() 
    return []

  def clear(self, ses):
    if self._hashes.has_key(ses):
      self._hashes[ses].clear()
  
  def addSession(self, newsession, basesession=None):
    if basesession:
      if self._hashes.has_key(basesession):
        sdata = self._hashes[basesession]
        for mem in sdata._dirs.keys():
          self.addDir(newsession, mem, sdata._dirs[mem])

        for mem in sdata._excludes:
          self.addExclude(newsession, mem)

  def removeSession(self, ses):
    if self._hashes.has_key(ses):
      del self._hashes[ses]

  def persist(self, args):
    """
    write_hook function for persisting the state of our session.
    """
    ses = args["session"]
    quiet = args["quiet"]

    data = self.getInfo(ses)
    if quiet:
      data = [m + " quiet={true}" for m in data]

    return data

  def userfilter(self, args):
    """
    user_filter_hook function to check for speedwalking expansion.
    """
    ses = args["session"]
    internal = args["internal"]
    verbatim = args["verbatim"]
    text = args["dataadj"]
    
    if not self._hashes.has_key(ses) or exported.get_config("speedwalk", ses) == 0 or verbatim == 1:
      return text

    sdata = self._hashes[ses]

    if not sdata._dirs or not sdata._regexp or text in sdata._excludes \
        or text in sdata._aliases or not sdata._regexp.match(text):
      return text
    
    swdirs = []
    dir = num = ""
    for char in text:
      if char.isdigit():
        num = num + char
      else:
        dir = dir + char
        if dir in sdata._dirs_available:
          if num: count = int(num)
          else: count = 1
          for i in range(count):
            swdirs.append(sdata._dirs[dir])
          dir = num = ""
    
    output = ";".join(swdirs)
    if output == text:
      return text
    else:
      # anything that gets recursed on should be recursed internally
      exported.lyntin_command(output, 1, ses)
      return None


commands_dict = {}

def swdir_cmd(ses, args, input):
  """
  This adds speedwalking aliases and tells you the current speedwalking dirs
  already registered.

  examples:
    #swdir {n} {north}
    #swdir {s} {south}
    #swdir {e} {east}
    #swdir {w} {west}
    #swdir {NE} {northeast}
    #swdir {l} {look}
    ...

  This allows you to string characters together to speedwalk:

    4e2sNE

  which using the above swdirs gets expanded to 
  "east;east;east;east;south;south;northeast" and who wants to type all 
  that?

  see also: swexclude

  category: commands
  """
  # originally written by Sebastian John
  alias = args["alias"]
  dir = args["dir"]
  quiet = args["quiet"]

  # they typed '#swdir dd*' and are looking for matching speedwalking dirs
  if not dir:
    data = exported.get_manager("speedwalk").getDirsInfo(ses, alias)
    if not data:
      data = ["swdir: no speedwalking dirs defined."]

    exported.write_message("swdirs:\n" + "\n".join(data), ses)
    return

  try:
    exported.get_manager("speedwalk").addDir(ses, alias, dir)
    if not quiet:
      exported.write_message("swdir: {%s} {%s} added." % (alias, dir), ses)
  except ValueError, e:
    exported.write_error("swdir: cannot add alias '%s': %s." % (alias, e), ses)

commands_dict["swdir"] = (swdir_cmd, "alias= dir= quiet:boolean=false")


def swexclude_cmd(ses, args, input):
  """
  Adds words that should be excluded from speedwalk expansion as well
  as tells you which words are currently being excluded.

  If you had swdirs "n", "e", "s", and "w", you might want to create
  excludes for the words "sense", "news", "sew", ...  Which are real
  words that you most likely don't want to be expanded.

  examples:
    #swexclude {end}
    #swexclude {news}

  see also: swdir

  category: commands
  """
  # originally written by Sebastian John
  excludes = args["exclude"]
  quiet = args["quiet"]

  # they typed '#swexclude'--print out all current speedwalking excludes
  if len(excludes) == 0:
    data = exported.get_manager("speedwalk").getExcludesInfo(ses)
    if not data:
      data = ["swexcl: no speedwalking excludes defined."]

    exported.write_message("swexcludes:\n" + "\n".join(data), ses)
    return

  for exclude in excludes:
    exported.get_manager("speedwalk").addExclude(ses, exclude)
    if not quiet:
      exported.write_message("swexclude: {%s} added." % exclude, ses)

commands_dict["swexclude"] = (swexclude_cmd, "exclude* quiet:boolean=false")


def unswdir_cmd(ses, args, input):
  """
  Allows you to remove swdirs.

  category: commands
  """
  func = exported.get_manager("speedwalk").removeDirs
  modutils.unsomething_helper(args, func, ses, "swdir", "swdirs")

commands_dict["unswdir"] = (unswdir_cmd, "str= quiet:boolean=false")


def unswexclude_cmd(ses, args, input):
  """
  Allows you to remove swexcludes.

  category: commands
  """
  func = exported.get_manager("speedwalk").removeExcludes
  modutils.unsomething_helper(args, func, ses, "swexclude", "swexcludes")

commands_dict["unswexclude"] = (unswexclude_cmd, "str= quiet:boolean=false")


sm = None

def load():
  """ Initializes the module by binding all the commands."""
  global sm
  modutils.load_commands(commands_dict)
  sm = SpeedwalkManager()
  exported.add_manager("speedwalk", sm)

  exported.hook_register("user_filter_hook", sm.userfilter, 80)
  exported.hook_register("write_hook", sm.persist)

  from lyntin import config
  for mem in exported.get_active_sessions():
    tc = config.BoolConfig("speedwalk", 1, 1,
         "Allows you to turn on and turn off speedwalk handling.")
    exported.add_config("speedwalk", tc, mem)

def unload():
  """ Unloads the module by calling any unload/unbind functions."""
  global sm
  modutils.unload_commands(commands_dict.keys())
  exported.remove_manager("speedwalk")

  exported.hook_unregister("user_filter_hook", sm.userfilter)
  exported.hook_unregister("write_hook", sm.persist)

  # remove configuration items for every session involved
  for mem in exported.get_active_sessions():
    exported.remove_config("speedwalk", mem)

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
