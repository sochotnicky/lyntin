#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: message.py,v 1.1 2003/08/01 00:14:52 willhelm Exp $
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
  def __init__(self, data, messagetype=LTDATA, ses=None):
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


