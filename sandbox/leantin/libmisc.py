from __future__ import generators
import UserDict, time, os, os.path

try:
  from Tkinter import *
  import tkFont
  from ScrolledText import ScrolledText
except: pass

def space_to_respace(regexp):
  """take a regexp string like 'Hi Mom!' and change it to 'Hi\s+Mom!'"""
  parts = regexp.split(' ')
  return r"\s+".join(parts)

class DeltaDict(UserDict.UserDict):
  random = 'asdf'
  
  def __init__(self, *args, **opts):
    UserDict.UserDict.__init__(self, *args, **opts)
    self.origdata = {}
    return

  def __setitem__(self, name, val):
    try:
      self.origdata[name] = self.data[name]
    except (KeyError,): pass
    
    self.data[name] = val
    return self.data[name]

  def delta_num(self, name):
    return (int(self.data[name]) - int(self.origdata[name]))

  def delta_pair(self, name):
    return (self.data[name], self.origdata[name])

  def changed_tuples(self):
    """return a list of tuples of (name, curr_value, old_value)
       for any item that has ever changed"""

    changes = []
    for (k) in self.data.keys():
      if (k in self.origdata and self.data[k] != self.origdata[k]):
        changes.append((k, self.data[k], self.origdata[k]))
    return changes

class LineBuffer(object):
  def __init__(self, **opts):
    self.pending = '' # incoming data, possibly without terminating newlines
    self.prompt = opts.get('prompt', None)
    return

  def add(self, inp):
    """figure out where the newlines are, return any new full lines"""
    self.pending += inp.replace('\r', '') # might screw windows folk, I'm OK with that.
    parts = self.pending.split('\n')
    self.pending = parts[-1] # likely empty
    for (newline) in parts[:-1]:
      if (self.prompt is not None and newline.startswith(self.prompt)):
        newline = newline[len(self.prompt):]
      yield newline+"\n" # restore the newline
    return

def color_delta(amt):
  escape = chr(27)
  color = '[0m'
  text = str(amt)
  if (amt > 0):
    color = '[32m'
    text = '+' + text
  elif (amt < 0):
    color = '[31m'
  return escape + color + text + escape + '[0m'

def color_bold(text):
  escape = chr(27)
  return escape + '[1m' + str(text) + escape + '[0m'

class Cron(object):
  """A little class that will run jobs every so often"""
  class Crony(object):
    """A helper class for crons"""
    def __init__(self, func, secs, name):
      self.func = func
      self.seconds = secs
      self.counter = 0
      self.name = name
      return
    def tick_tock(self, elapsed):
      self.counter += elapsed
      if (self.counter >= self.seconds):
        self.func()
        self.counter = 0.0
      return
    def __str__(self):
      return "%s:%s %s every %d" % (self.__class__.__name__, id(self), str(self.func), self.seconds)
  # end class Crony()
  def __init__(self):
    self.__obs = []
    self.last = time.time()
    return
  
  def add(self, func, every_x_seconds, name = None):
    self.__obs.append(Cron.Crony(func, every_x_seconds, name))
    return
  def rm_by_func(self, func):
    self.__obs = filter(lambda x:x.func != func, self.__obs)
    return
  def rm_by_name(self, name):
    self.__obs = filter(lambda x:x.name != name, self.__obs)
    return
  def tick_tock(self):
    new = time.time()
    elapsed = new - self.last
    self.last = new
    for (ob) in self.__obs:
      ob.tick_tock(elapsed)

  def sess_init(self, sess): pass

  def __str__(self):
    outstr = "%s:%d\n" % (self.__class__.__name__, id(self))
    for (ob) in self.__obs:
      outstr += "   %s\n" % (str(ob))
    return outstr

  def done(self):
    self.__obs = []

class Bump(Cron):
  """Like cron, but time is counted in mud bumps instead"""

try:
  l = enumerate(range(3))
except:
  def enumerate(l):
    for (pair) in zip(range(len(l)), l):
      yield pair
    return

def tk_scroll(text, title = 'Help'):
  win = Tk()

  fnt = tkFont.Font(family="Fixedsys", size=12)
  fnt = tkFont.Font(family="Courier", size=12)
  
  scroll = ScrolledText(win, fg='white', bg='black', font=fnt, height=20)
  scroll.pack(side=BOTTOM, fill=BOTH, expand=1)
  scroll.insert('end', text)
  Button(win, text='OK', command=win.destroy).pack(side=BOTTOM)
  win.title(title)
  return win

class Register(type):
  """A tiny metaclass to help classes register themselves automagically"""

  def __init__(cls, name, bases, dict):
    if ('register' in dict): # initial dummy class
      setattr(cls, 'register', staticmethod(dict['register']))
    elif (getattr(cls, 'DO_NOT_REGISTER', 0)): # we don't want to register this non-concrete class
      delattr(cls, 'DO_NOT_REGISTER')
    elif (object not in bases):
      cls.register(name, cls)
    return

def rotate_logs(canonical_name):
  """if there is a file where canonical_name is, rename it to name.1
     while first moving name.2 to name.3, etc"""
  def make_name(name, i):
    if (i == 0):
      return name
    else:
      return '%s.%d' % (name, i)

  # first find the lowest number not taken
  i = 0
  done = 0
  while (not done):
    try:
      test_exist = file(make_name(canonical_name, i))
      i += 1
    except IOError:
      done = 1

  if (i == 0): # nothing to do
    return
  
  # now rotate old logs
  while (i > 0):
    os.rename(make_name(canonical_name, i-1),
              make_name(canonical_name, i))
    i -= 1
  return

class Flag(object):
  """Flag objects are used to share true/false flags like 'shutdown'
     fob = Flag()
     fob.flag_true() # set the flag (and children) to true
     fob.flag_false() # set the flag (and children) to ture
     kid = Flag()
     fob.also_flag(kid)
     fob.flag_true() # fob and kid are set to true
  """
  def __init__(self):
    self.value = 0
    self.children = []
    return
  def __nonzero__(self):
    return self.value

  def also_flag(self, guy):
    self.children.append(guy)
    return

  def flag_true(self):
    self.value = 1
    for (child) in self.children:
      child.flag_true()
    return
  def flag_false(self):
    self.value = 0
    for (child) in self.children:
      child.flag_false()
    return

def ensure_path_built(pathname):
  """for the given pathname, create the directories if they do not already exist"""

  # common case, see if the whole thing already exists
  if (os.access(pathname, os.R_OK)):
    return

  path = os.path.normpath(pathname) # remove redundant slashes
  try:
    os.mkdir(path, 0770)
  except (OSError,):
    (subdir, dummy) = os.path.split(path)
    ensure_path_built(subdir) # recurse down our subdirs
    os.mkdir(path, 0770) # if it fails again, allow the error to propagate

  return
