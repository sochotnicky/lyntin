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
# $Id: scheduler.py,v 1.5 2007/07/24 00:39:03 willhelm Exp $
#########################################################################
"""
This module defines the ScheduleManager which manages scheduling 
events for Lyntin.  It's pretty intense.  It handles both events
oriented around "lyntin time" (what the current Lyntin tick is)
as well as "real time" (what time it really is).  Scheduled
events can be lyntin commands as well as functions with 
arguments.

This module implements the #schedule and #unschedule commands
as well as the completely re-implemented #tick* suite of
commands.
"""
import time
from lyntin import exported, manager, utils, event
from lyntin.modules import modutils

myscheduler = None
commands_dict = {}

def truncate(text, maxwidth):
  if len(text) > maxwidth:
    text = text[:maxwidth] + "..."
  return text

class SchedEvent:
  """ 
  Holds event data as well as handles representation of the data.
  """
  def __init__(self, offset, ses, cmd, repeat=0, quiet=0, tag="none"):
    self._id = "-1"
    self._tag = tag
    self._offset = offset
    self._ses = ses
    self._cmd = cmd
    self._repeat = repeat
    self._quiet = quiet
    self._args = []
    self._xargs = {}

  def __repr__(self):
    if self._repeat == 0:
      return truncate("%s [%s] %d {%s}" % (self._id, self._ses._name, self._offset, self._cmd), 60)
    return truncate("%s [%s] %d(r) {%s}" % (self._id, self._ses._name, self._offset, self._cmd), 60)

class SchedTimeEvent:
  """
  Holds event data as well as handles representation of the data.

  The only difference between this and the SchedEvent is that this
  displays the offset as if it were a real date/time (which it is).
  """
  def __init__(self, offset, ses, cmd, repeat=0, quiet=0, tag="none"):
    self._id = "-1"
    self._tag = tag
    self._offset = offset
    self._ses = ses
    self._cmd = cmd
    self._repeat = repeat
    self._quiet = quiet
    self._args = []
    self._xargs = {}
    self._time = ""

  def __repr__(self):
    return truncate("%s [%s] %s {%s}" % (self._id, self._ses._name, time.strftime("%d %b %H:%M:%S", time.localtime(self._offset)), self._cmd), 60)



