# python imports
import re
# our imports
import libmisc
# lyntin imports

"""Some basic classes that know how to read, and possibly swallow output
   Cather: a class the takes input to be acted on, listened to, or munged
   CatchQueue: a class that takes input and passes it on to Catchers, it also manages the actions for Catchers

   They share a common subset of functions, so a CatchQueue can also pass on events to other CatchQueues
   it is managing just like Catchers.  This lets you make CatchQueues for specific purposes, like per-monster
   or per-mode that have a longer lifespan than Catcher objects, but you still want to add/expire
"""

class Caught(Exception): pass
class Begun(Caught): pass
class Done(Exception): pass
class DoneEarly(Done): pass
class DoneReparse(Done): pass # also go back and rerun the queue, we changed stuff

END_CALLBACK = 1
BEGIN_CALLBACK = 2

PASS = 0
FILTER = 1
MUFFLE = 2

class NullRE(object):
  """An object that has the re interface that never matches anything"""
  def match(self, *args):
    return None
  def search(self, *args):
    return None
  def finditer(self, *args):
    return []
  def findall(self, *args):
    return []

class CatchQueue(object):
  def __init__(self):
    self.prioritized_obs = []
    return
  def add(self, ob, priority = 100):
    self.prioritized_obs.append((priority, ob))
    self.prioritized_obs.sort(lambda a,b:cmp(a[0],b[0]))
    return

  def _list_obs(self):
    return map(lambda x:x[1], self.prioritized_obs)
  obs = property(_list_obs)

  def rm(self, ob):
    self.prioritized_obs = filter(lambda x:id(x[1])!=id(ob), self.prioritized_obs)
    return
  
  def input_many(self, lines):
    """Like input(), but never returns a value"""
    for (line) in lines:
      self.input(line)
    return
  
  def input(self, line):
    ret = None
    action = PASS
    consume = []
    output = None
    reparse = 0
    for (ob) in self.obs:
      try:
        ob.line(line)
        continue
      except (Done,), e:
        ob.count -= 1
        if (ob.count == 0 or isinstance(e, DoneEarly)):
          self.rm(ob)
        ob._do_end_callbacks()
        if (isinstance(e, DoneReparse)):
          reparse = 1
      except (Caught,), e: pass

      if (output is None):
        if (ob.action == MUFFLE):
          output = ''
        elif (ob.action == FILTER):
          output = ob.output
      action = max(action, ob.action)

    if (output is not None): # MUFFLE'd or FILTER'd
      final = output
    else: # wasn't modified
      final = line
    if (reparse):
      return self.input(final)
    else:
      return final

  def func_expirations(self, func_name):
    consume = []
    for (i, ob) in enumerate(self.obs):
      try:
        func = getattr(ob, func_name)
        func()
        continue
      except (Done,), e:
        ob.count -= 1
        if (ob.count == 0 or isinstance(e, DoneEarly)):
          self.rm(ob)
        ob._do_end_callbacks()
      except (Caught,), e: pass

  def __len__(self):
    return len(self.obs)

  def tick_tock(self):
    self.func_expirations('tick_tock')
    return
  
  def bump_tock(self):
    self.func_expirations('bump_tock')
    return

  def __str__(self):
    outstr = "%s:%d\n" % (self.__class__.__name__, id(self))
    for (ob) in self.obs:
      outstr += "   %s\n" % (str(ob))
    return outstr

  def suicide(self):
    for (ob) in self.obs:
      ob.suicide()
    self.prioritized_obs = []
    return

