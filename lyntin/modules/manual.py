#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: manual.py,v 1.1 2003/05/05 05:56:02 willhelm Exp $
#######################################################################
"""
This module holds the README manual text.
"""
from lyntin import exported

bugs = """
Lyntin was originally written by Lyn Headley.  Lyntin is 
currently being maintained by Will Guaraldi, 
willhelm@users.sourceforge.net as of 1.3.2.

We appreciate ALL types of feedback.

Inevitably you will either run across a bug in Lyntin or the need 
for a feature to be implemented.  When this happens, we ask you 
to provide as much information as you can:

  - operating system, version of Python and version of Lyntin
    (from #diagnostics)
  - stacktrace (if it's a bug and kicked up a stacktrace)
  - explanation of what happened vs. what should be happening
  - any other pertinent information

Enter this in the bugs forum or send it to the mailing list.  
Details for both are on the Lyntin web-site:

   http://lyntin.sourceforge.net/

category: readme
"""

command = """
Lyntin uses Lyntin commands to allow you to manipulate the Lyntin 
client and setup your session with aliases, variables, actions, 
and such.  Commands start with the command character--by default 
this is "#".  It can be changed with the "#config" command.  The 
command character can also do some other special things:

1. You can execute commands in another session by typing the 
   command character and then the sesion name: "#3k say hello" 
   will say hello in the 3k session.

2. You can switch to another session by typing the command 
   character and then the session name: "#3k" will switch to the 
   3k session.

3. You can execute a command in all sessions by typing the 
   command character then all: "#all say hello" will say hello in 
   all sessions.

4. You can execute a command a number of times by typing the 
   command character then a number, then the command: 
   "#5 say hello" will send "say hello" to the current session 
   5 times.

Commands are separated by the semicolon.  Semicolons can be 
escaped with the \ character.

Command arguments can be enclosed with { }.  This enables you to 
specify arguments that have multiple words in them.

{, } and \ can all be escaped with the \ character: \{, \}, and \\.

category: readme
"""

contribute = """
Development and maintenance is entirely managed by the maintainer 
right now.  If you're interested in sending in bug fixes, please 
feel welcome.  I'm extremely accomodating to most methods of 
sending in patches, however a diff -u output file is great for 
this sort of thing.

All patches and such things should be sent to the mailing list at:

   lyntin-devl@lists.sourceforge.net

Note: Patches will not be applied unless the author either yields 
the copyright to the FSF or to us (and then we'll yield it to the 
FSF).

Please read through the web-site areas on coding conventions and 
such before sending in code.

category: readme
"""

errata = """
The latest release of Lyntin is always available from:

   http://lyntin.sourceforge.net/

under Download.  We also have snapshots of what's in CVS under
Development.

There are very few developers working on Lyntin, but we turn
around bugs in very short periods of time.  Issues are tracked
via the Sourceforge bug-tracker or through email.  If you have
problems, feel free to submit a bug report--please include as
much information as you can so we can reproduce and then fix
the bug.  If you want to fix it yourself, please do!  Feel free
to send in patches.

In-game help is accessed by typing ``#help``.  When you start 
Lyntin for the first time, type ``#help general`` and that'll 
get you started.  Read through the various help files at your 
leisure.

category: readme
"""

evaluation = """
Variables get evaluated according to a new methodology we developed
after disliking the Tintin way of doing things.  This new methodology
provides maximum flexibility and provides for some things that
the Tintin variable evaluation did not provide for.

  * Variables and placement variables with a single $ or % are
    evaluated/expanded.  One layer of $s or %s is then stripped 
    off when this evaluation occurs.

  * Variable expansion is always done on user input before 
    commands are evaluted.  This means variables can be used as 
    arguments to any commands, etc.

  * Variable expansion happens again when certain expressions are
    evaluated, such as action triggers, alias expansion, etc.
    Essentially, when any stored value gets expanded its variables
    will get expanded (typically whenever tintinmode would do its 
    sole expansion.) 

  * Placement vars in actions and aliases support an expanded 
    syntax based on python array slices.  %0:1 will evaluate to 
    the first and second arguments, while %0: will be all 
    arguments, and %:-1 will be all but the last argumen, etc.

Examples:

1. #action {$Myvar} {woo} 

Will trigger whenever the value Myvar holds when this is entered 
(the original value of Myvar - it will not change if Myvar's 
value changes)

2. #action {$$Myvar} {woo}

Will trigger whenever the current value of Myvar passes by.

3. #action {$$$Myvar} {woo}

Will trigger whenever the literal string $Myvar is seen.  Place 
more $s in if you wish to trigger on more of them, the first 2 
will be stripped by the variable expansion processes. 

4. #alias {hello} {$moo}

Will bind hello to $moo's current value.

5. #alias {hello} {$$moo}

Will bind hello to always expand to moo's current value at the
time of expansion.

6. #alias {hello} {$$$moo}

Will bind hello to expand to the literal string "$moo"

category: readme
"""