class Scheduler:
  """
  Manages scheduled data.
  """
  def __init__(self):
    # mapping of tick time -> SchedEvent list
    self._events = {}

    # mapping of seconds since epoch -> SchedEvent list
    self._tevents = {}

    # the current Lyntin tick
    self._current_tick = 0

    # the event id index
    self._eid = 0

  def startup(self):
    exported.hook_register("timer_hook", self.timeUpdate)

  def shutdown(self):
    exported.hook_unregister("timer_hook", self.timeUpdate)
 
  def getEvents(self, ses):
    """
    Returns a list of the events for a given session.

    @param ses: the session to look at
    @type  ses: Session

    @returns: the list of session information
    @rtype: list of strings
    """
    output = []
    for listing in self._events.values():
      for mem in listing:
        if mem._ses == ses:
          output.append(repr(mem))

    for listing in self._tevents.values():
      for mem in listing:
        if mem._ses == ses:
          output.append(repr(mem))

    output.sort()
    return output

  def getEventById(self, id):
    """
    Finds an event by id or by tag.  It returns the event as well
    as adding a _next_tick attribute to the event telling you
    when the event is next scheduled to execute.  Sneaky, eh?

    @param id: the id or tag of the event to find
    @type  id: string

    @returns: the SchedEvent instance or None
    @rtype: SchedEvent
    """
    for key in self._events.keys():
      listing = self._events[key]
      for mem in listing:
        if mem._id == id or mem._tag == id:
          mem._next_tick = key
          return mem

    for key in self._tevents.keys():
      listing = self._tevents[key]
      for mem in listing:
        if mem._id == id or mem._tag == id:
          mem._next_tick = key
          return mem

    return []

  def removeById(self, id):
    """
    Removes an event from the scheduler by id or by tag or by '*'.

    @param id: the id or tag of the event to remove
    @type  id: string

    @returns: a list of the events unscheduled
    @rtype: list of strings
    """
    output = []
    for listing in self._events.values():
      for mem in listing:
        if id == '*' or mem._id == id or mem._tag == id:
          output.append(repr(mem))
          listing.remove(mem)

    for listing in self._tevents.values():
      for mem in listing:
        if id == '*' or mem._id == id or mem._tag == id:
          output.append(repr(mem))
          listing.remove(mem)

    output.sort()
    return output

  def addEvent(self, tick, sevent, real=0, id=-1):
    """
    Adds an event to the scheduler.

    @param tick: the tick that this event kicks off at
    @type  tick: int

    @param sevent: the SchedEvent object
    @type  sevent: SchedEvent

    @param real: whether or not this is a real event (tick is seconds since
        epoch) or a regular event (tick is an offset of seconds from now)
    @type  real: int
    """
    if id == -1:
      eid = self._eid
      self._eid += 1
    else:
      eid = id

    sevent._id = str(eid)

    if real == 0:
      eventdict = self._events
    else:
      eventdict = self._tevents

    if eventdict.has_key(tick):
      eventdict[tick].append(sevent)
    else:
      eventdict[tick] = [sevent]

  def timeUpdate(self, args):
    """
    This gets called by the timer_hook in the engine every
    second.  It goes through and executes all the events for this
    Lyntin tick as well as events who are supposed to execute at
    this seconds since the epoch or before.

    It also handles tossing events back in the schedule if they
    need repeating.
    """
    tick = args["tick"]

    events = []

    if self._events.has_key(tick):
      for mem in self._events[tick]:
        events.append(mem)

      del self._events[tick]

    self._current_tick = tick

    # we want to execute for this second and any previous seconds
    # that have been missed.
    sec = int(time.time())
    keys = self._tevents.keys()
    keys = [mem for mem in keys if mem < sec]
    for key in keys:
      for mem in self._tevents[key]:
        events.append(mem)
      del self._tevents[key]

    # go through and execute all the events we've found
    for mem in events:
      if not mem._quiet:
        exported.write_message("Executing %r." % mem)

      if not callable(mem._cmd):
        exported.lyntin_command(mem._cmd, internal=1, session=mem._ses)
      else:
        try:
          mem._cmd(*mem._args, **mem._xargs)
        except:
          exported.write_traceback("exception kicked up while trying to execute event.")

      # handles repeating events
      if mem._repeat == 1:
        self.addEvent(tick + mem._offset, mem, id=mem._id)

def schedule_cmd(ses, args, input):
  """
  With no arguments lets you view the scheduled events.

    lyntin: Scheduled events:
    lyntin: 1 [a] 200 {#showme Will is super duper!}

  First column is the event id.
  Second column is the session it's in.
  Third column is the tick offset or time it's going to kick off at.
  Fourth column is the command to execute.

  With arguments it creates a scheduled event to kick off (and 
  possibly repeat) at TICK seconds from now at which point it will 
  execute EVENT which could be any valid user input.

  examples:

    #schedule {5} {#showme blah}

  will kick off 5 ticks from now (a tick is approx one second) and
  will execute "#showme blah".

    #schedule {1m30s} {#showme blah}

  will kick off in 1 minute and 30 seconds.

    #schedule {10} {#showme blah} {true}

  will kick off every 10 seconds.

  category: commands
  """
  global myscheduler

  tick = args["tick"]
  cmd = args["event"]
  quiet = args["quiet"]
  repeat = args["repeat"]

  if not tick:
    output = myscheduler.getEvents(ses)
    if not output:
      exported.write_message("schedule: there are no scheduled events.")
      return

    if not quiet:
      exported.write_message("scheduled events:\n" + "\n".join(output))
    return

  setimespan = 0
  setime = 0
  try:
    setimespan = utils.parse_timespan(tick)
  except:
    try:
      setime = utils.parse_time(tick)
    except:
      exported.write_error("schedule: %s is not a valid time or timespan." % tick)
      return

  if setimespan != 0:
    sevent = SchedEvent(setimespan, ses, cmd, repeat, quiet)
    tick = setimespan + myscheduler._current_tick
    myscheduler.addEvent(tick, sevent)

  else:
    repeat = 0
    sevent = SchedTimeEvent(setime, ses, cmd, repeat, quiet)
    myscheduler.addEvent(setime, sevent, real=1)

  if not quiet:
    exported.write_message("schedule: event scheduled: %r" % sevent)

commands_dict["schedule"] = (schedule_cmd, "tick= event= repeat:boolean=false quiet:boolean=false")


