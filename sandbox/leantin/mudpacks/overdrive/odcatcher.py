# python imports
import re
# our imports
import libmisc
from catcher import Catcher
import catcher

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

class TooHeavy(Catcher):
  start = re.compile('.*?: Too heavy\.$')
  end = start

  def parse(self, lines):
    return


class Vitals(Catcher):
  all_kinds = '(?:(?:SOUL)|(?:END)|(?:ENERGY)|(?:MANA))'
  start = re.compile('-=>\s+HP:\s+(\d+)/(\d+)\s+%s:\s+(\d+)/(\d+)\s+EXP:\s+(\d+)/(\d+)\s+<=-' % (all_kinds))
  end = start
  #manual_vitals = re.compile('HP\s+:\s+(\d+)\s+(\d+)\s+%s\s+:\s+(\d+)\s+(\d+)()()' % (all_kinds))
  statl = ('hp', 'max_hp', 'mp', 'max_mp', 'exp', 'next_level', 'to_level')
  def __init__(self, **opts):
    Catcher.__init__(self, **opts)
    self.stats = {}
    self.old = {}
    self.output = None
    for (stat) in Vitals.statl:
      self.stats[stat] = 0
      self.old[stat] = 0

  def update_stat(self, name, value):
    self.old[name] = self.stats[name] # push old value
    self.stats[name] = value
    self.stats['to_level'] = self.stats['next_level'] - self.stats['exp'] # be lazy, update regardless
    return

  def change(self, stat):
    return self.stats[stat] - self.old[stat]

  def bump_changed(self):
    answer = self.change('mp') or self.change('hp') or self.change('exp')
    return answer
  
  def __str__(self):
    new_line = 'HP: %s/%d (%s) SOUL: %s/%3d (%s) EXP: (%s)\n' % (
      libmisc.color_bold(self.stats['hp']), self.stats['max_hp'], libmisc.color_delta(self.change('hp')),
      libmisc.color_bold(self.stats['mp']), self.stats['max_mp'], libmisc.color_delta(self.change('mp')),
      libmisc.color_delta(self.change('exp')),
    )
    return new_line

  def parse(self, lines):
    txt = lines[0]
    m = self.start.search(txt)
    for (stat_name, value) in zip(Vitals.statl, map(int, m.groups())):
      self.update_stat(stat_name, value)
    # set our output that will be used in filter
    self.output = str(self)
    # if we haven't changed, change ourselves to MUFFLE, else FILTER
    if (not self.bump_changed()):
      self.action = catcher.MUFFLE
    else:
      self.action = catcher.FILTER

  def done(self): pass
