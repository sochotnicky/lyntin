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
# $Id: manager.py,v 1.5 2007/07/24 00:39:03 willhelm Exp $
#########################################################################
"""
Managers manage things.  Most X{manager}s subclass the "manager.Manager"
class.  It doesn't really provide a lot of functionality, but it 
allows us to group them all and treat them all the same.  Adding 
new managers is much easier because of this.

Also, managers register themselves with the engine via the
"exported.add_manager" function.  The engine will cycle
through registered managers for things like status and persistence.
In addition, registered managers get told when the user has created
a new session and when the user has ended a session through the
"addSession" and "removeSession" methods.

To build a new manager, you need to:

  1. extend the manager.Manager class

  2. implement all the methods of manager.Manager that are marked as 
     needing to be overridden

  3. implement the additional methods that your manager needs

  4. create a "load()" function in the module your manager is 
     defined in which adds the manager to the engine via 
     "exported.add_manager(...)"


Then to dynamically load your new module and instantiate your new manager
you can do one of two things:

  1. put the .py file in the modules/ subdirectory where it will be 
     loaded automatcially

  2. execute an "#import modulenamehere" inside of Lyntin which will 
     import the module
"""

class Manager:
  """
  Base manager class for managing things in Lyntin.  The Manager class
  gives all managers a standard way of interacting with sessions and user
  queries for information, 
  """
  def __init__(self):
    pass

  def clear(self, ses=None):
    """
    Removes everything the manager was managing--essentially reinitializes it.
    Override this to clear out the data your manager is managing.  This is
    typically session oriented and gets called by the "#clear" command.

    @param ses: the session this applies to--None if it applies to all
        sessions
    @type  ses: session.Session
    """
    pass

  def getInfo(self, ses, text=''):
    """
    Returns information managed by this class.  This is mostly for 
    display to the user--we shouldn't be using this method for Lyntin 
    introspection.

    @param text: allows the user to pass in a name filter which should
        show a subset of the data based on what names match the filter
    @type  text: string

    @return: a string of everything involved
    @rtype: string
    """
    return ''

  def getItems(self):
    """
    Returns a list of the items that this manager manages.  So the
    gag manager manages gags as well as antigags and would return::

       [ "gag", "antigag" ]

    These items are used in getInfoMappings as well as getParameters.

    If this manager doesn't manage anything, then it'll return an
    empty list.

    @return: returns a list of strings
    @rtype: list of strings
    """
    return []

  def getInfoMappings(self, item, ses):
    """
    Returns a list of maps of parameter name -> value that represents
    all the info this manager is managing for this session.

    For example, an AliasManager manages aliases and their expansions.
    Say it had three aliases a, b, and c which expand to "smile %1", 
    "frown %1", and "kick %1".  It would return::

       [
         { "alias": "a", "expansion": "smile %1" },
         { "alias": "b", "expansion": "frown %1" },
         { "alias": "c", "expansion": "kick %1" }
       ]

    @param item: the item to get data for
    @type  item: string

    @param ses: the session in question
    @type  ses: Session

    @returns: a list of maps of parameter name -> value
    @rtype: list of mappings
    """
    return []

  def getParameters(self, item):
    """
    Returns a list of tuples of the parameters we're storing in
    this manager and the description of each parameter.

    If this manager does not manage this item, it should raise
    a ValueError.

    @param item: the item to get parameters for
    @type  item: string

    @returns: list of (parameter, desc) tuples
    @rtype: list of tuples
    """
    return []

  def addSession(self, newsession, basesession=None):
    """
    Tells the manager to create a new session based on another session.
    For example, when we connected to the 3k mud, we would tell all
    the managers to clone the common session to the new session created
    thus populating the new session.

    @param newsession: the new session just created
    @type  newsession: Session

    @param basesession: the session to use as a template for the new
        session.  most managers just copy the data from the basesession
        to the newsession.  if this is None, then we don't want to clone
        from anything--we use None when Lyntin starts up and we create
        the common session.
    @type  basesession: Session
    """
    pass

  def removeSession(self, ses):
    """
    Tells the manager to remove information regarding the session.

    @param ses: the session we no longer need to hold information for
        because the session has gone away
    @type  ses: Session
    """
    pass

  def getStatus(self, ses):
    """
    Returns a one-liner status of the state of this manager for
    a given session.  If this manager does not apply to sessions
    then it should return an empty string.

    For example, the SubstituteManager which is holding 5 substitutes
    and 2 gags for a session named "3k" would return the string::

       "5 substitute(s). 2 gag(s)."

    But the ThreadManager which is a globally scoped manager and doesn't 
    apply to the "3k" session would return an empty string.

    @param ses: the session to get status for
    @type  ses: Session

    @return: a one-liner string of the status or an empty string
    @rtype: string
    """
    return ''

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
