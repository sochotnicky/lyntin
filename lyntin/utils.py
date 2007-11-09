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
# $Id: utils.py,v 1.16 2007/11/09 18:40:54 willhelm Exp $
#########################################################################
"""
This has a series of utility functions that aren't related to classes 
in the application, but are useful in a variety of places.  They're 
not dependent on application things, so it's easier to test them.
"""
import string, re, time, types, os
import ansi, constants

# for finding non-escaped semi-colons in user input
SPLIT = ";"
SPLIT_REGEXP = re.compile(r'(?<!\\);')

TIMESPAN_REGEXP = re.compile(r"^(?P<days>\d+d)?(?P<hours>\d+h)?(?P<minutes>\d+m)?(?P<seconds>\d+s?)?$")
TIME_REGEXP1=re.compile(r"^(?P<hour>[1-9]|1[0-2])(?P<ampm>a|p)$")
TIME_REGEXP2=re.compile(r"^(?P<hour>[1-9]|1[0-2]):(?P<minute>[0-5][0-9])(:(?P<second>[0-5]\d))?(?P<ampm>a|p)?$")
TIME_REGEXP3=re.compile(r"^(?P<hour>0|1[3-9]|2[0-3]):(?P<minute>[0-5][0-9])(:(?P<second>[0-5]\d))?$")

# for finding %... variables
PVAR_REGEXP = re.compile(r'%+(-?(\d+):?-?(\d*)|:-?(\d+))')

class PriorityQueue:
  """
  This is a pretty basic priority queue.
  """
  def __init__(self):
    # holds the maps of priorities to items
    self._prioritymap = {}

    # the ordered list of items
    self._orderedlist = []

    # whether or not our orderedlist is dirty
    self._dirty = 0

  def __generateList(self):
    """
    Goes through the prioritymap and generates an orderedlist.  This
    saves cycles since it puts the ordering of the list up front
    rather than when the orderedlist is retrieved.
    """
    priorities = self._prioritymap.keys();
    priorities.sort()

    self._orderedlist = []

    for priority in priorities:
      for mem in self._prioritymap[priority]:
        self._orderedlist.append(mem)
    self._dirty = 0        

  def add(self, func, priority=constants.LAST):
    """
    Adds a function to the prioritymap and marks the PriorityQueue as
    "dirty" which means it needs to regenerate the ordered list before
    it hands it out.

    @param func: the function to call when the hook is spammed
    @type  func: function

    @param priority: the function will get this place in the call
        order.  functions with the same priority specified will get
        arbitrary ordering.  defaults to onstants.LAST.
    @type  priority: int
    """
    if not callable(func):
      exported.write_error("Function %s not callable." % repr(func))
      return

    if self._prioritymap.has_key(priority):
      self._prioritymap[priority].append(func)
    else:
      self._prioritymap[priority] = [func]

    self._dirty = 1

  def remove(self, func):
    """
    Removes a func from the priority map.

    @param func: the function to unregister
    @type  func: function
    """
    for priority in self._prioritymap.keys():
      if func in self._prioritymap[priority]:
        self._prioritymap[priority].remove(func)

        if len(self._prioritymap[priority]) == 0:
          del self._prioritymap[priority]

        break

    self._dirty = 1
  
  def getList(self):
    """
    Retrieves the list.  It might regenerate it if the prioritymap
    has been adjusted since the last time we regenerated the list.
    """
    if self._dirty == 1:
      self.__generateList()
    return self._orderedlist

  def count(self):
    """
    Returns how many functions are in the list.

    @returns: the number of functions registered
    @rtype: int
    """
    return len(self.getList())

def filter_cm(text):
  """
  Filters out ^M.  Useful for logging.

  @returns: text without ^M stuff
  @rtype: string
  """
  return text.replace("\r", "")


CHOMP_EOL = re.compile("[\r\n]+$")

def chomp(text):
  """
  Removes all CR and LF from the end of the input string.

  @param text: the text to chomp
  @type  text: string

  @returns: the text without CR or LF at the end.
  @rtype: string
  """
  global CHOMP_EOL
  return CHOMP_EOL.sub('', text)