def unschedule_cmd(ses, args, input):
  """
  Allows you to remove a scheduled event by id.  To remove all events
  scheduled use *.  To see a list of the events and ids for the current 
  session use the #sched command.

  examples:
    #unschedule *
    #unschedule 44

  category: commands
  """
  global myscheduler

  id = args["str"]
  quiet = args["quiet"]

  if id:
    ret = myscheduler.removeById(id)
    if not ret:
      if id == "*":
        exported.write_error("unschedule: no scheduled events to unschedule.")
      else:
        exported.write_error("unschedule: id '%s' is not valid." % id)
      return
    if not quiet:
      exported.write_message("events removed:\n%s" % "\n".join(ret))
    return
 
  exported.write_message("not implemented yet.")

commands_dict["unschedule"] = (unschedule_cmd, "str= quiet:boolean=false")


# this is a dict holding the DEFAULT_TICKER values.  we copy
# this whenever we don't have them.
DEFAULT_TICKER = {
      "len": 3,
      "warn_len": 2,
      "enabled": 0
   }

def _tickfunc(ses):
  """
  Handles executing the command or displaying a message to the
  user.

  @param ses: the Session instance
  @type  ses: Session
  """
  am = exported.get_manager("alias")
  if am:
    tickaction = am.getAlias(ses, "TICK!!!")
  if not tickaction:
    tickaction = am.getAlias(ses, "TICK")

  if tickaction:
    event.InputEvent(tickaction, internal=1, ses=ses).enqueue()
  else:
    exported.write_message("TICK!!!")

def _tickwarnfunc(ses, warnlen): 
  """
  Handles executing the command or displaying a message to the
  user.

  @param ses: the Session instance
  @type  ses: Session

  @param warnlen: the warning length
  @type  warnlen: int
  """
  am = exported.get_manager("alias")
  if am:
    tickaction = am.getAlias(ses, "TICKWARN!!!")
  if not tickaction:
    tickaction = am.getAlias(ses, "TICKWARN")

  if tickaction:
    event.InputEvent(tickaction, internal=1, ses=ses).enqueue()
  else:
    exported.write_message("ticker: %d seconds to tick!" % warnlen)


def _addtickevents(ses):
  """
  Utility function for adding the tick and tickwarn events to 
  the schedule.

  @param ses: the Session instance
  @type  ses: Session
  """
  global myscheduler

  tick_tagname = ses.getName() + "tick"
  tickwarn_tagname = ses.getName() + "tickwarn"

  # build the tick event, figure out when it should start,
  # and add it to the schedule
  sevent = SchedEvent(ses._ticker["len"], ses, _tickfunc, repeat=1, 
                      quiet=1, tag=tick_tagname)
  sevent._args = [ses]
  tick = myscheduler._current_tick + ses._ticker["len"]
  myscheduler.addEvent(tick, sevent)

  # build the tickwarn event, figure out when it should start,
  # and add it to the schedule
  warnsevent = SchedEvent(ses._ticker["len"], ses, _tickwarnfunc, 
                          repeat=1, quiet=1, tag=tickwarn_tagname)
  warnsevent._args = [ses, ses._ticker["warn_len"]]
  tick = tick - ses._ticker["warn_len"]
  myscheduler.addEvent(tick, warnsevent)


def _removetickevents(ses):
  """
  Utility function for removing the tick events (tick and tickwarn)
  for a given session.  We return all the events that we've removed
  so the caller knows whether there were events to remove or not.

  @param ses: the Session instance
  @type  ses: Session

  @returns: the SchedEvents removed
  @rtype: list of SchedEvents
  """
  global myscheduler

  sesname = ses.getName()

  # remove the tick and tickwarn events by id
  tick_tagname = sesname + "tick"
  tickwarn_tagname = sesname + "tickwarn"

  ret = myscheduler.removeById(tick_tagname)
  ret2 = myscheduler.removeById(tickwarn_tagname)
  return ret + ret2
 