examples = """
Examples of commands in Lyntin::

   say hello
   get all;put all in chest
   #3k {get all;put all in chest}
   #alias gg {get all;put all in chest}
   #alias gg {get all;put all in chest} quiet={true}
   #alias k {kill %1;follow %1;#action {pummels you} {%2}}
   #3k {say you people are irritating;#zap}
   #5 {get all from chest;donate all}
   say you rock!  \;)

category: readme
"""

general = """
"lyntin.py --help" lists command line arguments and what they do.

Type "#help help" for help on how to use the in-game help system.

Read through the "#help readme" topics.  These will help as they 
will walk you through how Lyntin works, how to get additional 
help, where to go for answers, and what to do if you find a bug.  
These are also exported into the README file.

You should read through the topics in "#help commands" for all 
the currently registered Lyntin commands.

Each user interface has its own help topic--these will be on the 
top level of the help structure.

To start, the "#session" command will allow you to start a 
session.  When you're done, "#end" will close Lyntin.

All documentation that comes with Lyntin is also available on the
Lyntin web-site.  If you find problems with the documentation or
have fixes for it, let us know on the lyntin-devl mailing list.

category: readme
"""

gettingstarted = """
Lyntin incorporates the _look and feel_ of Tintin, so if you've used
Tintin or a variant it should be pretty easy to make the transition.  
It offers all the major features of Tintin, including multiple 
sessions, but leaves a few minor things out.

There are *in-game* help files covering the commands and most 
other things we could think of which can be accessed with the "#help"
command.

All the documentation comes with Lyntin and is also available on
the Lyntin website in HTML form.  If you find problems with the 
documentation or have fixes for it, let us know.

Lyntin has a series of command line flags which change its behavior.

category: readme
"""

osnotes = """
Lyntin works in most environments we can think of, but it has some
caveats with the various operating systems due to differences 
between them.

WINDOWS
-------

Windows users should use either \\ or / to denote directory 
separaters.

ex::

   #write c:\\commandfile
   #write c:/commandfile


REDHAT LINUX
------------

Depending on which version of RedHat Linux you have, you will have 
to install the Python RPM as well as the Python Tkinter RPM.  If 
you don't install the Tkinter RPM, then you won't be able to use 
the Tk ui and it'll complain that it's missing a library when you 
try.


MAC OSX
-------

I have no experience with Mac OSX but after reading the various 
pages on Python and how it works on OSX, I'm hesitant to say 
Lyntin is fully supported.  However, I don't know of any reason 
it shouldn't be supported either except that one person on the 
mailing list has had problems with getting #write to work.


OTHER NOTES
-----------

If you encounter other operating system issues, let us know both 
the problem and the solution so we can add them here.

category: readme
"""

regexp = """
Lyntin allows the use of regular expressions in various arguments
for commands like #action, #highlight, and such.  It uses a 
specific format to trigger using raw regular expressions rather 
than having your argument get escaped so it can be compiled into 
a regular expression.  This allows you to write arguments using 
the simplest form that you can without having to adjust toggles 
and such.

For example:

  #highlight {red} {*says:}

is the same as:

  #highlight {red} {r[^.*?says:]}

The first one will undergo escaping and get transformed into 
"^.*?says\:" (without the quotes) before being compiled into a
regular expression.

The second one gets compiled without being escaped.

For regular expression documentation, refer to the Python 
documentation at:

  http://www.python.org/doc/current/lib/re-syntax.html

Note: It may have moved since this was written.

category: readme
"""

whylyntin = """
Lyntin is written entirely in Python--a nicely written and very 
portable programming language.  Thusly Lyntin is platform 
independent.  Lyntin is exposes the Python interpreter allow you 
more freedom than mere 'if you see this then send this' aliases 
and triggers.  They can be Python functions which do anything 
from setting a variable to forking a web spider.  In addition, 
your code can interface with Lyntin's code.  

Lyntin is great if:

1. you want a mud client that you can see the source code to
   and adjust it to suit your needs
2. you want a mud client that has a sophisticated API for 
   enhancing and building bots/agents/triggers more advanced than
   "if you see this then do this"
3. you want a mud client that works on all your machines,
   has a text ui, a tk gui, and can also work over ssh/telnet

Lyntin is not great if:

1. you prefer wizards and menus to the command line
2. you hate Python
3. you want fancy bells and whistles in the ui

category: readme
"""

def load():
  exported.add_help("bugs", bugs)
  exported.add_help("command", command)
  exported.add_help("contribute", contribute)
  exported.add_help("errata", errata)
  exported.add_help("evaluation", evaluation)
  exported.add_help("examples", examples)
  exported.add_help("general", general)
  exported.add_help("gettingstarted", gettingstarted)
  exported.add_help("osnotes", osnotes)
  exported.add_help("regexp", regexp)
  exported.add_help("whylyntin", whylyntin)