def fixdir(d):
  """
  Takes in a directory (datadir, moduledir, ...) and fixes it (by
  adding an os.sep to the end) as well as verifies that it exists.

  If it does not exist, then it returns a None.  If it does exist,
  then it returns the adjusted directory name.

  @param d: the directory in question
  @type  d: string

  @returns: None or the fixed directory
  @rtype: string
  """
  if not os.path.exists(d):
    return None

  if len(d) > 0 and d[-1] != os.sep:
    d = d + os.sep

  return d


def http_get(url):
  """
  Retrieves the data at a given url and returns it as a big string.

  @param url: the url of the resource to retrieve
  @type  url: string

  @return: the resource at the given url
  @rtype: string

  @raises ValueError: if the url is not valid or if the resource doesn't exist
  """
  import httplib
  if url.find("http://") == -1:
    raise ValueError("This is not a valid url.")

  filename = url[7:]

  if filename.find("/") == -1:
    filename += "/"
  host, resource = filename.split("/", 1)

  resource = "/" + resource
  sock = httplib.HTTPConnection(host)
  sock.request("GET", resource)
  r = sock.getresponse()
  status = r.status
  reason = r.reason
  data = r.read()

  if status != 200:
    raise ValueError("HTTP error: %d %s" % (status, reason))

  return data


# handles regular expression syntax and flags
REG_REGEXP = re.compile("^(r\[.*?)(\$?\][Ii]*)$")

# for finding variables in the subject
SUBVAR_REGEXP = re.compile("%_?[0-9]+")

def compile_regexp(text, anchors=0, stars=0):
  """
  Takes in a string and compiles it into a regular expression.  This
  is for commands that take in strings that can be compiled either
  as a full-fledged regular expression (using Perl5 regexp syntax) or
  strings that are not regular expressions and use * as a wildcard
  character.

  @param text: the string to convert
  @type  text: string

  @param anchors: whether (1) or not (0) to deal with anchors
      in the case of a string that's not a regular expression.
      anchors are ^ and $ at the beginning and end of a string.
  @type  anchors: boolean

  @param stars: whether (1) or not (0) to deal with * wildcards
      which can match whatever
  @type  stars: boolean

  @return: the resulting regular expression
  @rtype: Re
  """
  if not text:
    return re.compile("")

  flags_bitmask = 0
  pieces = []

  if REG_REGEXP.match(text) != None:
    # this is something we should compile as a regular expression
    # without doing any finagling

    end_index = text.rfind("]")
    # handle flags issues
    flags = text[end_index+1:]
    if flags == 'i' or flags == 'I':
      flags_bitmask = re.IGNORECASE

    # handle adjusting the string
    text = text[2:end_index]

    i = 0
    match = SUBVAR_REGEXP.search(text)
    while match:
      b, e = match.span()
      pieces.append(text[i:b])
      if text[b:e].find("_") != -1:
        pieces.append("(\S+?)")
      else:
        pieces.append("(.+?)")
      i = e
      match = SUBVAR_REGEXP.search(text, i)

    pieces.append(text[i:])

  else:
    if anchors == 1:
      anchor_begin = 0
      anchor_end = 0
      if text.startswith("^"):
        anchor_begin = 1
        text = text[1:]

      if text.endswith("$"):
        anchor_end = 1
        text = text[:-1]

    if stars == 1:
      star_begin = 0
      star_end = 0
      if text.startswith("*"):
        star_begin = 1
        text = text[1:]
      if text.endswith("*"):
        star_end = 1
        text = text[:-1]

    i = 0
    match = SUBVAR_REGEXP.search(text)
    while match:
      b, e = match.span()
      pieces.append(re.escape(text[i:b]))
      if text[b:e].find("_") != -1:
        pieces.append("(\S+?)")
      else:
        pieces.append("(.+?)")

      i = e
      match = SUBVAR_REGEXP.search(text, i)

    pieces.append(re.escape(text[i:]))
    if anchors == 1:
      if anchor_begin:
        pieces.insert(0, "^")
      if anchor_end:
        pieces.append("$")

    if stars == 1:
      if star_begin:
        pieces.insert(0, "^.*")
      if star_end:
        pieces.append(".*$")

  return re.compile("".join(pieces), flags_bitmask)


