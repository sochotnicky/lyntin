#!/usr/bin/env python
#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2001
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: testserver.py,v 1.2 2005/01/07 14:50:40 glasssnake Exp $
#######################################################################
"""
This new test-server is a patchwork of stuff from the existing test server
and code I wrote for the Varium mud server way back when.  It is actually
a functional mini-mud now.
"""
import socket, sys, Queue, select, string
import connection, toolsutils
from toolsutils import wrap_text

my_world = None

class Event:
  def __init__(self):
    pass

  def execute(self, world):
    pass

  def __str__(self):
    return ""

class InputEvent(Event):
  def __init__(self, conn, input):
    self._conn = conn
    self._input = input

  def __str__(self):
    return '"%s" for "%s"' % (self._input, str(self._conn))

  def execute(self, world):
    self._conn.handleInput(world, self._input)

class HeartbeatEvent(Event):
  def __init__(self, source):
    self._source = source

  def execute(self, world):
    self._source.heartbeat(world)

class NPC:
  def __init__(self, world):
    self._world = world
    self._name = "Joe"
    self._desc = "A regular looking NPC."

    from random import Random
    self._random = Random()

  def blab(self):
    self._world.spamroom(self._name + " looks fidgety.\n")

  def heartbeat(self, world):
    pass

class Neil(NPC):
  def __init__(self, world):
    NPC.__init__(self, world)
    self._name = "Neil"
    self._desc = "Neil is the bartender at this little mini-tavern."

  def heartbeat(self, world):
    g = (self._random.random() * 10)
    if (g < 2):
      self._world.spamroom(self._name + " flicks a bug off his bar.\n")
    elif (g < 4):
      self._world.spamroom(self._name + " scrubs some glasses with his dishrag.\n")
    elif (g < 5):
      self._world.spamroom(self._name + " says, \"Mighty fine morning, isn't it?\"\n")


class World:
  def __init__(self, options):
    self._event_queue = Queue.Queue(0)
    self._worker = None
    self._options = options
    self._ms = None

    temp = ("Welcome to Neil's Pub--a small tavern of unusual candor.  " +
            "In many ways, this is a dream come true for Neil and it shows " +
            "in the care he gives to the place.  The tavern is both " +
            "infinitely large and terribly small.  There are no exits.  " +
            "Only a long bar and a series of barstools for folks to show " +
            "up, take a load off, and socialize.")

    self._desc = wrap_text(temp, 70, 0, 0)
    self._npcs = []

    self._npcs.append(Neil(self))

  def enqueue(self, ev):
    self._event_queue.put(ev)

  def startup(self):
    from threading import currentThread
    self._worker = currentThread()

    # launch the server
    self._ms = MasterServer(self, self._options)
    self._ms.startup()

    do_heartbeat = self._options["heartbeat"]
    beat = 0

    # this is our main loop thingy!
    while 1:
      if do_heartbeat == "yes":
        beat += 1
        if beat % 30 == 0:
          beat = 0
          self.heartbeat()

      self._ms.networkLoop()

      if not self._event_queue.empty():
        event = self._event_queue.get(0)
        es = str(event)
        if es:
          print "handling: '%s'" % es

        try:
          event.execute(self)
        except Exception, e:
          print "exception: %s" % e

          if hasattr(event, 'conn'):
            try:
              conn.write("exception: %s" % e)
            except: pass

      
  def heartbeat(self):
    # we don't do heartbeats when no one is connected.
    if len(self._ms._conns) > 1:
      for mem in self._npcs:
        self.enqueue(HeartbeatEvent(mem))

  def disconnect(self, conn):
    if conn in self._ms._conns:
      self._ms._conns.remove(conn)
    if hasattr(conn, '_name'):
      self.spamroom("%s has left the game.\n" % conn._name)
    print "Goodbye %s" % str(conn)

  def look(self, conn, item):
    if item:
      for mem in self._npcs:
        if item == mem._name.lower():
          return mem._desc + "\n"

      for mem in self._ms._conns:
        if item == mem._name.lower():
          return mem._desc + "\n"

    else:
      out = self._desc + "\n\n"
      names = map(lambda x:x._name, self._ms._conns)
      for mem in self._npcs:
        names.append(mem._name)
      out += testutils.wrap_text(string.join(names, ', '), 70, 0, 0)
      out += "\n"

      return out

    return "That does not exist.\n"

  def spamroom(self, data):
    # note--we only spam real connections--not npcs
    for mem in self._ms._conns:
      try: mem.write(data)
      except: pass

  def shutdown(self):
    if self._ms:
      self._ms.closedown()
    print "Shutting down."


