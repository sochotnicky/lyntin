# python imports
import re
# our imports
import catcher, libmisc

"""The basic module for all spells
   NB: we get classes inserted into this namespace from magespells (and priest-specific spells might move out of here sometime as well)
"""

class Expired(Exception): pass
class TimedOut(Expired): pass

def filter_regexps(string):
  if (not string or string.find('INVALID') != -1):
    return 0
  else:
    return 1
    
def multi_match(*l):
  l = filter(filter_regexps, l)
  if ('.' in l):
    myre = '.'
  else:
    myre = '^\s*(?:%s)' % ('|'.join(map(lambda x:'(?:%s)' % (libmisc.space_to_respace(x)), l)))
  return myre

def compile_multi_match(*l):
  l = filter(filter_regexps, l)
  if ('.' in l):
    l = ['.']

  if (not l):
    return catcher.NullRE() # object that never matches anything

  if (len(l) == 1):
    return re.compile(l[0])
  else:
    myre = '^\s*(?:%s)' % ('|'.join(map(lambda x:'(?:%s)' % (libmisc.space_to_respace(x)), l)))

  return re.compile(myre)

class SpellCatchQueue(catcher.CatchQueue):
  """Actually just a CatchQueue, we subclass to make debugging output more obvious"""

class SpellQueue(object):
  """For casting spells we need to know three things
     1) When a turn bump happened
     2) When the spell was actually cast
     3) How many bumps the spell keeps us busy

     This object also takes priorities for spells and
     keeps some SPs in reserve.  All spells are cast
     in their priority order, lower is better.  If a
     spell has a negative priority it will be cast as
     long as we have enough sps.  Positive priority
     spells are only cast when we have enough to cast
     them and still be above our safety margin

     We do not keep spell state, that is up to the
     individual spell objects
  """

  class Engaged(catcher.Catcher):
    _engaged = "You're already engaged this round"
    _no_sps_priest = "You don't have the piety to request this gift" # this should come from the player class
    _no_sps_mage = "You don't have the spell points to cast this spell"
    start = compile_multi_match(_engaged, _no_sps_priest, _no_sps_mage)
    end = start
    def parse(self, lines): pass
  
  def __init__(self, safety):
    self._queue = [] # waiting to be cast
    self._pending = [] # we sent the command, did it happen?
    self.active = [] # spells currently running
    self.busy = 0
    self.safety = safety
    self.already_casting = 0 # only try to start a spell once a round
    self.engaged = None
    self.catch = None
    return

  def done(self):
    for (ob) in (map(lambda x:x[1], self._queue) + self._pending + self.active):
      ob.done()
    return

  def sess_init(self, sess):
    """gives us a chance to hook on to a listener"""
    if (self.engaged is not None):
      self.engaged.suicide()

    #self.catch = SpellCatchQueue()
    #sess.interf.catch.add(self.catch) # add our queue to the listeners

    self.engaged = SpellQueue.Engaged(listen=1)
    self.engaged.add_callback(self._engaged_cast)
    sess.interf.catch.add(self.engaged)

  def __contains__(self, spellname):
    for (priority, ob) in self._queue:
      if (ob.cast == spellname):
        return 1
    for (ob) in self._pending:
      if (ob.cast == spellname):
        return 1
    return 0

  def __len__(self):
    return len(self._queue) + len(self._pending)
  
  def cast(self, spell, priority):
    spell.priority = priority
    self._queue.append((priority, spell))
    self._queue.sort()
    return
  
  def turn_bump(self, sess):
    self.already_casting = 0
    if (self.busy > 3 and self.busy < 50): # cheese to defend against false positive regexp matches, allow it to be set high for 'pause' effects
      self.busy = 3
    if (self.busy):
      self.busy -= 1
    self.consider_casting(sess)
    self.turn_bump_actives(sess)
    return
  
  def turn_bump_actives(self, sess):
    """Let all active spells know a bump has gone by,
    this gives them a chance to timeout"""
    consume = []
    for (i, sp) in enumerate(self.active):
      try:
        sp._turn_bump() # collusion, Spell._turn_bump calls the overriden spellob.turn_bump()
      except (Expired,):
        consume.append(i)
    consume.reverse()
    for (i) in consume:
      self.active.pop(i)
    return

  def consider_casting(self, sess):
    """check the spell queue and consider if we can afford to cast the top priority spell"""
    if (self.already_casting):
      return

    if (not self.busy and self._queue): # we have stuff we want to cast
      (priority, sp) = self._queue[0]

      # figure out if we can cast it
      if (priority < 0 and sess.player.vitals.stats['mp'] > sp.cost): # urgent spell and we have the sps
        cast_it = 1
      elif (priority > 0 and (sess.player.vitals.stats['mp'] - self.safety) > sp.cost): # we can cast and keep our safety margin
        cast_it = 1
      else: # no dice
        cast_it = 0

      if (cast_it):
        self.already_casting = 1
        (dummy, spell) = self._queue.pop(0) # take first spell
        # setup the callback so we know when the spell _actually_ starts
        # set a high priority so the queue must update our status before other callbacks can examine it and us
        spell.add_callback(lambda :self._started_cast(spell), priority=-10)
        self._pending.append(spell)
        sess.interf.catch.add(spell)
        sess.interf.write.mudraw(spell.cast)
    return


  def would_cast(self, sess, spob):
    """check the spell queue and consider if we can afford to cast the top priority spell"""
    if (self.already_casting or self.busy):
      return 0

    if (self._queue and spob.priority > self._queue[0][0]):
      return 0

    if (spob.priority < 0 and sess.player.vitals.stats['mp'] > spob.cost): # urgent spell and we have the sps
      return 1
    elif (spob.priority > 0 and (sess.player.vitals.stats['mp'] - self.safety) > spob.cost): # we can cast and keep our safety margin
      return 1

    return 0

  def _started_cast(self, spell):
    try:
      if (spell.result == 'expired'):
        return
    except AttributeError: pass

    if (spell.result == 'failure'):
      busy_len = spell.failure_length
    elif (spell.result == 'notarget'):
      busy_len = spell.notarget_length
    elif (spell.result == 'already'):
      busy_len = spell.already_length
    else: # success or unknown
      busy_len = spell.cast_length
    self.busy += busy_len
    
    anymatch = filter(lambda x:x.cast == spell.cast, self.active)
    if (not anymatch):
      self.active.append(spell)

    self._pending = filter(lambda x:x != spell, self._pending)
    return

  def _engaged_cast(self):
    """put all the pendings back in the queue"""
    for (sp) in self._pending:
      self.cast(sp.fresh_copy(), sp.priority)
      sp.suicide()
    self._pending = []
    return

  def __str__(self):
    short = '%s:%d busy: %d, already cast %d\n' % (self.__class__.__name__, id(self), self.busy, self.already_casting)
    for (sp) in self._queue:
      short += ' que:%s\n' % (str(sp))
    for (sp) in self.active:
      short += ' act:%s\n' % (str(sp))
    i = 0
    for (sp) in self._pending:
      short += ' pen%d:%s\n' % (i, str(sp))
      i += 1
    return short

  def clear_n(self, n):
    try:
      self._pending.pop(n)
    except: pass

  def clear_all(self):
    self._pending = []
    self._queue = []

  def status_str(self):
    q = ', '.join(map(lambda x:x[1].cast, self._queue))
    short = '%s: busy %d, acast %d [%s]\n' % (self.__class__.__name__, self.busy, self.already_casting, q)
    return short

