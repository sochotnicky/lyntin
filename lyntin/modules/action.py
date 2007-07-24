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
# $Id: action.py,v 1.24 2007/07/24 00:39:03 willhelm Exp $
#########################################################################
"""
This module defines the ActionManager which handles managing actions 
(triggers), matching triggers in mud_data and executing the resulting
action on behalf of the user for that session.

The ActionManager contains an ActionData object for every session that
has actions.

An action consists of:

1. the trigger statement
2. the response statement
3. the priority of the action
4. whether or not the action is a onetime action
5. optional action tag - the name of the action or action group

We also store a compiled regular expression of the trigger which
we use on incoming mud_data to check for triggered actions.

The compiled regular expressions gets recompiled every time a variable
changes--this allows us to handle Lyntin variables in the action trigger
statements.
"""
import re
from lyntin import manager, utils, event, exported, ansi
from lyntin.modules import modutils


# the placement variable regular expression
VARREGEXP = re.compile('%_?(\d+)')

class ActionData:
  def __init__(self, ses):
    self._actions = {}
    self._ses = ses
    self._disabled = {}
    self._actionlist = None

  def addAction(self, trigger, response, color=0, priority=5, onetime=0, tag=None):
    """
    Compiles a trigger pattern and adds the entire action to the
    hash.

    @param trigger: the trigger pattern
    @type  trigger: string

    @param response: what to do when the trigger pattern is found
    @type  response: string

    @param color: whether (1) or not (0) we try matching the line with
        the ansi colors still in it.  (i.e. if color==0, we filter the
        ansi colors out before matching)
    @type  color: boolean

    @param priority: the priority to run this action at.  actions
        are sorted by priority then by the trigger statement when
        we go to check for triggered actions.  default is 5
    @type  priority: int

    @param onetime: if the trigger is found, should this action then
        get removed after the response is executed
    @type  onetime: boolean

    @return: 1
    @rtype:  boolean
    """
    expansion = exported.expand_ses_vars(trigger, self._ses)
    if not expansion:
      expansion = trigger
    compiled = utils.compile_regexp(expansion, 1)
    self._actions[trigger] = (trigger, compiled, response, color, priority, onetime, tag)
    self._actionlist = None       # invalidating action list
    return 1

  def _recompileRegexps(self):
    """
    When a variable changes, we go through and recompile all the
    regular expressions for the actions in this session.
    """
    for mem in self._actions.keys():
      (trigger, compiled, response, color, priority, onetime, tag) = self._actions[mem]
      expansion = exported.expand_ses_vars(trigger, self._ses)
      if not expansion:
        expansion = trigger

      compiled = utils.compile_regexp(expansion, 1)

      self._actions[trigger] = (trigger, compiled, response, color, priority, onetime, tag)

  def clear(self):
    """
    Clears all the stored actions from the action manager.
    """
    self._actions.clear()
    self._disabled = {}
    self._actionlist = None

  def getInfoMappings(self):
    l = []
    for key in self._actions.keys():
      mem = self._actions[key]
      l.append( { "trigger": mem[0],
                  "action": mem[2],
                  "tag": mem[6],
                  "color": mem[3],
                  "priority": mem[4],
                  "onetime": mem[5] } )
    return l

  def removeActions(self, text, mytag=None):
    """
    Removes actions that match the given text and have given tag 
    from the list and returns the list of actions that were removed
    so the calling function knows what actually happened.

    @param text: all actions that match this text pattern will 
        be removed.  the text pattern is "expanded" by 
        "utils.expand_text"
    @type  text: string

    @param mytag: all actions with given tag will be removed.
    @type  mytag: string

    @return: list of tuples (trigger, response, tag) of the action
        that were removed.
    @rtype: (string, string, string)
    """
    actions = self._actions
    keys = []
    if text:
      keys = utils.expand_text(text, actions.keys())
    elif mytag:  
      keys = actions.keys()

    ret = []
    for mem in keys:
      (trigger, compiled, response, color, priority, onetime, tag) = actions[mem]
      if not mytag or mytag == tag:
        ret.append((trigger, response, tag))
        del actions[mem]

    self._actionlist = None       # invalidating action list

    return ret

  def checkActions(self, text):
    """
    Checks to see if text triggered any actions.  Any resulting 
    actions will get added as an InputEvent to the queue.

    @param text: the data coming from the mud to check for triggers
    @type  text: string
    """
    # FIXME - make sure this works even when lines are broken up.

    actionlist = self._actionlist
    if not actionlist:
      actionlist = filter(lambda x: not self._disabled.has_key(x[6]),
                          self._actions.values())
      actionlist.sort(lambda x,y:cmp(x[3], y[3]))
      self._actionlist = actionlist

    colorline = utils.filter_cm(text)
    nocolorline = ansi.filter_ansi(colorline)

    # go through all the lines in the data and see if we have
    # any matches
    for (action, actioncompiled, response, color, priority, onetime, tag) in actionlist:
      if color:
        match = actioncompiled.search(colorline)
        line = colorline
      else:
        match = actioncompiled.search(nocolorline)
        line = nocolorline

      if match:
        # for every match we figure out what the expanded response
        # is and add it as an InputEvent in the queue.  the reason
        # we do a series of separate events rather than one big
        # event with ; separators is due to possible issues with 
        # braces and such in malformed responses.

        # get variables from the action
        actionvars = get_ordered_vars(action)

        # fill in values for all the variables in the match
        varvals = {}
        for i in xrange(len(actionvars)):
          varvals[actionvars[i]] = match.group(i+1)

        # add special variables
        varvals['a'] = line.replace(';', '_')
            
        # fill in response variables from those that
        # matched on the trigger
        response = utils.expand_vars(response, varvals)

        # event.InputEvent(response, internal=1, ses=self._ses).enqueue()
        try:
          exported.lyntin_command(response, internal=1, session=self._ses)
        except:
          exported.write_traceback()

        if onetime and self._actions.has_key(action):
          del self._actions[action]
          self._actionlist = None           # invalidate the list


  def getStatus(self):
    """
    Returns a one-liner as to how many actions we have.

    @return: a description of the status of this manager
    @rtype:  string
    """
    return "%d action(s)." % len(self._actions)

  def getInfo(self, text="", tag=None):
    """
    Returns information about the actions in here.

    This is used by #action to tell all the actions involved
    as well as #write which takes this information and dumps
    it to the file.

    @param text: the text to expand to find actions the user
        wants information about.
    @type  text: string

    @param tag: the tag which to find actions for.
    @type  tag: string

    @return: a list of strings where each string represents an action
    @rtype: list of strings
    """
    listing = self._actions.keys()
    if text:
      listing = utils.expand_text(text, listing)

    data = []
    for mem in listing:
      actup = self._actions[mem]
      
      if not tag or actup[6] == tag:
        data.append("action {%s} {%s} color={%d} priority={%d} onetime={%s} tag={%s}" % 
                (utils.escape(mem), utils.escape(actup[2]), actup[3], actup[4], actup[5], actup[6]))

    return data

  def getDisabledInfo(self, tag=None):
    """
    Returns information about disabled tags.

    @param tag: the tag which to find actions for.
    @type  tag: string

    @return: a list of strings where each string represents an action
    @rtype: list of strings
    """
    data = []
    for mem in self._disabled.keys():
      if not tag or mem == tag:
        data.append("disable tag={%s}" % mem)

    return data

  def enable(self, tag):
    """
    Enables all the actions with given tag.

    @param tag: tag name
    @type tag: string
    """
    if self._disabled.has_key(tag):
      del self._disabled[tag]
      self._actionlist = None

  def disable(self, tag):
    """
    Disables all the actions with given tag.

    @param tag: tag name
    @type tag: string
    """
    self._disabled[tag] = 1
    self._actionlist = None

  def listTags(self):
    """
    Lists all the existing tags
    """
    tags = {}
    for action in self._actions.values():
      tags[action[6]] = 0
    tags.update(self._disabled)  
    return [ "%s tag={%s}" % ((" enabled", "disabled")[disabled], mem)
             for (mem, disabled) in tags.items() ]