def expand_text(filter, fulllist):
  """
  Returns a subset of the list that matches the given string.

  Takes a list and a string and returns a list of items in the 
  original list that match the given string.  Handles * and 
  anchors too.

  @param filter: the string to match
  @type  filter: string

  @param fulllist: the list of strings to match in
  @type  fulllist: list of strings

  @returns: the matching strings from the full list
  @rtype: list of strings
  """
  ret = []

  # if they didn't have wildcards....
  if not "*" in filter:
    for mem in fulllist:
      if mem == filter:
        ret.append(mem)

  # if they had wildcards....
  else:
    filter = re.escape(filter)

    # escaping the string will replace * with \* so we unreplace
    # it with .*
    # FIXME - this isn't quite right--we need to account for escaped
    # * stuff
    regex = re.compile("^" + filter.replace("\\*", ".*") + "$")

    for mem in fulllist:
      if regex.match(mem):
        ret.append(mem)

  return ret

def __change_command_split(newsplit):
  global SPLIT, SPLIT_REGEXP

  if not newsplit:
    SPLIT_REGEXP = None
  else:
    SPLIT_REGEXP = re.compile(r'(?<!\\)' + re.escape(newsplit))

  SPLIT = newsplit

 
def split_commands(splitchar, text):
  """
  This method takens in text and parses it into separate commands
  on the SPLIT.  It accounts for \\SPLIT as well as SPLIT in { } which 
  indicate that we shouldn't be splitting there.

  SPLIT is defined in SPLIT_REGEXP.

  If SPLIT_REGEXP is empty string or None, then this doesn't split the
  command.

  @param text: the text to split
  @type  text: string

  @return: the split text
  @rtype: list of strings
  """
  global SPLIT, SPLIT_REGEXP

  if splitchar != SPLIT:
    __change_command_split(splitchar)

  if not SPLIT_REGEXP:
    return [text]

  marker = 0
  ret = []

  matchob = SPLIT_REGEXP.search(text)
  while (matchob):
    (b, e) = matchob.span()
    # we count braces--this is a bit interesting since if the entire 
    # segment we're looking at doesn't have a full set of matched 
    # braces, we ignore this semi-colon as a split point.
    left = 0
    right = 0
    for i in range(marker, b):
      if text[i] == '{' and (i == 0 or text[i-1] != "\\"):
        left += 1
      if text[i] == '}' and (i == 0 or text[i-1] != "\\"):
        right += 1 

    count = left - right

    if count == 0:
      ret.append(text[marker:b])
      marker = e

    matchob = SPLIT_REGEXP.search(text, e)

  ret.append(text[marker:])
  return ret


def strip_braces(text):
  """
  Returns text after stripping the braces around the text.
  If the incoming text has a { at the beginning and a } at the
  end, it removes the braces.

  @param text: the string to remove braces from
  @type  text: string

  @return: the text with braces (if matched) removed
  @rtype: string
  """
  text = text.strip()
  if len(text) < 1:
    return text

  if text.startswith("{") and text.endswith("}"):
    return text[1:-1]
  return text


def parse_args(args):
  """
  Takes in a list of args and parses it out into a hashmap of arg-name 
  to value(s).

  @param args: the list of command-line arguments
  @type  args: list of strings

  @return: list of tuples of (arg, value) pairings
  @rtype: list of tuples of (string, string)
  """
  i = 0
  optlist = []
  while (i < len(args)):

    if args[i].startswith("-"):
      if (i+1 < len(args)):
        if not args[i+1].startswith("-"):
          optlist.append((args[i], args[i+1]))
          i = i + 1
        else:
          optlist.append((args[i], ""))
      else:
        optlist.append((args[i], ""))

    else:
      optlist.append(("", args[i]))

    i = i + 1
  return optlist


def _find_next_break(token, marker, wrapcount, wraplength):
  """
  Figures out where the next break should be while word-wrapping.

  @param token: the token we're working on
  @type  token: string

  @param marker: the point at which to start looking--the break is
      after this marker in the token
  @type  marker: int

  @param wrapcount: 

  @param wraplength: the line length to wrap at or under
  @type  wraplength: int

  @returns: index of where to wrap at or -1 if we don't need
      to wrap on this token
  @rtype: int
  """
  # first we check to see to see if we need to find a break
  if len(token) <= marker - wrapcount + wraplength:
    return -1

  # first we look at carriage returns--they're fun and yummy!
  x = token.rfind("\n", marker, marker - wrapcount + wraplength)
  if x != -1:
    return x

  # ok--no carriage returns.  so we try going out wraplength and working
  # to the left for spaces.
  x = token.rfind(" ", marker, marker - wrapcount + wraplength)
  if x != -1:
    return x

  return marker - wrapcount + wraplength