def compile_re(regexp, flags = re.MULTILINE|re.DOTALL):
  regexp = libmisc.space_to_respace(regexp)
  return re.compile(regexp, flags)
  
class SpellMeta(type):
  def __init__(cls, name, bases, dict):
    if (hasattr(cls, 'IGNOREME')):
      delattr(cls, 'IGNOREME')
      return
    
    # compile all the regexps
    real_start = []
    for (member) in ('failure', 'already', 'notarget', 'success', 'expire', 'dispel', 'report'):
      v = getattr(cls, member, None)
      if (v is None):
        setattr(cls, '%s_comp' % (member), catcher.NullRE())
        continue
      
      if (type(v) == type('string')):
        real_start.append(v)
        rev = compile_multi_match(v)
      else: # assume it is a list and combine them
        real_start.extend(v)
        rev = compile_multi_match(v)
      setattr(cls, '%s_comp' % (member), rev)

    # default all the optional busy round specs to cast_length
    for (length) in ('already_length', 'failure_length', 'notarget_length'):
      if (getattr(cls, length, None) is None):
        setattr(cls, length, cls.cast_length)
    
    setattr(cls, 'start', compile_multi_match(*real_start))
    if (not hasattr(cls, 'finished')):
      setattr(cls, 'end', cls.start) # start & finish on the same input

    setattr(cls, 'parse_re', compile_re(cls.parse_re))
  