class Catcher(object):
  debug = 1
  def __init__(self, **opts):
    # calc pass-through or muffle
    self.action = PASS
    if ('muffle' in opts and opts['muffle']):
      self.action = MUFFLE
    elif ('filter' in opts and opts['filter']):
      self.action = FILTER

    # calc listen always, or just X times
    if ('listen' in opts):
      self.count = -1 # means never expire
    elif ('count' in opts):
      self.count = opts['count']
    else:
      raise Exception("Must pass 'count' or 'listen' to constructor")
      
    self.data = libmisc.DeltaDict()
    self.__callbacks = []
    # proper values for these next two are set in _reset()
    self.__line = None
    self.__text = None
    self.__expire_seconds = 60 * 5 # default to five minutes
    self.__expire_bumps = 60 / 2 * 5 # default to five minutes
    self.output = None
    self.debug = 0
    self._reset()
    return

  def _reset(self):
    self.__line = 0
    self.__text = []
    return
  
  def clean_line(self, text):
    """provide a default line cleaner"""
    return text.strip()
  
  def line(self, text):
    self.output = None
    if (self.debug): print "Intext '%s'" % (text.strip())
    if (self.start.match(text)):
      if (self.debug): print self, "START MATCH"
      text = self.clean_line(text)
      if (text):
        self.__text.append(text)
      self.__line += 1
      self._do_begin_callbacks()
    elif (self.__line > 0):
      if (self.debug): print self, "CONTINUE MATCH"
      text = self.clean_line(text) # do a little cleanup
      if (text): # non-empty line, 
        self.__text.append(text)
      self.__line += 1
    else:
      if (self.debug): print "Didn't match start"
      return

    # start end and could be the same line
    
    # we give them a few options for announcing "DONE"
    # 1) line count
    is_done = 0
    if (hasattr(self, 'expects')):
      if (self.__line >= self.expects):
        if (self.debug): print self, "EXPECTS END"
        is_done = 1
      else:
        if (self.debug): print self, "EXPECTS MISSED"
    # 2) 'end' regexp
    elif (hasattr(self, 'end')):
      if (self.end.search(text)):
        if (self.debug): print self, "END END"
        is_done = 1
      else:
        if (self.debug): print self, "END MISSED"
    # 3) 'finished' func which returns true the line _after_ it is done
    elif (hasattr(self, 'finished')):
      answer = self.finished(text)
      if (answer is not None):
        if (self.debug): print self, "FINISHED() END"
        is_done = 1 + answer # True + X lines to pop
      else:
        if (self.debug): print self, "FINISHED() MISSED"
    else:
      raise Exception("Catcher object has no way to end!")
    
    if (is_done):
      for (dummy) in range(is_done - 1): # pop this many lines, we might have overshot
        self.__text.pop()
      self.parse(self.__text) # may throw DoneEarly() to force consumption
      self._reset()
      raise Done()
      
    raise Caught()

  def add_callback(self, func, **opts):
    calltype = END_CALLBACK
    if ('type' in opts):
      calltype = opts['type']
    priority = 0
    if ('priority' in opts):
      priority = opts['priority']
    
    assert(calltype == BEGIN_CALLBACK or calltype == END_CALLBACK)
    self.__callbacks.append((priority, func, calltype))
    self.__callbacks.sort() # sorts by priority
    return

  def clear_callbacks(self):
    self.__callbacks = []
    return

  def rm_callback(self, func):
    self.__callbacks = filter(lambda x:x[1]==func, self.__callbacks)

  def _do_begin_callbacks(self):
    for (dummy, func, dummy) in filter(lambda x:x[2] == BEGIN_CALLBACK, self.__callbacks):
      func()

  def _do_end_callbacks(self):
    for (dummy, func, dummy) in filter(lambda x:x[2] == END_CALLBACK, self.__callbacks):
      func()

  def __str__(self):
    out = "%s:%d|%d|%s" % (self.__class__.__name__, self.count, len(self.__text), id(self))
    for (k, v) in self.data.items():
      out += "%s:%s," % (str(k), str(v))
    if (self.debug):
      out += "TEXT:" + str(self.__text)
    return out

  def __getitem__(self, k):
    return self.data[k]

  def __contains__(self, k):
    return (k in self.data)

  def deltas(self):
    return self.data.changed_tuples()

  def suicide(self):
    """arrange for ourselves to be removed at the next pass"""
    self.start = re.compile('.') # match anything
    self.expects = -1
    def parse_die(*args): # always expire if we are called
      raise DoneEarly()
    self.parse = parse_die
    self.clear_callbacks()
    return
  done = suicide

  def tick_tock(self):
    """put ourselves one second closer to timing out"""
    if (hasattr(self, 'i_handle_my_own_timeouts')):
      # apparently they handle their own timeouts, natch
      return
    if (self.count < 0): # listen forever
      return
    
    self.__expire_seconds -= 1
    if (self.__expire_seconds <= 0):
      self.suicide()
    return

  def bump_tock(self):
    """put ourselves one second closer to timing out"""
    if (hasattr(self, 'i_handle_my_own_timeouts')):
      # apparently they handle their own timeouts, natch
      return
    if (self.count < 0): # listen forever
      return
    
    self.__expire_bumps -= 1
    if (self.__expire_bumps <= 0):
      self.suicide()
    return

  def _peek_text(self):
    return self.__text