def wrap_text(textlist, wraplength=50, indent=0, firstline=0):
  """
  It takes a block of text and wraps it nicely.  It accounts for
  indenting lines of text, wraplengths, and wrapping around ANSI 
  colors.

  We break on carriage returns (those are easy) and if no carriage
  returns are available we break on spaces.

  If the actual line is longer than the wraplength, then we'll break
  in the line at the wraplength--this will cut words in two.

  Note: we don't expand tabs or backspaces.  Both count as one
  character.

  @param textlist: either a string of text needing to be formatted and
      wrapped, or a textlist needing to be formatted and wrapped.
  @type  textlist: string or list of strings

  @param wraplength: the maximum length any line can be.  we'll wrap
      at an index equal to or less than this length.
  @type  wraplength: int

  @param indent: how many spaces to indent every line.
  @type  indent: int

  @param firstline: 0 if we shouldn't indent the first line, 1 if we 
      should
  @type  firstline: boolean

  @returns: the wrapped text string
  @rtype: string
  """
  wrapcount = 0           # how much we've got on the line so far
  linecount = 0           # which line we're on

  if wraplength > 2:
    wraplength = wraplength - 2

  # split the formatting from the text
  if type(textlist) == types.StringType:
    textlist = ansi.split_ansi_from_text(textlist)

  for i in range(0, len(textlist)):
    # if this is a color token, we gloss over it
    if ansi.is_color_token(textlist[i]):
      continue

    # if this is a text token, then we need to factor it into the word
    # wrapping
    marker = 0

    # this handles the offset for not indenting the first line (if that's
    # the sort of thing we're into).
    if firstline:
      x = _find_next_break(textlist[i], marker, wrapcount, wraplength - indent)
    else:
      x = _find_next_break(textlist[i], marker, wrapcount, wraplength)

    # go through finding breaks and sticking in carriage returns and indents
    # and things for this text token
    while x != -1:
      # insert the carriage return, any indent, and lstrip the line as well
      # print "'" + textlist[i] + "'", len(textlist[i]), x
      if textlist[i][x] == "\n":
        if indent:
          textlist[i] = (textlist[i][:x+1] + (indent * ' ') + textlist[i][x+1:].lstrip())
        else:
          textlist[i] = (textlist[i][:x+1] + textlist[i][x+1:])
      else:
        if indent:
          textlist[i] = (textlist[i][:x+1] + '\n' + (indent * ' ') + textlist[i][x+1:].lstrip())
        else:
          textlist[i] = (textlist[i][:x+1] + '\n' + textlist[i][x+1:])

      marker = x + indent + 2
      wrapcount = 0

      x = _find_next_break(textlist[i], marker, wrapcount, wraplength - indent)

    wrapcount = len(textlist[i]) - marker + wrapcount


  # this next line joins the list with no separator
  if firstline:
    return (indent * " ") + ''.join(textlist)
  else:
    return ''.join(textlist)


def build_graph(numbers_dict):
  """
  Takes in a dict of keys to values and prints out a graph accordingly.
  """
  if not numbers_dict:
    return "No data available."

  values = numbers_dict.values()
  values.sort()
  min = values[0]
  max = values[-1]

  if min == max:
    return "All values are %d." % min

  if max < 60:
    divisor = 1
  elif max < 140:
    divisor = 2
  else:
    divisor = max / 60

  keys = numbers_dict.keys()
  keys.sort(lambda x,y: cmp(len(x), len(y)))
  maxlength = len(keys[-1])

  graph = []
  graph.append("  " + " ".ljust(maxlength+8) + "0" + ("-" * (max / divisor)) + ("%d" % max))

  keys.sort()
  for k in keys:
    v = numbers_dict[k]
    graph.append("  " + k.ljust(maxlength+1) + "- " + ("%d" % v).ljust(5) + "|" + ("=" * (v / divisor)))

  return "\n".join(graph)