class Spell(catcher.Catcher):
  """The spell classs is the base for combat & effect spells. The things they have in
  common is that they keep us enganged for a number of rounds, they can fail, they"""
  __metaclass__ = SpellMeta

  IGNOREME = 1 # LOUDLY announce we are an intermediate class
  
  cast_length = 1 # how many rounds this keeps us busy, 1 is the default
  already_length = None # if different from cast_length, how many rounds if there it is already going
  failure_length = None # " if failure
  notarget_length = 0 # " if notarget
  
  cast = 'SPELLNAME' # how we cast it
  cost = 0 # sps to cast
  timeout =  (15 * 60) / 2 # default timeout of 15 minutes (2 secs per bump)
  priority = "This is actually set by the spellqueue if it is used at all"
  i_handle_my_own_timeouts = 1 # a flag to catcher.Catcher that tells it we handle timeouts

  # regular expression strings (not re objects) used to figure out our state
  # if these are set to a list they will be compiled as an OR of all the strings
  failure = 'INVALID RE' # re for failed spell
  already = 'INVALID RE'
  success = 'INVALID RE'
  notarget = 'INVALID RE'
  parse_re = 'INVALID()()RE' # catch should be who and howmuch
  # the next section only applies to effect spells
  expire = None # when it expires.
  dispel = None # when it is dispelled or cleansed
  report = None # what it looks like in the report
  strengths = []
  
  def __init__(self, **opts):
    self.opts = opts.copy()
    self.priority = 10
    if ('priority' in opts):
      self.priority = opts['priority']
      del opts['priority']
    if ('target' in opts): # 'You', 'Scout', 'Fierce Rat', etc
      self.target = opts['target']
      del opts['target']
    
    catcher.Catcher.__init__(self, **opts)
    self.__timeout = self.timeout
    self.who = '?'
    self.howmuch = None
    self.result = '?'
    return

  def fresh_copy(self):
    """return a copy of us init'd with our original options"""
    return self.__class__(**self.opts)

  def _turn_bump(self):
    """SpellQueue knows to call us, we handle default timeouts and also call the
    instance turn_bump() method for the leaf classes to define"""
    
    self.__timeout -= 1
    if (self.__timeout <= 0):
      raise TimedOut()
    self.turn_bump()
    return

  def turn_bump(self): pass
  
  def parse(self, lines):
    text = "\n".join(lines)
    for (result, result_re) in (('failure', self.failure_comp),
                                ('already', self.already_comp),
                                ('success', self.success_comp),
                                ('notarget', self.notarget_comp),
                                ('expired', self.expire_comp),
                                ('expired', self.dispel_comp),
                                ('success', self.report_comp),
                               ):
      m = result_re.search(text)
      if (m):
        self.result = result
        break

    self._post_parse(text)
    return

  def _post_parse(self, text):
    print "In post_parse", self
    return self.post_parse(text)
  
  def post_parse(self, text):
    m = self.parse_re.search(text)
    if (m):
      if (len(m.groups()) == 2):
        (self.who, self.howmuch) = self.parse_re.search(text).groups()
    return
  
  def __str__(self):
    short = catcher.Catcher.__str__(self)
    short += "%s: [%s]" % (self.cast.upper(), self.result)
    if (self.strengths):
      if (self.howmuch in self.strengths):
        short + str(self.howmuch)
      else:
        short + 'UNK:' + str(self.howmuch)
    return short

  def status_str(self):
    short = "%s: " % (self.cast.upper()[:3])
    if (self.howmuch in self.strengths):
      return short + str(self.howmuch)
    else:
      return short + 'UNK:' + str(self.howmuch)

class Jinx(Spell):
  failure = 'Even as you speak them, you realize that the words of the hex twist and fail\.'
  expire = '(?:(?:A)|(?:An)|(?:The)|(?:))\s*(.*) looks much steadier on \w+ feet\.'
  already = '(?:(?:The target is already jinxed)|(?:.* too balanced to be jinxed\.))'
  success = 'You make the sign of a hex'
  parse_re = '^\s*You make the sign of a hex, and watch (.*) stagger (.*) as'
  strengths = ['somewhat', 'moderadtely', 'notably', 'horribly', 'exceptionally']
  notarget = 'Jinx what'
  cast = 'jinx'
  cost = 45
  already_length = 0 # we can still cast if they're already jinxed