class Skills(Catcher):
  command = 'skills'
  start = re.compile('\s*-*<\s*SKILLS\s*>-*')
  _skill_re = re.compile('([-\w!]+)\s*:\s*([\d\w!-]+)\s*', re.DOTALL|re.MULTILINE)
  finished = 'NB: actually defined below, this is just a reminder'

  def __init__(self, **opts):
    Catcher.__init__(self, **opts)
    self.pending_done = 0

  def finished(self, line):
    """called for every line, return true on the line _after_ we are done"""
    if (Skills._skill_re.match(line)):
      self.pending_done = 1
    elif (self.pending_done):
      self.pending_done = 0 # reset, this ob may be reused
      return 1
    return None
  
  def clean_line(self, text):
    return text

  def parse(self, text):
    alltxt = ''.join(text)
    for (m) in Skills._skill_re.finditer(alltxt):
      (skill, val) = m.groups()
      try:
        val = int(val)
      except (ValueError,):
        val = -1
      self.data[skill] = int(val)
    return

class Spells(Skills):
  command = 'spells'
  _priest_spells = '(?:Gifts you may request from Llardin)'
  _thief_spells = '(?:TALENTS)'
  _fighter_spells = '(?:TALENTS)' # redundant, included for completeness
  _mage_spells = '(?:SPELLS)'
  
  start = re.compile('^\s*-------<\s*(?:%s|%s|%s|%s)\s*>-------' % (_priest_spells, _thief_spells, _fighter_spells, _mage_spells))

class Stats(Skills):
  command = 'stats'
  start = re.compile('^\s+-------< STATS >-------')
  long_to_short = dict((('Strength', 'str'),
                        ('Intelligence', 'int'),
                        ('Wisdom', 'wis'),
                        ('Dexterity', 'dex'),
                        ('Constitution', 'con'),
                       )
                      )

  def parse(self, text):
    """Use the base Skills.parse() but translate the stat names"""
    Skills.parse(self, text)
    for (long, short) in Stats.long_to_short.items():
      if (long in self.data):
        self.data[short] = self.data[long]
        del self.data[long]
    return

class Armors(Catcher):
  command = 'armors'
  expects = 14
  start = re.compile('^You are wearing the following armor types')
  _std_re = re.compile('^\s*(\w+)\s*:\s*(.*)\s*$')
  def __init__(self, **opts):
    Catcher.__init__(self, **opts)
    self.maybe_ring = 0
    return

  def line(self, text):
    m = Armors._std_re.match(text)
    if (m and m.group(1) == 'ring'):
      self.maybe_ring = 1
    elif (not m and self.maybe_ring): # workaround since the number of lines can be +1 for two rings
      self.expects = self.expects + 1
      self.maybe_ring = 0
    return Catcher.line(self, text)
  
  def parse(self, text):
    ring = 0
    for (line) in text[1:]: # skip top sigil line
      m = Armors._std_re.match(line)
      if (m):
        (loc, item) = m.groups()
      else:
        item = line.strip()
      if (item == '<none>'):
        item = None
      if (loc == 'ring'): # 'loc' will be 'ring' even for the second (and blank) ring line
        self.data['%s%d' % (loc, ring)] = item
        ring += 1
      else:
        self.data[loc] = item
    return