def columnize(textlist, screenwidth=72, indent=0):
  """
  Takes a list of data and converts it into a series of columns and rows 
  that are evenly spaced and pretty and stuff.

  @param textlist: the list of strings to columnize
  @type  textlist: list of strings

  @param screenwidth: the maximum width to wrap against
  @type  screenwidth: int

  @param indent: the amount of spaces to indent each line
  @type  indent: int

  @return: the final formatted columnized string
  @rtype: string
  """
  if screenwidth > 2 + indent:
    screenwidth = screenwidth - 2 - indent

  SPACING = 4
  maxwidth = 0

  for mem in textlist:
    maxwidth = max(maxwidth, len(mem))

  numcols = max(1, (screenwidth + SPACING) / (maxwidth + SPACING))
  numrows = (len(textlist) + numcols - 1) / numcols

  rows = []
  # We can't just do "rows = ([],) * rows" -- need distinct lists
  for i in range(numrows): 
    rows.append([])

  idx = 0
  for mem in textlist:
    rows[idx].append(mem.ljust(maxwidth))
    idx = (idx + 1) % numrows

  rows = map(string.rstrip, map(string.join, rows))
  return (indent * " ") + ("\n" + (indent * " ")).join(rows)


def parse_timespan(timespan):
  """
  Parses a timsspan into a number of seconds.  

  @param timespan: the timespan string to parse
  @type  timespan: string

  @returns: the number of seconds in the timespan
  @rtype: int

  @raises ValueError: if the timespan is unparseable
  """
  match=TIMESPAN_REGEXP.match(timespan)

  if not match:
    raise ValueError("Invalid timespan string.")
    
  timespec = match.groupdict()

  if not timespec["days"] and not timespec["hours"] and not timespec["minutes"] and not timespec["seconds"]:
    raise ValueError("Invalid timespan string.")

  days = timespec["days"]
  if not days:
    days="0"
  elif days.endswith("d"):
    days=days[:-1]
  days=int(days)

  hours = timespec["hours"]
  if not hours:
    hours="0"
  elif hours.endswith("h"):
    hours=hours[:-1]
  hours=int(hours)

  minutes = timespec["minutes"]
  if not minutes:
    minutes="0"
  elif minutes.endswith("m"):
    minutes=minutes[:-1]
  minutes=int(minutes)
    
  seconds = timespec["seconds"]
  if not seconds:
    seconds="0"
  elif seconds.endswith("s"):
    seconds=seconds[:-1]
  seconds=int(seconds)
      
  return days * 24 * 60 * 60 + hours * 60 * 60 + minutes * 60 + seconds


def parse_time(timearg):
  """
  Parses a time into the number of seconds since the epoch.
 
  First attempts to parse as a time of day, and if that fails attempts
  to parse as a timespan.  Timespans are interpretted as times from
  time.time() (now). 

  @param timearg: the time string to parse
  @type  timearg: string

  @return: the number of seconds
  @rtype: int

  @raises ValueError: if the time string was unparseable
  """
  match = TIME_REGEXP1.match(timearg) or TIME_REGEXP2.match(timearg) or TIME_REGEXP3.match(timearg)

  if not match:
    try:
      timespan = parse_timespan(timearg)
      return time.time() + timespan
    except:
      raise ValueError("Invalid time string.")

  timespec = match.groupdict()
  currenttime = time.localtime()

  # print timespec

  hour=int(timespec.get("hour",None))
  ampm=timespec.get("ampm",None)
  if hour > 12:
    if ampm:
      raise ValueError("Invalid time string: ampm specified with hours > 12.")
    else:
      ampm="p"
  else:
    if ampm == "p":
      hour = hour + 12

  if hour < 1 or hour > 24:
    raise ValueError("Invalid time string: hours are out of range.")

  minute = timespec.get("minute",None)
  if minute == None:
    minute = 0
  else:
    minute = int(minute)
  
  second = timespec.get("second",None)
  if second == None:
    second = 0
  else:
    second = int(second)

  timetuple = (currenttime[0],currenttime[1],currenttime[2],hour,minute,second,currenttime[6],currenttime[7],currenttime[8])
  if ampm:
    increment=24
  else:
    increment=12
    
  while timetuple < currenttime:
    timetuple = timetuple[:3] + (timetuple[3] + increment,) + timetuple[4:]
  
  try:
    return time.mktime(timetuple)
  except Exception, e:
    raise ValueError("Invalid time string: %s" % e)


