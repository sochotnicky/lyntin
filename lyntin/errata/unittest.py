#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: unittest.py,v 1.1 2003/05/05 05:55:33 willhelm Exp $
#######################################################################
"""
This module has its own main method.  It's used to unit test functions in
Lyntin.  Don't mind it--it just hangs out here.
"""
failures = 0

import sys

def _pass_fail(desc, testoutput, realoutput):
  """ Used for testing purposes."""
  global failures

  if testoutput == realoutput:
    # print "   pass:", testoutput
    print "   pass:", desc
  else:
    print "   fail:", desc
    print "'" + str(testoutput) + "'"
    print "'" + str(realoutput) + "'"
    failures += 1


if __name__ == '__main__':
  import sys

  sys.path.insert(0, "../")

  from utils import split_commands
  _pass_fail("split_commands 1", split_commands('test'), 
            ['test'])
  _pass_fail("split_commands 2", split_commands('test;test2'), 
            ['test', 'test2'])
  _pass_fail("split_commands 3", 
            split_commands('#alias t3k #ses a localhost 3000'),
            ['#alias t3k #ses a localhost 3000'])
  _pass_fail("split commands 4", 
            split_commands('#alias gv {put all in vortex;get all}'),
            ['#alias gv {put all in vortex;get all}'])
  _pass_fail("split_commands 5", 
            split_commands('#alias sv {put all in vortex;get all};test'),
            ['#alias sv {put all in vortex;get all}', 'test'])
  _pass_fail("split commands 6",
            split_commands(r'#showme \{ blah;#showme another }'), 
            [r'#showme \{ blah', r'#showme another }'])

  print 

  from ansi import split_ansi_from_text
  _pass_fail("split_ansi_from_text 1",
            split_ansi_from_text("This is some text."),
            ["This is some text."])
  _pass_fail("split_ansi_from_text 2",
            split_ansi_from_text("\33[1;37mThis is\33[0m text."),
            ["\33[1;37m", "This is", "\33[0m", " text."])
  _pass_fail("split_ansi_from_text 3",
            split_ansi_from_text("Hi \33[1;37mThis is\33[0m text."),
            ["Hi ", "\33[1;37m", "This is", "\33[0m", " text."])
  _pass_fail("split_ansi_from_text 4",
            split_ansi_from_text("\33[1;37mThis is\33[0"),
            ["\33[1;37m", "This is", "\33[0"])

  print

  text = "This is a really long line to see if we're wrapping correctly.  Because it's way cool when we write code that works.  Yay!"

  from utils import wrap_text
  _pass_fail("wrap text 1",
            wrap_text(text),
"""This is a really long line to see if we're 
wrapping correctly.  Because it's way cool when 
we write code that works.  Yay!""")

  _pass_fail("wrap text 2",
            wrap_text(text, indent=5),
"""This is a really long line to see if we're 
     wrapping correctly.  Because it's way cool 
     when we write code that works.  Yay!""")
  _pass_fail("wrap text 3",
            wrap_text(text, indent=5, firstline=1),
"""     This is a really long line to see if we're 
     wrapping correctly.  Because it's way cool 
     when we write code that works.  Yay!""")


  text = "Hi.  Check this out: Thistexthasnospacesinitandmightcausethingstocrashorgointoaninfiniteloopandstuff.whichwouldbesuperbad.  What do you think?"
  _pass_fail("wrap_text 4 (big big string)", wrap_text(text),
"""Hi.  Check this out: 
Thistexthasnospacesinitandmightcausethingstocrash
orgointoaninfiniteloopandstuff.whichwouldbesuperb
ad.  What do you think?""")
  _pass_fail("wrap_text 5 (big big string with indent)", 
            wrap_text(text, indent=5),
"""Hi.  Check this out: 
     Thistexthasnospacesinitandmightcausethingsto
     crashorgointoaninfiniteloopandstuff.whichwou
     ldbesuperbad.  What do you think?""")
  _pass_fail("wrap_text 6 (long url like string with indent)",
            wrap_text("[You said to notadragon17]: http://abcnews.go.com/sections/us/DailyNews/terrifica021105.html", 70, 5, 0),
"""[You said to notadragon17]: 
     http://abcnews.go.com/sections/us/DailyNews/terrifica021105.html
     """)
  _pass_fail("wrap_text 7 (long series of digits with indent)",
            wrap_text("[notadragon17 said]: 123456789012345678901234567890124567890123456789012345678901234567890123456789012345678901234567890", 70, 5, 0),
"""[notadragon17 said]: 
     1234567890123456789012345678901245678901234567890123456789012345
     67890123456789012345678901234567890""")



  text = "This is some text \33[1;37mwith some\33[0m ansi formatting in it to see if we can handle wrapping with it \33[1;37mtoo.\33[0m"
  _pass_fail("wrap_text 8 (with ansi)", wrap_text(text),
"""This is some text \33[1;37mwith some\33[0m ansi formatting in 
it to see if we can handle wrapping with it \33[1;37mtoo.\33[0m""")

  _pass_fail("wrap_text 9 (with ansi)", wrap_text(text, indent=5),
"""This is some text \33[1;37mwith some\33[0m ansi formatting in 
     it to see if we can handle wrapping with 
     it \33[1;37mtoo.\33[0m""")

  print

  from utils import parse_timespan
  _pass_fail("parse_timespan 1", parse_timespan("1h"), 3600)
  _pass_fail("parse_timespan 2", parse_timespan("1m"), 60)
  _pass_fail("parse_timespan 3", parse_timespan("1s"), 1)
  _pass_fail("parse_timespan 4", parse_timespan("1h2m3s"), 3723)
  _pass_fail("parse_timespan 5", parse_timespan("17"), 17)
  _pass_fail("parse_timespan 6", parse_timespan("5h"), 3600 * 5)

  print

  # FIXME - these always fail because we don't get the precision right.
  # not sure what to do about that.
  from utils import parse_time
  _pass_fail("parse_time 1", int(parse_time("4:20p")), 1029878400)
  _pass_fail("parse_time 2", int(parse_time("4m")), 1029796956)
  _pass_fail("parse_time 3", int(parse_time("9")), 1029796725)
  _pass_fail("parse_time 4", int(parse_time("1:17:34a")), 1029824254)

  print

  from utils import expand_placement_vars
  # these are lyntin mode tests
  _pass_fail("expand_placement_vars 1", 
            expand_placement_vars("#test 1 2 3", "#test"),
            "#test 1 2 3")
  _pass_fail("expand_placement_vars 2",
            expand_placement_vars("#test 1 2 3", "#test %1 %2"),
            "#test 1 2")
  _pass_fail("expand_placement_vars 3",
            expand_placement_vars("#test 1 2 3", "#test %0"),
            "#test #test")
  _pass_fail("expand_placement_vars 4",
            expand_placement_vars("#test 1 2 3", "#test %-1"),
            "#test 3")
  _pass_fail("expand_placement_vars 5",
            expand_placement_vars("#test 1 2 3", "#test %:-1"),
            "#test #test 1 2")
  _pass_fail("expand_placement_vars 6",
            expand_placement_vars("#test 1 2 3", "#test %1:-1"),
            "#test 1 2")

  print

  from utils import expand_vars
  # these are lyntin mode tests
  varmap = {"var1": "value1", "var2": "value2", "var3": "value3"}
  _pass_fail("expand_vars 1", 
            expand_vars(r"This has no vars.", varmap), "This has no vars.")
  _pass_fail("expand_vars 2", 
            expand_vars(r"$var1 $var2 $var3", varmap), "value1 value2 value3")
  _pass_fail("expand_vars 3", 
            expand_vars(r"$var1 $$var2 \$var3", varmap), r"value1 $$var2 \$var3")

  print "There were %d failures." % failures

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
