from mudpacks import mudbasic
from mudpacks.overdrive.odcatcher import *
from mudpacks.overdrive import spells
class ODPlayer(mudbasic.Player):
  """A boring object that just stores other stuff"""
  def __init__(self):
    self.stats = Stats(listen=1)
    self.skills = Skills(listen=1)
    self.armors = Armors(listen=1)
    self.spells = Spells(listen=1)
    self.who = Who(listen=1)
    self.spellq = spells.SpellQueue(100)
    self.active_spells = []
    self.drunk = None
    self.food = None
    # make a list for the loader to attach to the catch q
    self.catcher_add_these = [self.stats, self.skills, self.spells, self.armors, self.who]
    return

  def status_line(self):
    line1 = 'HP: %3d/%3d  MP:%3d/%3d Exp %d %d  %s/%s' % (self.vitals.stats['hp'],
                                                          self.vitals.stats['max_hp'],
                                                          self.vitals.stats['mp'],
                                                          self.vitals.stats['max_mp'],
                                                          self.vitals.stats['exp'],
                                                          self.vitals.stats['to_level'],
                                                          str(self.drunk),
                                                          str(self.food),
                                                         )
    line2 = str(self.xpqueue)
    return "%s\n%s\n" % (line1, line2)