class ActionManager(manager.Manager):
  def __init__(self):
    self._actions = {}

  def getActionData(self, ses):
    if not self._actions.has_key(ses):
      self._actions[ses] = ActionData(ses)
    return self._actions[ses]

  def clear(self, ses):
    if self._actions.has_key(ses):
      self._actions[ses].clear()

  def getInfoMappings(self, item, ses):
    if item != "action":
      raise ValueError("%s is not a valid item for this manager." % item)

    return self.getActionData(ses).getInfoMappings()

  def getItems(self):
    return [ "action" ]

  def getParameters(self, item):
    if item != "action":
      raise ValueError("%s is not a valid item for this manager." % item)

    return [ ("trigger", "Text that triggers the action."),
             ("action", "Command to execute when the trigger is kicked off."),
             ("tag", "Group of actions this action belongs to."),
             ("color", "Whether we try to match the line with color or not."),
             ("priority", "The priority to test this trigger at."),
             ("onetime", "Whether this action should be removed after it's triggered.")]
    
  def getInfo(self, ses, text="", tag=None):
    return self.getActionData(ses).getInfo(text, tag)

  def getDisabledInfo(self, ses, tag=None):
    return self.getActionData(ses).getDisabledInfo(tag)

  def listTags(self, ses):
    return self.getActionData(ses).listTags()

  def addSession(self, newsession, basesession=None):
    if basesession:
      if self._actions.has_key(basesession):
        bdata = self.getActionData(basesession)
        ndata = self.getActionData(newsession)

        for (mem, act) in bdata._actions.items():
          ndata.addAction(mem, *act[2:])
        for tag in bdata._disabled.keys():
          ndata.disable(tag)

  def removeSession(self, ses):
    if self._actions.has_key(ses):
      del self._actions[ses]

  def getStatus(self, ses):
    return self.getActionData(ses).getStatus()

  def persist(self, args):
    """
    write_hook function for persisting the state of our session.
    """
    ses = args["session"]
    quiet = args["quiet"]

    ad = self.getActionData(ses)

    data = ad.getInfo() + ad.getDisabledInfo()

    if quiet == 1:
      data = [m + " quiet={true}" for m in data]

    return data

  def variableChange(self, args):
    """
    When a variable changes, we need to recompile the regular
    expressions involved.  This facilitates that.

    This is registered with the variable_change hook.
    """
    ses = args["session"]
    if self._actions.has_key(ses):
      self._actions[ses]._recompileRegexps()

  def mudfilter(self, args):
    """
    mud_filter_hook function to check for actions when data
    comes from the mud.
    """
    ses = args["session"]
    text = args["dataadj"]

    if exported.get_config("ignoreactions", ses, 0) == 0:
      if self._actions.has_key(ses):
        self._actions[ses].checkActions(text)

    return text