class PlayerJinx(Jinx):
  """what it looks like when we're affected"""
  success = '^.*?(?:(?:hex, and you stagger\s+(\w+)))'
  expire = '^Your muscles firm up'
  def post_parse(self, text):
    self.who = 'You'
    if (self.result == 'success'):
      m = self.success_comp.search(text)
      if (m):
        self.howmuch = m.group(1)
    elif (self.result == 'expired'):
      self.howmuch = None

class Faerie(Spell):
  failure = 'Your prayers fail you\.'
  expire = '(.*) stops glowing\.'
  already = 'The creature is already affected!'
  success = '\s*You murmur a prayer, and'
  parse_re = '^\s*You murmur a prayer, and (.*) glows (.*)\.'
  strengths = ['very dimly', 'dimly', 'clearly', 'somewhat brightly', 'brightly', 'very brightly', 'extremely brightly', 'brilliantly']
  cast = 'faerie'
  notarget = 'Invalid target\.'
  cost = 35

  dispel = '^\s*You stop glowing'

class PlayerFaerie(Faerie):
  expire = '^\s*You stop glowing'
  success = '^\s*You start glowing ([\w\s]+)'
  def pose_parse(self, text):
    self.who = 'You'
    if (self.result == 'success'):
      m = self.success_comp.search(text)
      if (m):
        self.howmuch = m.group(1)
    elif (self.result == 'expired'):
      self.howmuch = None
  
class WaterBreath(Spell):
  cast = 'wb'
  cost = 50
  failure = "Llardin doesn't answer your request for aid"
  already = "Llardin is already helping you in that manner"
  success = "You feel your lungs twinge"
  notarget = 'Who\?'

class PlayerWaterBreath(WaterBreath):
  success = "Your lungs return to their air-breathing state"
  expire = "You feel the water-breathing wear off"
  dispel = "Your lungs return to their air-breathing state"

  def post_parse(self, text):
    if (self.result == 'success'):
      self.howmuch = 1
    elif (self.result == 'expired'):
      self.howmuch = 0
  
class Cleanse(Spell):
  cost = 30
  cast = 'cleanse'
  success = "Llardin's holy blessings descend"
  already = 'You call upon the cleansing powers of Llardin'
  failure = 'Nothing happens'
  notarget = 'Cleanse whom'

class Cure(Spell):
  already = 'Cure only works on physical'
  success = '\w+ (?:(?:is)|(?:are)) now' # this could be fleshed out, or not.
  success = '.'
  notarget = 'Cure whom'
  failure = 'Nothing happens'

  cost = 125
  cost = 1
  cast = 'cc;,'

class SmartCure(Cure):
  def __init__(self, **opts):
    if ('stats' in opts):
      st = opts['stats']
      del opts['stats']
      

class Boozle(Spell):
  success = "You wave your hands around and intone 'Llardin'"
  already = "[\w\s-]+.*has witnessed Llardin's terrible splendor"
  failure = 'Your prayers fail you'
  notarget = 'Boozle whom'
  
  cost = 30
  cast = 'boozle'

class SelfBoozle(Spell):
  #success = "You wave your hands around and intone 'Llardin'"
  success = '.'
  already = "[\w\s-]+.*(?:(?:has)|(?:have)) witnessed Llardin's terrible splendor"
  failure = 'Your prayers fail you'
  notarget = 'Boozle whom'
  
  cost = 1
  cost = 30
  cast = 'bb;,'