def convert_boolean(text):
  """
  Returns 1 if true, 0 if false, or -1 if it's not a boolean.

  @param text: the text to convert to a boolean value
  @type  text: string

  @returns: 1 if true, 0 if false, -1 if not a boolean
  @rtype: int
  """
  if text in constants.TRUE_VALUES:
    return 1
  elif text in constants.FALSE_VALUES:
    return 0
  else:
    return -1

def escape(s):
  r"""
  Takes in a string and escapes all \ (single backslash) by one level 
  (turning it into a double backslash) and all $ (single dollar sign) 
  by one level (turning it into a single backslash and a single dollar
  sign).

  @param s: the string to escape
  @type s: string

  @returns: the escaped string
  @rtype: string
  """
  s = s.replace("\\", "\\\\")

  # FIXME - this is a bit of a hack and won't work if people do
  # funky regexps that involve $ in the middle somewhere.  we
  # should probably build a regexp to do the substitution with
  # which handles the various situations.  or something along
  # those lines.
  rr = REG_REGEXP.match(s)
  if rr:
    s = rr.group(1).replace("$", "\\$") + rr.group(2)
  elif s.endswith("$"):
    s = s[:-1].replace("$", "\\$") + "$"
  else:
    s = s.replace("$", "\\$")

  return s


# --------------------------------------
# variable expansion functions
# --------------------------------------

def expand_vars(text, varmap):
  """
  Note: If you have a text string and you want the variable manager 
  to expand variables in that string according to session variables,
  use 'exported.expand_ses_vars' instead.

  The following functions are used in the command processing pipeline
  at different points:

    1. expand_vars - This expands variables in a function arbitrarily
       according to the desired expansion policy.  It should be safe to
       recusively evaluate this string and not have strings re-expanded.

    2. denest_vars - This finishes expansion of a string and should be
       called after all expansions are done.


  Note that the variablemanager's "expand" function is used for
  general expansion of text when there won't be a recursion on the
  partially expanded (but not yet denested) text.  It consists of
  chaining expand_vars and denest_vars together.

  Looks at user input and expands any variables involved using the Lyntin 
  variable expansion methodology.

  Lyntin variable expansion works by replacing all instances of $blah 
  with the appropriate variable.  Then at a later point, variables 
  preceded by multiple $ are denested one scope and lose a $.

  It returns the (un)adjusted text.

  @param text: the text to expand variables in
  @type  text: string

  @param varmap: the varname to expansion mapping
  @type  varmap: dict

  @return: the text with all variables expanded
  @rtype: string
  """
  if not ("%" in text or "$" in text) or len(text) == 0:
    return text

  varmapkeys = varmap.keys()
  # we want to sort them in order of longest first
  varmapkeys.sort(lambda x,y: cmp(len(y), len(x)))
  i = 0

  # we go through the text expanding things one at a time.
  while (i < len(text)):
    mem = text[i]
    if i != 0:
      memm1 = text[i-1]
    else:
      memm1 = None

    if (mem == "%" or mem == "$") and memm1 != "\\":
      j = i
      ccount = 0

      # count the $/% thingies first
      while j < len(text) and text[j] == mem:
        ccount += 1
        j += 1
 
      if ccount == 1 and j < len(text):
        closure = -1

        # if we're looking at a variable in the form of ${blah} then
        # we have this wonderful set of closures to play with.
        if text[j] == "{":
          closure = text.find("}", j)
          # if we didn't find a closure, then we set it to the end of
          # the text.
          if closure == -1:
            closure = len(text)-1

          # we found a { and a }, so the textfragment exists between
          # them.
          textfragment = text[j+1:closure]

          if textfragment in varmapkeys:
            repl = str(varmap[textfragment])
            text = text[:i] + repl + text[closure+1:]
            break

        else:
          textfragment = text[j:]

          for mem in varmapkeys:
            if textfragment.find(mem) == 0:
              repl = str(varmap[mem])
              text = text[:i] + repl + text[i+len(mem)+ccount:]
              break
      else:
        i += ccount

    i += 1

  #exported.write_message("utils.lyntin_expand_vars output: %s" % (text,))
  return text


