#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: lyntinunittest.py,v 1.2 2003/11/09 23:25:09 willhelm Exp $
#######################################################################
"""
This module uses the Python unittest framework to unittest various
pieces inside of Lyntin--mostly stuff that's standalone in the 
lyntin.utils module.
"""
# we kind of assume this is being run in ./lyntin40/tools/
import sys, unittest
sys.path.insert(0, "../")

import lyntin.utils
import lyntin.ansi

class TestSplitCommands(unittest.TestCase):
  t = (
     ("test", ["test"]),
     ("test;test2", ['test', 'test2']),
     ("#alias t3k #ses a localhost 3000", ["#alias t3k #ses a localhost 3000"]),
     ("#alias gv {put vx;get all}", ["#alias gv {put vx;get all}"]),
     ("#alias sv {put vx;get all};test", ["#alias sv {put vx;get all}", "test"]),
     (r"#sh \{ blah;#sh another }", [r"#sh \{ blah", r"#sh another }"])
  )

  def testSplit(self):
    """Tests lyntin.utils.split_commands"""
    for i in range(0, len(self.t)):
      c, s = self.t[i]
      result = lyntin.utils.split_commands(c)
      self.assertEquals(s, result, "test %d" % i)

class TestSplitAnsiFromText(unittest.TestCase):
  t = (
     ( "This is some text.", ["This is some text."]),
     ( "\33[1;37mThis is\33[0m text.", ["\33[1;37m", "This is", "\33[0m", " text."]),
     ( "Hi \33[1;37mThis is\33[0m text.", ["Hi ", "\33[1;37m", "This is", "\33[0m", " text."]),
     ("\33[1;37mThis is\33[0", ["\33[1;37m", "This is", "\33[0"])
  )

  def testAnsiSplit(self):
    """Tests lyntin.ansi.split_ansi_from_text"""
    for i in range(0, len(self.t)):
      c, s = self.t[i]
      result = lyntin.ansi.split_ansi_from_text(c)
      self.assertEquals(s, result, "test %d" % i)


class TestWrapText(unittest.TestCase):
  text = "This is a really long line to see if we're wrapping correctly.  Because it's way cool when we write code that works.  Yay!"
  text2 = "Hi.  Check this out: Thistexthasnospacesinitandmightcausethingstocrashorgointoaninfiniteloopandstuff.whichwouldbesuperbad.  What do you think?"
  text3 = "[You said to notadragon17]: http://abcnews.go.com/sections/us/DailyNews/terrifica021105.html"
  text4 = "[notadragon17 said]: 123456789012345678901234567890124567890123456789012345678901234567890123456789012345678901234567890"
  text5 = "This is some text \33[1;37mwith some\33[0m ansi formatting in it to see if we can handle wrapping with it \33[1;37mtoo.\33[0m"

  def testWrapText(self):
    """Tests lyntin.ansi.wrap_text with a non-exciting string"""
    self.assertEquals(lyntin.utils.wrap_text(self.text), \
"""This is a really long line to see if we're 
wrapping correctly.  Because it's way cool when 
we write code that works.  Yay!""", "test 1")

    self.assertEquals(lyntin.utils.wrap_text(self.text, indent=5), \
"""This is a really long line to see if we're 
     wrapping correctly.  Because it's way cool 
     when we write code that works.  Yay!""", "test 2")

    self.assertEquals(lyntin.utils.wrap_text(self.text, indent=5, firstline=1), \
"""     This is a really long line to see if we're 
     wrapping correctly.  Because it's way cool 
     when we write code that works.  Yay!""", "test 3")


  def testWrapText2(self):
    """Tests lyntin.ansi.wrap_text with a long word in it"""
    self.assertEquals(lyntin.utils.wrap_text(self.text2), \
"""Hi.  Check this out: 
Thistexthasnospacesinitandmightcausethingstocrash
orgointoaninfiniteloopandstuff.whichwouldbesuperb
ad.  What do you think?""", "test 1")

    self.assertEquals(lyntin.utils.wrap_text(self.text2, indent=5), \
"""Hi.  Check this out: 
     Thistexthasnospacesinitandmightcausethingsto
     crashorgointoaninfiniteloopandstuff.whichwou
     ldbesuperbad.  What do you think?""", "test 2")

  def testWrapText3(self):
    """Tests lyntin.ansi.wrap_text with a long url in it"""
    self.assertEquals(lyntin.utils.wrap_text(self.text3, 70, 5, 0), \
"""[You said to notadragon17]: 
     http://abcnews.go.com/sections/us/DailyNews/terrifica021105.html
     """, "test 1")

  def testWrapText4(self):
    """Tests lyntin.ansi.wrap_text with a long sequence of digits in it"""
    self.assertEquals(lyntin.utils.wrap_text(self.text4, 70, 5, 0), \
"""[notadragon17 said]: 
     1234567890123456789012345678901245678901234567890123456789012345
     67890123456789012345678901234567890""", "test 1")

  def testWrapText5(self):
    """Tests lyntin.ansi.wrap_text with a ansi markup in it"""
    self.assertEquals(lyntin.utils.wrap_text(self.text5), \
"""This is some text \33[1;37mwith some\33[0m ansi formatting in 
it to see if we can handle wrapping with it \33[1;37mtoo.\33[0m""", "test 1")

    self.assertEquals(lyntin.utils.wrap_text(self.text5, indent=5), \
"""This is some text \33[1;37mwith some\33[0m ansi formatting in 
     it to see if we can handle wrapping with 
     it \33[1;37mtoo.\33[0m""", "test 2")

