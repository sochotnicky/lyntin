"""
This module has two classes to make it easier to parse ANSI code.

the ANSIStream class is used to give/get (color, text) pairs from a text
stream.  Just keep ansi_stream_ob.parse('yet more text') and it will yield
(color, for_this_text) pairs.

By default color is an ANSIColor object which prints out the same ansi
color sequence as the original if you so str(ansi_color_ob)

NoColor is an ANSIColor derivative that always returns '' as it's string.

Define a new class that looks at the bold/underline/whatever attributes
of ANSIColor in it's __str__ method and returns whatever is appropriate
for your app.  See the _tkui/scrollers.py for an example (TkColor)
"""
import re
ANSI_ESCAPE = chr(27)

# used for converting text descriptions to ANSI color sequences
STYLEMAP = {
             "default": "0",
             "bold": "1",
             "bold_off": "22",
             "underline": "4",
             "underline_off": "24",
             "blink": "5",
             "blink_off": "25",
             "reverse": "7",
             "reverse_off": "27",
             "black": "30",
             "red": "31",
             "green": "32",
             "yellow": "33",
             "blue": "34",
             "magenta": "35",
             "cyan": "36",
             "white": "37",
             "grey": "1;30",
             "light red": "1;31",
             "light green": "1;32",
             "light yellow": "1;33",
             "light blue": "1;34",
             "light magenta": "1;35",
             "light cyan": "1;36",
             "light white": "1;37",
             "b black": "40",
             "b red": "41", 
             "b green": "42",
             "b yellow": "43",
             "b blue": "44",
             "b magenta": "45",
             "b cyan": "46",
             "b white": "47"
           }

class ANSIColor(object):
  def __init__(self, **opts):
    d = {'fg':0,'bg':0,'underline':0,'bold':0,'reverse':0,'blink':0}
    d.update(opts) # defaults to values above if nothing in opts

    # translate fg/bg colors if they passed in a word
    self.fg = STYLEMAP.get(d['fg'], d['fg'])
    self.bg = STYLEMAP.get(d['bg'], d['bg'])
    # be lenient, if they used a fg color name for the bg just translate it
    if (int(self.bg) < 40):
      self.bg = str(int(self.bg) + 10)
    # the rest are just booleans
    self.underline = d['underline']
    self.bold = d['bold']
    self.reverse = d['reverse']
    self.blink = d['blink']
    return

  def copy(self):
    cp = self.__class__()
    for (att) in ['fg','bg','underline','bold','reverse','blink']:
      setattr(cp, att, getattr(self, att))
    return cp

  def __str__(self):
    parts = []
    if (self.bold):
      parts.append(STYLEMAP['bold'])
    if (self.underline):
      parts.append(SYTLEMAP['underline'])
    if (self.blink):
      parts.append(STYLEMAP['blink'])
    if (self.reverse):
      parts.append(SYTLEMAP['reverse'])
    if (self.fg):
      parts.append(self.fg)
    if (self.bg):
      parts.append(self.bg)
    if (not parts):
      parts = ['0']
    return '%s%s]m' % (ANSI_ESCAPE, ';'.join(map(str, parts)))

  def __repr__(self):
    return repr(str(self))

class NoColor(ANSIColor):
  """This class is a little silly, if you dont' want any color
  then just ignore the color part of the (color, text) tuple
  yielded by ANSIStream
  """
  def __str__(self):
    return ''
    