def get_ordered_vars(text):
  """
  Takes in a string and removes any ordered variables
  from it.  Returns a list of the variables.

  @param text: the incoming string which may have ordered variables in it.
  @type  text: string

  @return: list of strings of the form '%[0-9]+' for ordered variable
      substitution.
  @rtype: list of strings
  """
  keylist = []
  matches = VARREGEXP.findall(text)

  for match in matches:
    keylist.append(match)

  return keylist

commands_dict = {}

def action_cmd(ses, args, input):
  """
  With no trigger, no action and no tag, prints all actions.
  With no trigger and no action, prints all actions with given tag.
  With a trigger and no action, prints actions that match the
  trigger statement.
  With a trigger and an action, creates an action.

  When data from the mud matches the trigger clause, the response
  will be executed.  Trigger clauses can use anchors (^ and $)
  to anchor the text to the beginning and end of the line 
  respectively.

  Triggers can also contain Lyntin pattern-variables which start
  with a % sign and have digits: %0, %1, %10...  When Lyntin sees 
  a pattern-variable in an action trigger, it tries to match any 
  pattern against it, and saves any match it finds so you can 
  use it in the response.  See below for examples.

  Note: As a note, actions are matched via regular expressions.
  %1 gets translated to (.+?) and %_1 gets translated to (\S+?).
  The special variable "%a" means "the whole matched line".

  We handle regular expressions with a special r[ ... ] syntax.  If
  you put an "i" or "I" after the ], then we'll ignorecase as well.

  The onetime argument can be set to true to have the action remove
  itself automatically after it is triggered.

  examples:
    #action {^You are hungry} {get bread bag;eat bread}
    #action {%0 gives you %5} {say thanks for the %5, %0!}
    #action {r[^%_1 tells\\s+you %2$]} {say %1 just told me %2}
    #action {r[sven dealt .+? to %1$]i} {say i just killed %1!}

  see also: unaction, enable, disable, atags
  
  category: commands
  """
  trigger = args["trigger"]
  action = args["action"]
  color = args["color"]
  priority = args["priority"]
  onetime = args["onetime"]
  quiet = args["quiet"]
  tag = args["tag"]

  am = exported.get_manager("action")
  ad = am.getActionData(ses)

  # they typed '#action'--print out all the current actions
  if not action:
    data = ad.getInfo(trigger, tag)
    if not data:
      data = ["action: no actions defined."]

    message = "actions"
    if tag:
      message += " with tag={%s}" % tag
      data += ad.getDisabledInfo(tag)
    exported.write_message(message + "\n" + "\n".join(data), ses)
    return

  try:
    ad.addAction(trigger, action, color, priority, onetime, tag)
    if not quiet:
      exported.write_message("action: {%s} {%s} color={%d} priority={%d} tag={%s} added." % (trigger, action, color, priority, str(tag)), ses)
  except:
    exported.write_traceback("action: exception thrown.", ses)

