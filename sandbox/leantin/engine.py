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
    self.shutdown = libmisc.Flag()
    return

  def add_session(self, sess, msg=''):
    if (not self._default_session):
      self._default_session = sess
    else:
      self.setup_reads_for_session(sess)

    self.sessions.insert(0, sess) # newest sessions come first
    self.shutdown.also_flag(sess.shutdown)
     # create the first ocatch that handles commands
    cmd = mudcommands.CommandCatcher(listen=1, muffle=1)
    cmd.add_callback(lambda :cmd.apply_command(sess))
    sess.ocatch.add(cmd)
    
    # setup the UI
    self.ui.change_session(sess.ui)
    sess.ui.write('DEBUG, welcome to %s\n' % (sess.name))
    sess.ui.write(msg)
    return

  def launch_ui(self, ui_cls):
    self.ui = ui_cls(shutdown=self.shutdown,
                     input_callback=self.to_mud,
                    )
    return

  def rm_session(self, sess):
    if (sess == self._default_session): # sanity check
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
    junk_t = threading.Thread(target=sess.from_mud)
    junk_t.start()

  def to_mud(self, text):
    sess = self.sessions[0]
    sess.to_mud(text)

class Quit(mudcommands.Command):
  command = 'end'
  def do_command(sess, arg):
    global engine
    engine.shutdown.flag_true()
    return
