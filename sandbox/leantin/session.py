import socket

import catcher
import rtelnetlib, sock
import mudcommands
import libmisc
import engine
import login

class Session(object):
  def __init__(self, **opts):
    self.config = None
    self.ui = None
    self.commands = []
    self.mode = []
    self.mud = None
    self.modes = None
    self.timecron = None
    self.turncron = None
    self.player = None
    self.ocatch = None
    self.icatch = None
    self.name = opts.get('name', 'unnamed')
    self.prompt = opts.get('prompt', None)
    self.log = None
    self.sock = None
    self.rawcatch = []
    self.echo_change = None
    self.__lb = libmisc.LineBuffer(prompt=self.prompt)

  def from_mud(self):
    """ This is run in it's own thread created by the engine,
        DO NOT call this yourself
    """
    while not self.shutdown and not self.sock.shutdown:
      try:
        txt = self.sock.read()
        if (not txt):
          continue
      except (rtelnetlib.ReadException):
        # we didn't get a newline we were hoping for
        # assume we are looking at a prompt and paint the pending line anyway
        if (self.__lb.pending):
          self.ui.write_prompt_text(self.__lb.pending)
          self.__lb.pending = ''
        continue
      except Exception, e: # bad things, just get out
        print "BAD THINGS", str(e)
        self.shutdown.flag_true()
        continue # finishes the tread

      # iterate over all the full lines (newline terminated)
      for (line) in self.__lb.add(txt):
        final_line = self.icatch.line(line)
        if (final_line.strip()): # not just whitespace on the line
          self.ui.write_mud_text(final_line)
          if (self.log):
            self.log.write(final_line)

      if (self.__lb.pending):
        # if we have a partial line see if it matches our rawcacthers
        # this is where login prompts are handled
        if (self.rawcatch):
          for (i, rawcatcher) in enumerate(self.rawcatch):
            output = rawcatcher.raw_input(self.__lb.pending)
            if (output):
              self.sock.write(output+"\n")
              self.rawcatch.pop(i)
    # end while
    print "Shutting down sock", self.name
    return
  
  def to_mud(self, txt):
    """Call this function to output text to the mud"""
    final_text = self.ocatch.line(txt)
    if (final_text):
      if (self.sock and not self.sock.shutdown):
        self.sock.write(final_text)
        if (self.log):
          self.log.write('%' + final_text)
      else:
        self.ui.write("# WARNING, output ignored.  You aren't attached to anything\n")
        print self.sock, self.sock and self.sock.shutdown and 1
    return

class Connect(mudcommands.Command):
  command = 'connect'
  def do_command(sess, arg):
    eng = engine.Engine()
    if (arg != '_default'):
      if (arg not in login.Login.all):
        # write to the current UI
        sess.ui.write("No idea, choices are %s" % (','.join(login.Login.all.keys())))
        return
      if (arg in map(lambda x:x.name, eng.sessions)): # already have one of those
        sess.ui.write("Already connected to '%s'\n"
                      "Use 'session %s' to change to that session" % (arg, arg))
        return
      name = arg
      info = login.Login.all[name]
      prompt = info.mud_class.prompt
    else:
      info = None
      prompt = None
      
    sess = Session(name=arg, prompt=prompt)
    sess.shutdown = libmisc.Flag()
    sess.ocatch = catcher.CatchQueue()
    sess.ui = engine.Engine().ui.session_ui()
    msg = ''
    if (arg != '_default'):
      sess.sock = sock.Sock(info.mud_class.host, info.mud_class.port,
                            recv_timeout=0.3,
                            prompt_on_timeout=1,
                            shutdown=sess.shutdown,
                            echo_callback=sess.ui.echo_change,
                           )
      sess.ui.size_change = sess.sock.update_size
      msg = 'Connected to %s %d\n' % (info.mud_class.host, info.mud_class.port)
      sess.timecron = libmisc.Cron()
      sess.turncron = libmisc.Cron()
      sess.icatch = catcher.CatchQueue()
      sess.mud = info.mud_class()
      sess.player = info.player_class()
      # give everyone a chance to hook into the catchers, least likely to need it first
      for (ob) in [sess.timecron, sess.turncron, sess.mud, sess.player]:
        ob.sess_init(sess)
      if (sess.mud.name_prompt and info.user_name is not None):
        sess.rawcatch.append(catcher.CallAndResponse(sess.mud.name_prompt, info.user_name))
      if (sess.mud.pass_prompt and info.password is not None):
        sess.rawcatch.append(catcher.CallAndResponse(sess.mud.pass_prompt, info.password))
      if (info.log_dir):
        libmisc.ensure_path_built(info.log_dir)
        sess.log = open('%s/%s.log' % (info.log_dir, info.name), 'a+')

    engine.Engine().add_session(sess, msg)
    if (info is not None):
      info.ui_init(sess.ui)
    return

class Disconnect(mudcommands.Command):
  command = 'disconnect'
  def do_command(sess, arg):
    if (sess.name == '_default'):
      sess.ui.write("You aren't connected to anything!")
      return

    sess.shutdown.flag_true()
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
