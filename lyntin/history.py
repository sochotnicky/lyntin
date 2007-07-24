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
# $Id: history.py,v 1.4 2007/07/24 00:39:03 willhelm Exp $
#########################################################################
"""
The HistoryManager keeps track of the last 1000 lines of user input 
X{history}. The HistoryManager is a singleton and it's on an engine 
scoping thus we don't keep track of history per session.
"""
import manager

class HistoryManager(manager.Manager):
  """
  Manages user data history.

  This manages the user input history by storing the commands the
  user entered.  This module also handles manipulating that history
  letting the user to recall and edit those commands to fix mistakes
  they may have typed.
  """
  def __init__(self, e):
    self._history = [""]
    self._config = e.getManager("config")
    self._engine = e

  def getHistoryItem(self, userinput):
    """
    This retrieves the item (if it exists) and performs the 
    substitutions (if we need to).

    @param userinput: what the user typed--we'll use this to figure
        out which item they're referring to and whether to apply a 
        substitution
    @type  userinput: string

    @returns: None if we didn't discover anything or the command 
        string at the history index
    """
    tokens = userinput.split(" ", 1)

    # grab the first (and possibly only) token and remove the !
    index = tokens[0][1:]

    # if it's very short, we're looking at the last thing typed
    # (prior to this thing they typed)
    if len(index) == 0:
      returninput = self._history[0]
    else:
      try:
        returninput = self._history[int(index)]
      except:
        for h in self._history:
          if h[0:len(index)] == index:
            return h
        return None

    # check to see if they want to do a substitution
    if len(tokens) > 1:
      i = tokens[1].find("=")
      if i != -1:
        returninput = returninput.replace(tokens[1][:i], tokens[1][i+1:])

    return returninput

  def getHistory(self, count):
    """
    Returns everything in the history buffer as a list of strings

    @return: everything in the history buffer
    @rtype: list of strings
    """
    return self._history[:count]

  def recordHistory(self, input):
    """
    Records an item in the history (which is a queue).

    @param input: the line to record
    @type  input: string
    """
    if not input:
      return

    if input == self._history[0] and not self._config.get("repeathistory"):
      return

    self._history.insert(0, input)
    if len(self._history) > 1000:
      del self._history[-1]

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