# --------------------------------------
# denesting variables
# --------------------------------------

def denest_vars(text, varmap):
  """
  Replaces all the nested variables with appropriate variables.

  @param text: the string to expand variables in
  @type  text: string

  @param varmap: the varname to expansion mapping (here only in case
      a mode needs it in the future, and for consistency with the other
      var expansion commands.)
  @type varmap: dict

  @return: the text with all variables expanded
  @rtype: string
  """
  return _denest_vars_worker("$", text)


def _denest_vars_worker(varchar, text):
  """
  Handles the actual denesting for different variable types
  depending on the varchar passed in.
  """
  varchar2 = "%s%s" % (varchar, varchar)
  index = text.find(varchar2)

  while (index != -1):
    if (index == 0 or text[index] != "\\") and \
        (index == len(text)-2 or text[index+2] != varchar):
      text = text[:index] + text[index+1:]
    
    index = text.find(varchar2, index+1) 

  return text

# --------------------------------------
# placmeent variable expansion functions
# --------------------------------------

def _get_variable_value(inputsplit, var):
  """
  Takes a list and a var and figures out what the placement var
  is based on the inputsplit list.

  @param inputsplit: the input string list
  @type  inputsplit: list of strings

  @param var: the variable to retrieve
  @type  var: string

  @return: the variable expansion
  @rtype: string
  """
  # handles the 0 case
  if var == "0":
    start = 1
    end = len(inputsplit)

  # handles non splits
  elif var.find(':') == -1:
    start = int(var)
    if start == -1:
      end = len(inputsplit)
    else:
      end = start + 1

  # handles splits
  else:
    startmem,endmem = var.split(':')
    if startmem:
      start = int(startmem)
    else:
      start = 0
    if endmem:
      end = int(endmem)
    else:
      end = max(len(inputsplit),start)

  return ' '.join(inputsplit[start:end])


def _strip_placement_vars(text):
  """
  Returns a list of all the variables in a string.

  @param text: the text to strip placement vars from
  @type  text: string

  @return: list of replacement var strings
  @rtype: list of strings
  """
  global PVAR_REGEXP

  ret = []
  match = PVAR_REGEXP.search(text)
  while match:
    (b,e) = match.span()
    val = match.groups()[0]
    if val not in ret:
      ret.append(val)
    match = PVAR_REGEXP.search(text, e)
  return ret


def expand_placement_vars(input, expansion):
  """
  Takes an user input line and an alias expansion and hands it
  off to the appropriate function for evaluating the placement
  variable replacement.

  Takes an input and an expansion and replaces expansion
  variables with the components from the input.

  Returns the finalized string.

  @param input: the user's input
  @type  input: string

  @param expansion: the expansion of the alias in the input
  @type  expansion: string

  @return: the expansion with all nested_vars replaced and placement
      vars replaced
  @rtype: string
  """
  vars = _strip_placement_vars(expansion)

  if len(vars) > 0:
    varlookup = {}
    inputsplit = input.split(' ')

    # for all the variables, find what it translates to
    for mem in vars:
      if mem.find(':') < 0:
        start = int(mem)
        if start == -1:
          end = len(inputsplit)
        else:
          end = start + 1
      else:
        startmem,endmem = mem.split(':')
        if startmem:
          start = int(startmem)
        else:
          start = 0
        if endmem:
          end = int(endmem)
        else:
          end = max(len(inputsplit),start)

      varlookup[mem] = ' '.join(inputsplit[start:end])

    # run through the replacements
    vars = varlookup.keys()
    vars.sort( lambda x,y: -1 * len(x).__cmp__(len(y)) )
    
    for mem in vars:
      expansion = re.sub("(?<!%)%" + mem, varlookup[mem], expansion)

  else:
    if input.find(' ') > -1:
      expansion = expansion + ' ' + input.split(' ', 1)[1]

  expansion = _denest_vars_worker("%", expansion)

  return expansion


# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