class Score(Catcher):
  command = 'score'
  expects = 18
  start = re.compile('^----------------------------------------------------------------------')
  _split_re = '((?:\w+)|(?:\w+\s+\w+))\s*:\s*(.*)'
  _split_re = re.compile('%s\s+%s' % (_split_re, _split_re))

  def parse(self, text):
    ignore = ('hp', 'soul', 'satiation', 'intoxication')
    for (line) in text:
      m = Score._split_re.match(line)
      if (not m):
        continue
      parts = m.groups()
      print "PARTS", parts
      for (i) in range(0, len(parts), 2):
        (name, value) = map(lambda x:x.strip().lower(), parts[i:i+2])
        if (name not in ignore):
          self.data[name] = value
    return

class Report(Catcher):
  """Report:  
You are surrounded by a magical force.
The world is extremely blurry.
   Resistance: inactive

   Weapons:
"""
  def boobies(self): pass

def test_catch(cob, lines):
  c = CatchQueue()
  c.add(cob)
  for (line) in lines:
    c.input(line)
  return

class Who(Catcher):
  command = 'who'
  start = re.compile(r'^\s*/-+\\') # looks like '/---------------\'
  _bumper = re.compile(r'^\s*\\-+/') # looks like '\---------------/'
  def __init__(self,**opts):
    Catcher.__init__(self, **opts)
    self.seen_once = 0
    self.curr_line = 0
    return
  def finished(self, line):
    self.curr_line += 1
    ret = None
    if (Who._bumper.match(line)):
      if (self.seen_once):
        ret = 0 # this means finished (non-None)
      else:
        self.seen_once = 1
    elif (self.curr_line == 2): # it didn't match the bumper, must be something else
      ret = self.curr_line # give back all the lines
    if (ret is not None):
      self.curr_line = 0
      self.seen_once = 0
    return ret

  def parse(self, lines):
    classes = dict((('Fighters','Fighter'),
                    ('Mages', 'Mage'),
                    ('Thieves','Thief'),
                    ('Priests', 'Priest'),
                    ('Overdrivers', 'Overdriver'),
                    ('Total', 'Ignored'),
                  ))
    name_level = re.compile('^\s*(\w+)\s+[^\[]*\[(\d+)')
    name_only = re.compile('^\s*(\w+)\s+()')
    current_class = None
    for (line) in lines:
      t = name_level.match(line)
      if (t and t.group(1) in classes):
        current_class = classes[t.group(1)]
        continue
      
      for (guy) in (name_level, name_only):
        m = guy.match(line)
        if (m):
          (name, level) = m.groups()
          if (level):
            level = int(level)
          else:
            level = 0
          self.data[name] = (current_class, level)
          break
    self.seen_once = 0
    self.curr_line = 0

class Cost(Catcher):
  start = re.compile('The cost to raise your (.*?) from (\d+) to (\d+) is (\d+) experience points')
  expects = 1
  
  def parse(self, lines):
    line = lines[0] # always only 1
    (what, curr, to, exp)
    self.data[what] = (curr, to, exp)
    return

class CallAndResponse(object):
  def __init__(self, call, response):
    self.call = call
    self.response = response
    return
  def raw_input(self, text):
    if (text.find(self.call) != -1):
      return self.response
    else:
      return None

class Alias(Catcher):
  def __init__(self, **opts):
    Catcher.__init__(self, listen=1, filter=1)
    self.fromthis = opts['alias_from']
    self.tothis = opts['alias_to']
    self.start = re.compile('^%s(.*)' % (self.fromthis))
    self.end = self.start
    return
  def parse(self, lines):
    text = "\n".join(lines)
    m = self.start.match(text)
    self.output = self.tothis + m.group(1) + "\n"
    raise DoneReparse()

  def __eq__(self, other):
    if (isinstance(other, Alias) and self.fromthis == other.fromthis):
      return 1
    else:
      return 0

class TooHeavy(Catcher):
  start = re.compile('.*?: Too heavy\.$')
  end = start

  def parse(self, lines):
    return