class TestParseTimespan(unittest.TestCase):
  t = (
    ("1h", 3600),
    ("1m", 60),
    ("1s", 1),
    ("1h2m3s", 3723),
    ("17", 17),
    ("5h", 3600 * 5)
  )

  def testParseTimespam(self):
    """Tests lyntin.utils.parse_timespam"""
    for i in range(0, len(self.t)):
      c, s = self.t[i]
      self.assertEquals(lyntin.utils.parse_timespan(c), s, "test %d" % i)

class TestExpandPlacementVars(unittest.TestCase):
  c = "#test 1 2 3"
  t = (
    ("#test", "#test 1 2 3"),
    ("#test %1 %2", "#test 1 2"),
    ("#test %0", "#test #test"),
    ("#test %-1", "#test 3"),
    ("#test %:-1", "#test #test 1 2"),
    ("#test %1:-1", "#test 1 2")
  )

  def testExpandPlacementVars(self):
    """tests lyntin.utils.expand_placement_vars"""
    from lyntin.utils import expand_placement_vars
    for i in range(0, len(self.t)):
      c, s = self.t[i]
      self.assertEquals(expand_placement_vars(self.c, c), s, "test %d" % i)

class TestExpandVars(unittest.TestCase):
  varmap = {"var1": "value1", "var2": "value2", "var3": "value3"}
  t = (
    (r"$", "$"),
    (r" $", " $"),
    (r"$ ", "$ "),
    (r"This has no vars.", "This has no vars."),
    (r"$var1 $var2 $var3", "value1 value2 value3"),
    (r"$var1 $$var2 \$var3", r"value1 $$var2 \$var3"),
    (r"${var1} $${var2} \${var3}", r"value1 $${var2} \${var3}")
  )

  def testExpandVars(self):
    """tests lyntin.utils.expand_vars"""
    from lyntin.utils import expand_vars
    for i in range(0, len(self.t)):
      c, s = self.t[i]
      self.assertEquals(expand_vars(c, self.varmap), s, "test %d" % i)

"""
# FIXME - these always fail because we don't get the precision right.
# not sure what to do about that.
from lyntin.utils import parse_time
_pass_fail("parse_time 1", int(parse_time("4:20p")), 1029878400)
_pass_fail("parse_time 2", int(parse_time("4m")), 1029796956)
_pass_fail("parse_time 3", int(parse_time("9")), 1029796725)
_pass_fail("parse_time 4", int(parse_time("1:17:34a")), 1029824254)
"""


if __name__ == '__main__':
  from lyntin import constants
  print constants.VERSION

  unittest.main(testRunner=unittest.TextTestRunner(verbosity=2))

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