def tick_cmd(ses, args, input):
  """
  Displays the number of seconds left before this session's
  ticker ticks.

  When a tick happens, it will look for a TICK!!! alias then a TICK
  alias.  Finding none, it will print TICK!!! to the ui.

  When a tickwarning happens, it will look for a TICKWARN!!! alias
  and then a TICKWARN alias.  Finding none, it will print a tickwarning
  message to the ui.

  This allows you to perform an event every x number of seconds.

  see also: tick, tickon, tickoff, ticksize, tickwarnsize

  category: commands
  """
  global myscheduler
  if not hasattr(ses, "_ticker"):
    ses._ticker = DEFAULT_TICKER.copy()

  if ses._ticker["enabled"] == 1:
    tick = myscheduler._current_tick
    sevent = myscheduler.getEventById(ses.getName() + "tick")
    delta = sevent._next_tick - tick

    exported.write_message("tick: next tick in %d seconds." % delta, ses)
  else:
    exported.write_message("tick: ticker is not enabled.", ses)

commands_dict["tick"] = (tick_cmd, "")


def tickon_cmd(ses, args, input):
  """
  Turns on the ticker for this session.

  see also: tick, tickon, tickoff, ticksize, tickwarnsize

  category: commands
  """
  global myscheduler
  if not hasattr(ses, "_ticker"):
    ses._ticker = DEFAULT_TICKER.copy()

  tick_tagname = ses.getName() + "tick"
  tickwarn_tagname = ses.getName() + "tickwarn"

  # quick check to make sure there isn't already a tick event
  # for this session
  if myscheduler.getEventById(tick_tagname):
    exported.write_error("tickon: ticker is already enabled.", ses)
    return

  _addtickevents(ses)
  ses._ticker["enabled"] = 1

  exported.write_message("tickon: session %s ticker enabled." % ses.getName(), ses)
 
commands_dict["tickon"] = (tickon_cmd, "")


def tickoff_cmd(ses, args, input):
  """
  Turns off the ticker for this session.

  see also: tick, tickon, tickoff, ticksize, tickwarnsize

  category: commands
  """
  _removetickevents(ses)
  ses._ticker["enabled"] = 0

  exported.write_message("tickoff: session %s ticker disabled." 
                         % ses.getName(), ses)

commands_dict["tickoff"] = (tickoff_cmd, "")


def ticksize_cmd(ses, args, input):
  """
  Sets and displays the number of seconds between ticks for this
  session.

  examples:
    #ticksize
    #ticksize 6
    #ticksize 1h2m30s

  see also: tick, tickon, tickoff, ticksize, tickwarnsize

  category: commands
  """
  if not hasattr(ses, "_ticker"):
    ses._ticker = DEFAULT_TICKER.copy()

  size = args["size"]

  if size == 0:
    exported.write_message("ticksize: ticksize is %d seconds." % 
                           ses._ticker["len"], ses)
    return

  ses._ticker["len"] = size

  ret = _removetickevents(ses)
  if ret:
    _addtickevents(ses)
 
  exported.write_message("ticksize: tick length set to %s." % str(size), ses)

commands_dict["ticksize"] = (ticksize_cmd, "size:timespan=0")


def tickwarnsize_cmd(ses, args, input):
  """
  Sets and displays the number of seconds you get warned before a
  Tick actually happens.

  examples:
    #tickwarnsize
    #tickwarnsize 6
    #tickwarnsize 0

  see also: tick, tickon, tickoff, ticksize, tickwarnsize

  category: commands
  """
  if not hasattr(ses, "_ticker"):
    ses._ticker = DEFAULT_TICKER.copy()

  size = args["size"]

  if size == 0:
    exported.write_message("tickwarnsize: tickwarnsize is %d seconds." % 
                           ses._ticker["warn_len"], ses)
    return

  if size > ses._ticker["len"]:
    exported.write_error("tickwarnsize: tickwarn length cannot be >= " +
                         "to ticksize.\nCurrent ticksize is %s." %
                         ses._ticker["len"], ses)
    return

  ses._ticker["warn_len"] = size

  ret = _removetickevents(ses)
  if ret:
    _addtickevents(ses)
 
  exported.write_message("tickwarnsize: tickwarn length set to %s." %
                         str(size), ses)

commands_dict["tickwarnsize"] = (tickwarnsize_cmd, "size:timespan=0")


def load():
  global myscheduler

  myscheduler = Scheduler()
  myscheduler.startup()
  modutils.load_commands(commands_dict)

def unload():
  global myscheduler

  myscheduler.shutdown()
  myscheduler = None
  modutils.unload_commands(commands_dict)