class MasterServer:
  def __init__(self, world, options):
    self._args = args
    self._master = None
    self._conns = []
    self._shutdown = 0
    self._options = options
    self._world = world

  def startup(self):
    host = self._options["host"]
    port = int(self._options["port"])
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    s.listen(1)

    print "Test server starting up: %s:%d" % (host, port)
    self._master = connection.Connection(self._world, s, "MASTER")
    self._master._name = "Igor"
    self._master._desc = "A very busy old man."

    self._conns = []
    self._conns.append(self._master)

  def networkLoop(self):
    fi = []

    fns = map(lambda x:x.sockid(), self._conns)
    fi = select.select(fns, [], [], .1)[0]
    allconns = filter(lambda x,y=fi:x.sockid() in y, self._conns)

    for conn in allconns:
      if conn._addr == "MASTER":
        newsock, newaddr = conn._sock.accept()
        newconn = connection.Connection(self._world, newsock, newaddr)
        newconn.write("Welcome to Neil's Pub!  Type \"help\" if you're lost.\n")

        self._conns.append(newconn)

      else:
        try: new_data = conn._sock.recv(1024) 
        except Exception, e:
          print "exception: %s" % e
          if conn in self._conns:
            self._conns.remove(conn)
          conn.killConn()
          continue

        if new_data:
          conn.handleNetworkData(new_data)
        else:
          if conn in self._conns:
            self._conns.remove(conn)
          conn.killConn()

  def closedown(self):
    try: self._master.sockid().close()
    except Exception, e: print "closing down master socket: '%s'" % e
    for mem in self._conns:
      if mem._addr == "MASTER":
        continue
      try:
        mem.write("Server shutting down.\n")
        mem.killConn()
      except:
        pass


def print_syntax(message=""):
  print "testserver.py [--help] [options]"
  print "    -h|--host <hostname> - sets the hostname to bind to"
  print "    -p|--port <port>     - sets the port to bind to"
  print "    --heartbeat <yes|no> - sets whether or not to execute heartbeats"
  print
  if message:
    print message

if __name__ == '__main__':
  import testserver, signal

  # parse out arguments
  args = sys.argv[1:]
  i = 0
  optlist = []
  while (i < len(args)):

    if args[i][0] == "-":
      if (i+1 < len(args)):
        if args[i+1][0] != "-":
          optlist.append((args[i], args[i+1]))
          i = i + 1
        else:
          optlist.append((args[i], ""))
      else:
        optlist.append((args[i], ""))

    else:
      optlist.append(("", args[i]))

    i = i + 1

  options = {"host": "localhost", "port": "3000", "heartbeat":"yes"}
  print "Handling arguments."
  for mem in optlist:
    if mem[0] == "--host" or mem[0] == "-h":
      if mem[1]:
        options["host"] = mem[1]
      else:
        print_syntax("error: Host was not specified.")
        sys.exit(1)

    elif mem[0] == "--help":
      print_syntax()
      sys.exit(1)

    elif mem[0] == "--port" or mem[0] == "-p":
      if mem[1] and mem[1].isdigit():
        options["port"] = mem[1]
      else:
        print_syntax("error: Port needs to be a number.")
        sys.exit(1)

    elif mem[0] == "--heartbeat":
      if mem[1].lower() == "yes" or mem[1].lower() == "no":
        options["heartbeat"] = mem[1].lower()
      else:
        print_syntax("error: Valid heartbeat settings are 'yes' or 'no'.")
        sys.exit(1)

  print "Host: %s" % options["host"]
  print "Port: %s" % options["port"]

  # create the world
  testserver.my_world = World(options)
  try:
    testserver.my_world.startup()
  except Exception, e:
    print "Outer loop exception: %s" % e
  testserver.my_world.shutdown()

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
