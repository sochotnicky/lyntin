# python imports
import threading, Queue
# our imports
import libmisc, mudcommands

"""A very short and empty class that defines our top level Engine class"""

engine = None

class Engine(object):
  def __new__(cls, *args, **opts):
    global engine
    if (engine is None):
      engine = object.__new__(cls)
      engine.init(engine, *args, **opts)
    return engine

  def init(self, *args, **opts):
    print "Engine INIT"
    self.config = {} # Config()
    self.ui = {}
    self.sessions = []
    self._default_session = None
    self.shutdown = libmisc.Shutdown()
    return

  def add_session(self, sess):
    if (not self._default_session):
      print "Assiging default session"
      self._default_session = sess
    else:
      print "Assiging regular session"
      self.setup_reads_for_session(sess)

    self.sessions.insert(0, sess) # newest sessions come first
    self.shutdown.also_shutdown(sess.shutdown)
     # create the first ocatch that handles commands
    cmd = mudcommands.CommandCatcher(listen=1, muffle=1)
    cmd.add_callback(lambda :cmd.apply_command(sess))
    sess.ocatch.add(cmd)
    
    # setup the UI
    self.ui.change_session(sess.ui)
    sess.ui.write('DEBUG, welcome to %s\n' % (sess.name))
    return

  def launch_ui(self, ui_cls):
    self.ui = ui_cls(shutdown=self.shutdown,
                     input_callback=self.to_mud,
                    )
    return

  def rm_session(self, sess):
    if (sess == self._default_session):
      return
    
    self.sessions = filter(lambda x:x!=sess, self.sessions)
    self.ui.change_session(self.sessions[0].ui)
    sess.ui._destroy() # we have to hide/unhide others first or packing gets messed up    
    return

  def ch_session(self, sess):
    # tell the ui to change to the current session
    self.ui.change_session(sess.ui)
    # move this session to the front of the list
    self.sessions = [sess] + filter(lambda x:x!=sess, self.sessions)
    return

  def setup_reads_for_session(self, sess):
    lb = libmisc.LineBuffer()
    def from_mud():
      while not sess.shutdown:
        try:
          txt = sess.sock.read()
        except: # bad things, just get out
          self.shutdown.shutdown()
          return # finishes the tread
        if (txt):
          for (line) in lb.add(txt):
            final_line = sess.icatch.input(line)
            sess.ui.write(final_line)
          if (lb.pending and sess.rawcatch):
            for (i, rawcatcher) in enumerate(sess.rawcatch):
              output = rawcatcher.raw_input(lb.pending)
              if (output):
                sess.sock.write(output+"\n")
                sess.rawcatch.pop(i)
      print "Shutting down sock", sess.name
    
    junk_t = threading.Thread(target=from_mud)
    junk_t.start()

  def to_mud(self, text):
    if (self.sessions):
      sess = self.sessions[0]
    else:
      sess = self._default_session

    final_text = sess.ocatch.input(text)
    if (final_text):
      if (sess.sock and not sess.sock.shutdown):
        sess.sock.write(final_text)
      else:
        sess.ui.write("# WARNING, output ignored.  You aren't attached to anything\n")

class Quit(mudcommands.Command):
  command = 'end'
  def do_command(sess, arg):
    global engine
    engine.shutdown.shutdown()
    return
