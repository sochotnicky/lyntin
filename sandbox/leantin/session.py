import catcher
import sock
import mudcommands
import libmisc
import engine
import login

class Session(object):
  def __init__(self, **opts):
    self.config = None
    self.ui = None
    self.commands = []
    self.mud = None
    self.modes = None
    self.timecron = None
    self.turncron = None
    self.player = None
    self.ocatch = None
    self.icatch = None
    self.rawcatch = []
    self.name = opts.get('name', 'unnamed')
    self.sock = None
    return

  def engine_init(self, engine):
    self.config = Congif(engine.config)
    return

class Connect(mudcommands.Command):
  command = 'connect'
  def do_command(dummy, arg):
    if (arg != '_default'):
      if (arg not in login.Login.all):
        engine.Engine().ui.write("No idea, choices are %s" % (','.join(login.Login.all.keys())))
        return
      name = arg
      info = login.Login.all[name]
    else:
      info = None
      
    sess = Session(name=arg)
    sess.ui = engine.Engine().ui.session_ui()
    sess.shutdown = libmisc.Shutdown()
    sess.ocatch = catcher.CatchQueue()
    if (arg != '_default'):
      sess.sock = sock.Sock(info.mud_class.host, info.mud_class.port, shutdown=sess.shutdown)
      sess.timecron = libmisc.Cron()
      sess.turncron = libmisc.Cron()
      sess.icatch = catcher.CatchQueue()
      sess.mud = info.mud_class()
      sess.player = info.player_class()
      # give everyone a chance to hook into the catchers, least likely to need it first
      for (ob) in [sess.timecron, sess.turncron, sess.mud, sess.player]:
        ob.sess_init(sess)
      if (sess.mud.name_prompt):
        sess.rawcatch.append(catcher.CallAndResponse(sess.mud.name_prompt, info.user_name))
      if (sess.mud.pass_prompt):
        sess.rawcatch.append(catcher.CallAndResponse(sess.mud.pass_prompt, info.password))
    print "Adding session", sess.name
    engine.Engine().add_session(sess)
    if (info is not None):
      info.ui_init(sess.ui)
    return

class Disconnect(mudcommands.Command):
  command = 'disconnect'
  def do_command(sess, arg):
    if (sess.name == '_default'):
      sess.ui.write("You aren't connected to anything!")
      return

    sess.shutdown.shutdown()
    engine.Engine().rm_session(sess)
    return

class ChangeSession(mudcommands.Command):
  command = 'session'
  def do_command(sess, arg):
    eng = engine.Engine()
    change_to_sess = []
    for (sess) in eng.sessions:
      if (sess.name == arg): # perfect matches come first
        change_to_sess.insert(0, sess)
      elif (sess.name.startswith(arg)): # they might have meant a partial match
        change_to_sess.append(sess)
    if (change_to_sess): # at least one match, perfect comes first.  Otherwise most recent session with a partial match
      eng.ch_session(change_to_sess[0])
    return
