# lyntin import, dummy up a class if the import fails
import re, gc
import catcher, libmisc

TWO_ARGS = re.compile('(.*),(.*)', re.DOTALL)

class MetaCommand(type):
  all = []
  def __init__(cls, name, bases, dict):
    """We touchup the defined class here and add it as a command"""
    func = getattr(cls, 'do_command', None)
    if (not func): # must be an intermediate class
      return
    setattr(cls, 'do_command', staticmethod(func.im_func)) # don't let anyone on c.l.py see this
    if (cls.arg_parse is not None):
      setattr(cls, 'arg_parse_re', re.compile(cls.arg_parse))
    MetaCommand.all.append(cls)
    return

class CommandCatcher(catcher.Catcher):
  start = re.compile('^#(.*)')
  end = start

  def __init__(self, *args, **opts):
    catcher.Catcher.__init__(self, *args, **opts)
    self.command_input = None
    return
  
  def parse(self, lines):
    text = '\n'.join(lines)
    self.command_input = text
    return

  def parse_command_input(self, extra_commands = []):
    """valid after we've caught a command and parse() has been called.
       if a list of extra_commands is included they will be considered
       for running with the global commands
    """
    text = CommandCatcher.start.match(self.command_input).group(1)
    parts = text.split()
    name = parts[0]
    arg = ' '.join(parts[1:])
    matching = []
    for (cmd) in MetaCommand.all + extra_commands:
      if (cmd.command == name):
        matching.insert(0, cmd) # perfect matches go first
        break # and we will always use them
      elif (cmd.command.startswith(name)):
        matching.append(cmd)

    self.text = None
    if (matching):
      return (name, matching[0], arg)
    else:
      return (name, None, None)

  def apply_command(self, sess):
    """callback with a session that tells us to execute the last command"""
    # build a list of commands private to the session/mode
    extra_commands = sess.commands
    if (sess.mode):
      extra_commands += sess.mode[0].commands
    # and check out the text from parse()
    (name, command, arg) = self.parse_command_input(extra_commands)
    if (not command):
      sess.ui.write("# ERROR, no command named '%s'\n" % (name))
    else:
      command._do_command(sess, command.command, arg) # session, full command name, arg
    return

class Command(object):
  __metaclass__ = MetaCommand
  """The base Command class
  To define a command, inherit Command and define a do_command function in
  that class.  By default it will be called with one arg,"""
  arg_parse = None # defaults to whole line
  private = 0 # defaults to globally defined
  def _do_command(cls, session, cmd, line):
    """do arg parsing here"""
    if (cls.arg_parse is None):
      args = [line]
    else:
      m = cls.arg_parse.match(cls.arg_parse)
      args = m.groups()
    cls.do_command(session, *args)
    return
  _do_command = classmethod(_do_command)

class DefendTypeFindItem(Command):
  command = 'titem'
  def do_command(sess, loc):
    printem = []
    for (ob) in sess.mud.items.litems:
      if (isinstance(ob, item.Armor)):
        if (ob.type == loc):
          sess.interf.write.ui('%s\n' % (str(ob)))

    return

class TestDo(Command):
  command = 'tdo'
  
  def do_command(sess, do_this):
    cobs = [catcher.Stats(count=2,muffle=1), catcher.Spells(count=2,muffle=1), catcher.Skills(count=2,muffle=1)]
    for (ob) in cobs:
      sess.interf.catch.add(ob)
    def show_deltas():
      all_deltas = []
      for (ob) in cobs:
        all_deltas.extend(ob.deltas())
      for (name, new, old) in all_deltas:
        sess.interf.write.ui('%s %d %s\n' % (name, int(new), libmisc.color_delta(int(new) - int(old))))
      return
    
    cobs[-1].add_callback(show_deltas) # show the deltas after the last has been caught
    do_cmds = ";".join(map(lambda x:x.command, cobs) + ['glance'])
    sess.interf.write.mudraw(do_cmds)
    sess.interf.write.mudraw(do_this)
    sess.interf.write.mudraw(do_cmds)
    return

class GC(Command):
  command = 'garbage'
  def do_command(sess, arg):
    cnt = gc.collect()
    sess.ui.write("%d were collected\n" % (cnt)) # use the bare lyntin interface, we're doing lowlevel crap

class Alias(Command):
  command = 'alias'
  def do_command(sess, arg):
    parts = arg.split()
    name = parts[0]
    UnAlias.do_command(sess, name, silent=1)
    expands_to = arg[len(name)+1:]
    sess.ocatch.add(catcher.Alias(alias_from=name, alias_to=expands_to))
    return

class UnAlias(Command):
  command = 'unalias'
  def do_command(sess, name, **opts):
    defaults = {'silent':0}
    defaults.update(opts)
    # make an alias to compare it to
    like = catcher.Alias(alias_from=name, alias_to='dummy')
    for (ob) in sess.ocatch.obs:
      try:
        if (ob == like):
          sess.ocatch.rm(ob)
          if (not defaults['silent']):
            sess.ui.write("#unalias: '%s' removed\n" % (name))
          break
      except AttributeError: pass # wasn't an alias
    else:
      if (not defaults['silent']):
        sess.ui.write("#unalias WARNING: no alias named '%s'\n" % (name))
    return

class DoPath(Command):
  command = 'dp'

  _walk_re = re.compile('(\d*)([\s\w]+)')
  last_moves = []
  def do_command(sess, arg):
    parts = arg.split(',')
    for (part) in parts:
      m = DoPath._walk_re.match(part)
      if (m):
        (cnt, cmd) = m.groups()
        if (cnt):
          cnt = int(cnt)
        else:
          cnt = 1
      else:
        cnt = 1
        cmd = part
      for (c) in [cmd] * cnt:
        DoPath.last_moves.append(c)
        sess.sock.write('%s\n' % (c))
    DoPath.last_moves = DoPath.last_moves[-10:]

class Read(Command):
  command = 'read'
  def do_command(sess, filename):
    try:
      fob = open(filename)
    except IOError:
      sess.ui.write("Couldn't open '%s' for reading\n" % (filename))
      return
    for (line) in fob:
      line = line.strip()
      sess.ocatch.line(line)
    return
                    
          
class ReMatchTrig(Command):
  command = 'rtrig'
  arg_parse = TWO_ARGS

  def do_command(sess, match_re, action):
    class AnonCatcher(catcher.Catcher):
      start = re.compile(match_re)
      end = start
    cob = AnonCatcher(listen=1)
    def trig_func():
      sess.to_mud(action + "\n")
      return
    cob.add_callback(trig_func)
    sess.icatch.add(cob)

class AreYouThere(Command):
  command = 'ayt'
  def do_command(sess, line):
    import rtelnetlib as rt
    ayt = rt.IAC + rt.AYT
    sess.sock.rawwrite("%s gl\n%s gl\n%s " % (ayt, ayt, ayt))
    return

class SBTest(Command):
  command = 'sbtest'
  def do_command(sess, line):
    import rtelnetlib as rt
    ayt = rt.IAC + rt.SB + rt.MCCP2 + 'asdf' + rt.IAC + rt.SE
    sess.sock.rawwrite(ayt)
    return

class TestColor(Command):
  command = 'testcolor'
  def do_command(sess, line):
    color_re = re.compile('^(\w+)\s+(\w+)')
    (fg, bg) = color_re.match(line).groups()
    sess.ui.write(repr((fg, bg)), fg=fg, bg=bg)
