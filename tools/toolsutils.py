#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: toolsutils.py,v 1.1 2003/10/07 00:50:42 willhelm Exp $
#######################################################################
"""
This has a series of utility functions that aren't related to
classes in the application, but are useful in a variety of places.
"""
import string, re, time

ANSI_COLOR_REGEXP = re.compile(chr(27) + '\[[0-9;]*[mJ]')

def color(data, fc=37, bc=40, bold=0):
  if bold == 1:
    return "%c[1;%s;%sm%s%c[0m" % (chr(27), str(fc), str(bc), data, chr(27))
  else:
    return "%c[%s;%sm%s%c[0m" % (chr(27), str(fc), str(bc), data, chr(27))


def filter_ansi(text):
  """ Filters out ansi codes."""
  return re.sub(chr(27) + '\[[0-9;]*[mJ]', '', text)


def filter_cm(text):
  """ Filters out ^M.  Useful for logging."""
  return re.sub('\015|\r', '', text)


def chomp(text):
  """ Removes all '\\r' and '\\n' from the input string.

  arguments:

    'text' -- (string) the text to chomp

  returns:

    (string) chomped text

  """
  text = text.replace("\n", "")
  text = text.replace("\r", "")
  return text


def is_color_token(token):
  """ Returns whether or not this is a color token.

  arguments:

    'token' -- (string) the token to test

  returns:

    1 if it's a color token, 0 if not
  """
  if len(token) == 0:
    return 0

  return token[0:2] == chr(27) + "[" and token[-1] == "m"


def fix_color(color):
  """
  Helper function for debugging--it'll fix a color token
  so it's readable in ascii.

  arguments:

    'color' -- (string) the color token

  returns:

    string
  """
  color = color.replace(chr(27), "ESC")
  return color


def split_ansi_from_text(text):
  """ Takes in a string and returns a list of text and ansi tokens.

  arguments:

    'text' -- (string)

  returns:

    list of text and ansi tokens (all strings)
  """
  global ANSI_COLOR_REGEXP

  matchob = ANSI_COLOR_REGEXP.search(text)
  if matchob:
    textlist = []
    marker = 0
    while matchob:
      (b, e) = matchob.span()

      if marker == b:
        textlist.append(text[b:e])
      else:
        textlist.append(text[marker:b])
        textlist.append(text[b:e])

      marker = e
      matchob = ANSI_COLOR_REGEXP.search(text, marker)

    # we do this to handle ansi color sequences which are broken
    # between two network chunks
    b = text.rfind(chr(27))

    if b < marker:
      textlist.append(text[marker:])
    else:
      textlist.append(text[marker:b])
      textlist.append(text[b:])

    return textlist

  return [text]


def insert_cr(text, index, indent=0):
  """
  Inserts a carriage return into the line and deals with indenting
  the next line (if need be).

  arguments:

    'text' -- (string) the text in question

    'index' -- (int) the place to stick the cr

    'indent=0' -- (int) how much to indent the next line

  returns:

    (string) the text with the cr at the index and the next line
    indented so many spaces

  """
  return (text[:index] + '\n' + (indent * ' ') + text[index+1:].lstrip())


def wrap_text(textlist, wraplength=50, indent=0, firstline=0):
  """
  It takes a block of text and wraps it nicely.

  arguments:

    'textlist' -- (string) or (list of strings) either a string of 
                  text needing to be formatted and 
                  wrapped or a textlist--preferably the former.

    'wraplength' -- (int) how many characters to wrap at

    'indent=0' -- (int) how many spaces to indent each line

    'firstline=0' -- (int) 0 if we don't indent the first line, 1 if we do


  returns:

    (string) the wrapped text 
  """
  wrapcount = 0               # how much we've got on the line so far
  linecount = 0               # which line we're on

  if wraplength > 2:
    wraplength = wraplength - 2

  # split the formatting from the text
  if type(textlist) == type(''):
    textlist = split_ansi_from_text(textlist)

  for i in range(0, len(textlist)):

    # COLOR TOKEN
    if is_color_token(textlist[i]):
      pass

    # TEXT TOKEN
    else:
      marker = 0

      # while we keep finding carriage returns...
      x = textlist[i].find('\n')
      while x != -1:

        # if the carriage return is in a nice place we wrap there.
        if wrapcount + (x - marker) < wraplength:
          textlist[i] = insert_cr(textlist[i], x, indent)
          marker = x + 1
          wrapcount = 0

        # if the carriage return is not in a nice place.
        else:
          breakpoint = x
          # we look to the left for a space to wrap on.
          while wrapcount + (breakpoint - marker) > wraplength:
            breakpoint = textlist[i].rfind(' ', marker, breakpoint)
            if breakpoint <= marker:
              break

          # we either found a breakpoint or there are no spaces.
          # in the case of a breakpoint, we break.  otherwise
          # we just don't wrap that line....  i'm not a big fan
          # of wrapping inside a word thing.
          if breakpoint > marker:
            textlist[i] = insert_cr(textlist[i], breakpoint, indent)

          marker = breakpoint + 1
          wrapcount = 0

        x = textlist[i].find('\n', marker)

      # at this point there are no more carriage returns.  so we gots
      # to break at spaces.

      # if the remaining string exceeds the wraplength...       
      while len(textlist[i]) - marker + wrapcount >= wraplength:
        breakpoint = textlist[i].rfind(' ', 
                                       marker, 
                                       marker + wraplength - wrapcount)

        # we start looking from the end of the string leftwards
        # until we find a space

        # if there's a nice break point, we wrap there...
        if breakpoint > marker:
          textlist[i] = insert_cr(textlist[i], breakpoint, indent)
          wrapcount = 0
          marker = breakpoint
        else:
          break

      wrapcount += len(textlist[i]) - marker

  # this next line joins the list with no separator (GASP!)
  if firstline:
    return (indent * " ") + ''.join(textlist)
  else:
    return ''.join(textlist)


def columnize(textlist, screenwidth=72, indent=0):
  """
  Takes a list of data and converts it into a series of columns
  and rows that are evenly spaced and pretty and stuff.

  arguments:

    'textlist' -- (list of strings) the list to columnize

    'screenwidth=72' -- (int) the width to wrap against

    'indent=0' -- (int) the amount to indent each line

  returns:

    the final formatted string
  """
  if screenwidth > 2 + indent:
    screenwidth = screenwidth - 2 - indent

  SPACING = 4
  maxwidth = 0

  for mem in textlist:
    maxwidth = max(maxwidth, len(mem))

  numcols = max(1, (screenwidth + SPACING) / (maxwidth + SPACING))
  numrows = (len(textlist) + numcols - 1) / numcols

  rows = []
  ## We can't just do "rows = ([],) * rows" -- need distinct lists
  for i in range(numrows): 
    rows.append([])

  idx = 0
  for mem in textlist:
    mem = (mem + (' ' * (maxwidth + (SPACING - 1) - len(mem))))

    rows[idx].append(mem)
    idx = (idx + 1) % numrows

  rows = map(string.rstrip, map(string.join, rows))
  return (indent * " ") + string.join(rows, "\n" + (indent * " "))

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