class ANSIStream(object):
  """ANSIStrem keeps state about what you current colors are.
  When you call parse() on an instance it will return a list of
  (color, str) tuples that represent all the text it could parse.
  """
  _ansi_re = re.compile('%s\[([0-9;]*)m' % (ANSI_ESCAPE))
  _unfin1 = '(?:%s)' % (ANSI_ESCAPE)
  _unfin2 = '(?:%s\[)' % (ANSI_ESCAPE)
  _unfin3 = '(?:%s\[[0-9;]+)' % (ANSI_ESCAPE)
  _unfinished_re = re.compile('(%s)$' % ('|'.join([_unfin1, _unfin2, _unfin3])))
  def __init__(self, default_color = ANSIColor(), color_class = ANSIColor):
    self.default_color = default_color
    self.curr_color = default_color
    self.unfinished_text = ''
    self.new_color = color_class
    return

  def parse(self, text):
    """Add <text> to the ANSIStream,
    yields (color, str) tuples of all text that could be parsed.
    If <text> ends in what looks like the beginning of an ANSI code we hang on
    to that for the next time parse() is called.
    """
    for (raw_color, sometext) in self.tokenize(text):
      if (raw_color == '0'): # reset to default
        yield (self.default_color, sometext)
        self.curr_color = self.default_color.copy()
        continue
      elif (raw_color is None): # use current
        yield (self.curr_color, sometext)
        continue

      # else, we have a color change operation
      # copy the default color and change the bits specified in the string
      self.curr_color = self.default_color.copy()
      color = self.curr_color
      apply_to_default_fg = 0
      apply_to_default_bg = 0
      parts = map(int, filter(None, raw_color.split(';'))) # strip empties, then int() all the parts
      for (code) in parts:
        if code == 1:
          color.bold = 1
        elif code == 4:
          color.underline = 1
        elif code == 5:
          color.blink = 1
        elif code == 7:
          color.reverse = 1
        elif code == 22:
          color.bold = 0
        elif code == 24:
          color.underline = 0
        elif code == 25:
          color.blink = 0
        elif code == 27:
          color.reverse = 0
        elif code == 39: # next fg color sets default fg
          apply_to_default_fg = 1
        elif code == 49: # next bg color sets default bg
          apply_to_default_bg = 1
        elif 30 <= code and code<= 37: # these are foreground attributes
          if (apply_to_default_fg):
            self.default_color.fg = code
            print "Setting FG default to ", code
          else:
            color.fg = code
        elif 40 <= code and code<= 47: # these are background attributes
          if (apply_to_default_bg):
            self.default_color.bg = code
            print "Setting BG default to ", code
          else:
            color.bg = code

      yield (color, sometext)
    # end for
    return
  
  def tokenize(self, text):
    """yield (color, str) pairs as we tokenize the text"""
    if (self.unfinished_text): # we had a partial last time
      text = self.unfinished_text + text
      self.unfinished_text = ''
      
    last = 0
    lastcolor = None
    for (m) in self._ansi_re.finditer(text):
      if (m.start() > last): # skipped over some text
        yield (lastcolor, text[last:m.start()])        
      lastcolor = m.group(1) or '0' # ESC[m means ESC[0m
      last = m.end()
    
    # check for unfished ANSI at the end
    if (self._unfinished_re.search(text, last)):
      m = self._unfinished_re.search(text, last)
      self.unfinished_text = m.group(1)
      end = m.start()
    else:
      end = len(text)
    if (last < end): # there was some text between the previous ansi and this unterminate ansi
      yield (lastcolor, text[last:end])
    return

""" Author's note.
    ANSIStream could very easilly cache colors if it proves to be slow (I would be surprised if it was slow)
    in ANSIStream.__init__
    self._color_cache = {}
    then before we split and parse the pieces of a raw_color string, do
    try:
      cached_color_object = self._color_cache[raw_str] # done early!
      yield (cached_color_object, sometext)
    except: pass # oh well, do the normal parsing
"""


if (__name__ == '__main__'):
  dc = ANSIColor()
  p = ANSIStream(dc)
  print list(p.parse('asdf')), repr(p.unfinished_text)
  print list(p.parse('asdf%s[37;mboboo' % (chr(27)))), repr(p.unfinished_text)
  print list(p.parse('foo%s[0;mbar' % (chr(27)))), repr(p.unfinished_text)
  print list(p.parse('asdf%s[30' % (chr(27)))), repr(p.unfinished_text)
  print list(p.parse('mvoodoo')),repr(p.unfinished_text)

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
