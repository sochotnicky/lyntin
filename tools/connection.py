#!/usr/bin/env python
#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2001
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: connection.py,v 1.2 2005/01/07 14:50:40 glasssnake Exp $
#######################################################################
"""
This new test-server is a patchwork of stuff from the existing test server
and code I wrote for the Varium mud server way back when.  It is actually
a functional mini-mud now.
"""
import string, testserver, toolsutils
from toolsutils import color


class Connection:
  def __init__(self, world, newsock, newaddr=''):
    self._world = world
    self._sock = newsock
    self._sock.setblocking(0)      # non-blocking
    self._buffer = []
    self._addr = newaddr
    self._name = "spirit"
    self._desc = "A regular user."

    self._dir = []
    for item in dir(self.__class__):
      if ( type( eval("self.%s" % item)) == type(self.__init__) and \
            item.find("handle_") == 0):
        self._dir.append(item)

  def __str__(self):
    return repr(self._addr)

  def killConn(self):
    """killConn(self) -> None

    Shuts down the socket for the Connection ob.
    """
    if not self._sock: return
    self._sock.shutdown(2)
    self._sock.close()
    self._sock = None
    self._world.disconnect(self)

  def write(self, data):
    if not self._sock: return
    if not data: return

    data = string.replace(data, "\n", "\r\n")
    self._sock.send(data)

  def sockid(self):
    return self._sock

  def handleNetworkData(self, new_data):
    for c in new_data:
      if (c == chr(8) or c == chr(127)):
        if self._buffer:
          self._buffer = self._buffer[:-1]
        continue
      elif ord(c) > 127:
        continue
      elif c == "\n":
        self._world.enqueue(testserver.InputEvent(self, string.join(self._buffer, "")))
        self._buffer = []
        continue
      elif c == "\r" or c == chr(0):
        pass
      else:
        self._buffer.append(c)

  def handleInput(self, world, input):
    comm = input.split(" ", 1)[0]
    if ("handle_%s" % comm) in self._dir:
      exec ( "self.handle_%s(world, input)" % comm)
    else:
      # CATCH ALL for bad commands
      self.write(color("huh? '%s'\n" % input, 35))
    self.write("> ")

  def handle_set(self, world, input):
    """ Lets you set things: (name, desc...)."""
    if " " in input:
      input = input.split(" ", 1)[1]
    if " " in input:
      name, value = input.split(" ", 1)

      if hasattr(self, '_%s' % name):
        self.write("Old value of %s is '%s'.\n" % (name, eval("self._%s" % name)))
      exec ("self._%s = value" % name)
      self.write("Set to '%s'.\n" % value)
    else:
      self.write("Nothing to set.\n")

  def handle_say(self, world, input):
    """ Talk to your fellow mudders!"""
    if " " in input:
      text = input.split(" ", 1)[1]
      self.write(toolsutils.wrap_text("You say: %s" % text, 72, 5, 0) + "\n")
      world.spamroom(toolsutils.wrap_text("%s says: %s" % (self._name, text), 72, 5, 0) + "\n")
    else:
      self.write("say what?\n")

  def handle_look(self, world, input):
    """ Lets you look at things.  syntax: look <at thing>"""
    item = None
    if " " in input:
      item = input.split(" ", 1)[1].replace("at", "").strip().lower()

    self.write(world.look(self, item))

  def handle_quit(self, world, input):
    """ Quits out."""
    self.killConn()

  def handle_help(self, world, text):
    """ Prints out all the commands we understand."""
    commands = []
    for mem in self._dir:
      if mem.find("handle_") == 0:
        doc = ""
        try: doc = eval ("self.%s.__doc__" % mem)
        except: pass

        if doc:
          commands.append(mem[7:] + " - " + doc)
        else:
          commands.append(mem[7:])

    self.write(string.join(commands, "\n") + "\n")

  def handle_set_color(self, world, text):
    """ Sets the color to yellow."""
    self.write("\33[33m\nNow yellow.")

  def handle_colors(self, world, text):
    """ Prints out all the colors we know about."""
    response = ''
    for background in range(40,48):
      for foreground in range(30,38):
        response += color(str(foreground), foreground, background)
        response += color(str(foreground), foreground, background, 1)
      response += "\33[0m\n"

    self.write(response)

  def handle_lyntin(self, world, text):
    """ Returns a paragraph, which coincidentally, is a description of Lyntin."""
    output = ("Lyntin is a mud client that is written in Python and uses " +
             "Python as a scripting language. It strives to be functionally " +
             "similar to TinTin++ while enhancing that functionality with " +
             "the ability to call Python functions directly from the input " +
             "line. It has the advantage of being platform-independent and " +
             "has multiple interfaces as well--I use Lyntin at home with " +
             "the Tk interface as well as over telnet using the text " +
             "interface.\n")
    output = toolsutils.wrap_text(output, 70, 0, 0)
    self.write(output)

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
