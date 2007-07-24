#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2001-2007
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: message.py,v 1.3 2007/07/24 00:39:03 willhelm Exp $
#######################################################################
"""
Holds the ui's Message class.  This gets passed around Lyntin and
allows us to scope data going to the ui.
"""

""" The message type constants."""
ERROR = "ERROR: "
USERDATA = "USERDATA: "
MUDDATA = "MUDDATA: "
LTDATA = "LTDATA: "

""" Used for debugging purposes."""
MESSAGETYPES = {ERROR: "ERROR: ",
                USERDATA: "USERDATA: ",
                MUDDATA: "MUDDATA: ",
                LTDATA: "LTDATA: "}

class Message:
  """
  Encapsulates a message to be written to the user.
  """
  def __init__(self, data, messagetype=LTDATA, ses=None, **hints):
    """
    Initialize.

    @param data: the message string
    @type  data: string

    @param messagetype: the message type (use a constant defined in ui.ui)
    @type  messagetype: int

    @param ses: the session this message belongs to
    @type  ses: session.Session
    """
    self.session = ses
    self.data = data
    self.type = messagetype
    self.hints = hints

  def __repr__(self):
    """
    Represents the message (returns data + type).
    """
    return repr(self.session) + MESSAGETYPES[self.type] + repr(self.data)

  def __str__(self):
    """
    The string representation of the Message is the data
    itself.
    """
    return self.data