commands_dict["action"] = (action_cmd, "trigger= action= tag= color:boolean=false priority:int=5 onetime:boolean=false quiet:boolean=false")

def unaction_cmd(ses, args, input):
  """
  Removes action(s) from the manager.

  examples:
    #unaction {missed you.}
    #unaction missed*
    #unaction tag={indoor}
    
  see also: action, enable, disable, atags

  category: commands
  """
  am = exported.get_manager("action")
  ad = am.getActionData(ses)
  func = lambda x: ad.removeActions(x, args["tag"])
  modutils.unsomething_helper(args, func, None, "action", "actions")

commands_dict["unaction"] = (unaction_cmd, "str= tag= quiet:boolean=false")


def action_enable_cmd(ses, args, input):
  """
  Enables actions with given tag.
  By default, all the tags are enabled.
  
  see also: action, unaction, disable, atags

  category: commands
  """
  tag = args["tag"]
  am = exported.get_manager("action")
  ad = am.getActionData(ses)
  ad.enable(tag)

  if not args["quiet"]:
    exported.write_message("Enabling actions tagged as {%s}" % tag)
    
commands_dict["enable"] = (action_enable_cmd, "tag= quiet:boolean=false")

def action_disable_cmd(ses, args, input):
  """
  Temporarily disables all the actions with given tag, so their triggers
  won't trigger any actions (well, this desciption is a bit obscure,
  but I've tried my best :)

  see also: action, unaction, enable, atags
  
  category: commands
  """
  tag = args["tag"]
  am = exported.get_manager("action")
  ad = am.getActionData(ses)

  ad.disable(tag)

  if not args["quiet"]:
    exported.write_message("Disabling actions tagged as {%s}" % tag)
  
commands_dict["disable"] = (action_disable_cmd, "tag= quiet:boolean=false")

def action_tags_cmd(ses, args, input):
  """
  Shows all the tags available

  see also: action, unaction, enable, disable
  
  category: commands
  """
  list = exported.get_manager("action").listTags(ses)
  if list:
    exported.write_message("\n".join(list))
  else:
    exported.write_message("No tags defined.")

commands_dict["atags"] = (action_tags_cmd, "")  


am = None

def load():
  """ Initializes the module by binding all the commands."""
  global am, var_module
  modutils.load_commands(commands_dict)
  am = ActionManager()
  exported.add_manager("action", am)

  exported.hook_register("mud_filter_hook", am.mudfilter, 75)
  exported.hook_register("write_hook", am.persist)
  exported.hook_register("variable_change_hook", am.variableChange)

  from lyntin import config
  for mem in exported.get_active_sessions():
    # we need a separate BoolConfig for each session
    tc = config.BoolConfig("ignoreactions", 0, 1,
         "Allows you to turn off action handling.")
    exported.add_config("ignoreactions", tc, mem)

def unload():
  """ Unloads the module by calling any unload/unbind functions."""
  global am, var_module
  modutils.unload_commands(commands_dict.keys())
  exported.remove_manager("alias")

  exported.hook_unregister("mud_filter_hook", am.mudfilter)
  exported.hook_unregister("write_hook", am.persist)
  exported.hook_unregister("variable_change_hook", am.variableChange)

  # remove configuration items for every session involved
  for mem in exported.get_active_sessions():
    exported.remove_config("ignoreactions", mem)

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