class SpiritDisease(Spell):
  success = 'You mutter a malignant prayer, and attempt to curse'
  _success = re.compile(success)
  already = 'Your attention is already occupied'
  _already_re = re.compile('^\s*%s' % (already))
  expire = '.*?collapses!$'
  _failure1 = "You call on Llardin's darker side, but"
  _failure2 = 'You try to afflict'
  _failure3 = ".*?doesn't even get a headache"
  _failure = re.compile("(?:(?:%s)|(?:%s)|(?:%s))" % (_failure1, _failure2, _failure3), re.MULTILINE)
  _remote_hold = re.compile('(you|spirit)\.\.\.$')
  notarget = 'Spiritdisease whom'

  cost = 55
  cast = 'sd'
  cast_length = 3
  timeout = 60 # 25 - 30 rounds

  # for external use, just here logically
  player_affected = re.compile('^\s*Your spirit weakens under the assault')
  player_cleansed = re.compile('^\s*You feel a strengthening of your spirit\.\s*$')

  def __init__(self, *args, **opts):
    Spell.__init__(self, *args, **opts)
    #self.debug = 1
    return
  
  def finished(self, line):
    if (SpiritDisease._success.match(line)):
      return None
    elif (line.endswith('spirit!')):
      return None

    # dodging cowards
    if (line.endswith('..')):
      return None
    if (line.endswith('!')): # damn fighters
      self.failure = re.compile('.') # always matches failure
      return 0

    self.failure = SpiritDisease._failure
    return 0

class Soultap(Spell):
  success = "You raise your hand high and call upon Llardin's darkness"
  notarget = 'Soultap whom'
  
  cost = 85
  cast = 'st'
  cast_length = 2
  timeout = 4

class Flamestrike(Spell):
  success = '.'
  notarget = 'Flamestrike whom'
  
  cost = 60
  cast = 'fs'
  cast_length = 2
  timeout = 4
  
class Hammer(Spell):
  success = '.'
  notarget = 'Hammer whom'
  
  cost = 30
  cast = 'hammer'
  cast_length = 2
  timeout = 4
  
class Turn(Spell):
  success = '.'
  notarget = 'Turn whom'
  
  cost = 40
  cast = 'turn'
  cast_length = 1
  timeout = 4
  
class Gloriole(Spell):
  success = '.'
  notarget = 'Gloriole whom'
  
  cost = 60
  cast = 'gloriole'
  cast_length = 3
  timeout = 4

class Pacify(Spell):
  success = 'You try to calm'
  failure = 'You fail to calm'

  cost = 50
  cast = 'pac'
  cast_length = 1
  timeout = 2

class Stone(Spell):
  success = ''
  failure = ''
  notarget = '(?:(?:Stone whom)|(?:You have no stones to stone with))'
  

  cost = 15
  cast = 'stone'
  cast_length = 1

class Confess(Spell):
  success = 'Your deity summons you to the Hall of Souls'
  failure = "With so many sins you'll need to make an appointment"
  notarget = 'Mighty forces prevent you from contacting your God'

  _land = '^\s*You land in the Cathedral'

  cost = 30
  cast = 'confess'
  cast_length = 1

class ConfessWatcher(catcher.Catcher):
  """A very short class to let us know when we have landed"""
  start = re.compile(Confess._land)
  end = start
  result = 'Invalid from ConfessWatcher'
  def parse(self, lines):
    self.result = 'landed'
    return
  
class Revelation(Spell):
  _success_find = 'You are struck by a revelation!'
  _success_nofind = 'Unfortunately, you learn nothing of interest'
  success = '(?:(?:%s)|(?:%s))' % (_success_find, _success_nofind)
  failure = 'Llardin denies your request for divine inspiration'

  cost = 60
  cast = 'rev'
  cast_length = 1
  """
  Llardin denies your request for divine inspiration.

  Llardin smiles on your request.
  Unfortunately, you learn nothing of interest.
  
  Llardin smiles on your request.
  You are struck by a revelation!
  You find a trap door in the floor!
  """

class Shroud(Spell):
  """
  You recite a quick chant to Llardin and an aura of light surrounds you!
  The shroud dissipates from around you.
  You feel the return of Llardin's grace.
  """
  cast = 'shroud' # may be overwritten in __init__
  success = "You recite a quick chant to Llardin and an aura of \w+ surrounds you"
  failure = "You recite a quick chant to Llardin but nothing happens"
  notarget = "You are still too tired from the last time you made use of this gift"
  expire = "The shroud dissipates from around you"
  already = "You are already wearing a shroud"

  player_cleansed = re.compile('^\s*%s' % (expire))
  player_affected = re.compile('^\s*%s' % (success))
  
  def __init__(self, *args, **opts):
    if ('cost' in opts):
      self.cast = 'shroud %d' % (opts['cost'])
      del opts['cost']
    Spell.__init__(self, *args, **opts)
    return

  def post_parse(self, text):
    if (self.result == 'success'):
      self.howmuch = 1
    elif (self.result == 'expired'):
      self.howmuch = 0
      
        
    
