#########################################################################
# This file is part of Lyntin.
# 
# Lyntin is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
# 
# Lyntin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# 
# copyright (c) Free Software Foundation 2001-2007
# 
# $Id: ansi.py,v 1.2 2007/07/24 00:39:03 willhelm Exp $
#########################################################################
"""
This holds a series of classes and functions for helping to manipulate
ANSI color codes.

In general, Lyntin keeps the data from the mud intact without doing any
transformations on it letting the ui do the transformations it needs to
do to display the mud data.  The exception to this is when the user has
shut off mudansi using the #config command.  Then we'll whack any incoming
ANSI color stuff before moving it around.
"""
import re

# for finding ANSI color sequences
ANSI_COLOR_REGEXP = re.compile(chr(27) + '\[[0-9;]*[m]')

STYLE_NORMAL = 0
STYLE_BOLD = 1
STYLE_UNDERLINE = 4
STYLE_BLINK = 5
STYLE_REVERSE = 7

# enums for placement in the color list
PLACE_BOLD = 0
PLACE_UNDERLINE = 1
PLACE_BLINK = 2
PLACE_REVERSE = 3
PLACE_FG = 4
PLACE_BG = 5

# the default color
DEFAULT_COLOR = [0, 0, 0, 0, -1, -1]

# used for converting text descriptions to ANSI color sequences
STYLEMAP = {
             "default": "0",
             "bold": "1",
             "underline": "4",
             "blink": "5",
             "reverse": "7",
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


def filter_ansi(text):
  """
  Takes in text and filters out the ANSI color codes.

  @returns: text without ANSI color codes
  @rtype: string
  """
  return ANSI_COLOR_REGEXP.sub('', text)


def is_color_token(token):
  """
  Returns whether or not this is a color token.  It figures this out
  by checking to see if the token matches this regexp: 
  chr(27) + '\[[0-9;]*[m]'

  @param token: the token in question
  @type  token: string

  @return: 1 if it's color, 0 if not
  @rtype: boolean
  """
  if len(token) == 0:
    return 0

  return ANSI_COLOR_REGEXP.match(token)


def fix_color(color):
  """
  Helper function for debugging--it'll fix a color token so it's 
  readable in ascii.  It just replaces instances of chr(27) with 
  "ESC".

  @param color: the color token
  @type  color: string

  @return: the pretty string
  @rtype: string
  """
  return color.replace(chr(27), "ESC")


def split_ansi_from_text(text):
  """
  Takes in a string and separates it into a list of strings and ansi
  color strings.

  @param text: the full string to split up
  @type  text: string

  @return: list of text and ansi color tokens
  @rtype: list of strings
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
    if marker < len(text):
      escindex = text.rfind('\33', marker)
      if escindex != -1:
        for i in range(escindex+1, len(text)):
          c = text[i]

          if c.isdigit() or c == ";" or c == "[":
            continue
          else:
            escindex = -1
            break

      if escindex == -1:
        textlist.append(text[marker:])
      else:
        textlist.append(text[marker:escindex])
        textlist.append(text[escindex:])

    return textlist
  return [text]


def figure_color(textlist, currentcolor, leftover=""):
  """ 
  Takes a textlist of text and color tokens and figures out
  the latest current color.

  @param textlist: the list of string and ansi color code tokens
  @type  textlist: list of strings

  @param currentcolor: a tuple of (options, foreground, background) 
      that represent the current color
  @type  currentcolor: (int, int, int)

  @param leftover: if we encounter a half done color code, we throw
      it in the leftover string.  the leftover gets prepended
      to the textlist element on the next run of figure_color
  @type  leftover: string

  @return: the new currentcolor and leftover as a tuple
  @rtype: ((int, int, int), string)
  """
  global ANSI_COLOR_REGEXP, DEFAULT_COLOR

  if type(textlist) == type(''):
    textlist = split_ansi_from_text(textlist)

  if leftover:
    first = leftover + textlist[0]
    matchob = ANSI_COLOR_REGEXP.search(first)
    if matchob:
      (b, e) = matchob.span()
      textlist.insert(0, first[:e])
      textlist[1] = first[e:]
    leftover = ''

  for color in textlist:
    if is_color_token(color):
      color = color[2:-1]

      # handles the case where it's ESC[m which is short-hand for ESC[0m
      if color == "":
        currentcolor = list(DEFAULT_COLOR)

      # handles other cases!
      else:
        color = color.split(";")
        for i in color:
          if not i.isdigit():
            continue

          i = int(i)

          if i == 0:
            # 0 is a reset
            currentcolor = list(DEFAULT_COLOR)
      
          elif i == 1:
            currentcolor[PLACE_BOLD] = 1

          elif i == 4:
            currentcolor[PLACE_UNDERLINE] = 1

          elif i == 5:
            currentcolor[PLACE_BLINK] = 1

          elif i == 7:
            currentcolor[PLACE_REVERSE] = 1


          elif i == 22:
            currentcolor[PLACE_BOLD] = 0

          elif i == 24:
            currentcolor[PLACE_UNDERLINE] = 0

          elif i == 25:
            currentcolor[PLACE_BLINK] = 0

          elif i == 27:
            currentcolor[PLACE_REVERSE] = 0


          elif i == 39:
            # sets default foreground
            currentcolor[PLACE_FG] = -1

          elif 30 <= i and i <= 37:
            # these are foreground attributes
            currentcolor[PLACE_FG] = i

          elif i == 49:
            # sets default background
            currentcolor[PLACE_BG] = -1

          elif 40 <= i and i <= 47:
            # these are background attributes
            currentcolor[PLACE_BG] = i

  # we're looking for leftover pieces here
  if len(textlist) > 0:
    mem = textlist[-1]
    esc = mem.find('\33')
    if esc != -1:
      for i in range(esc, len(mem)):
        c = mem[i]

        if c.isdigit() or c == ";" or c == "[":
          continue
        else:
          esc = -1

      if esc != -1:
        leftover = mem
      
  return currentcolor, leftover


def get_color(style):
  """
  Looks at the style (which is a comma separated list of 
  styles) and figures out the markup string and returns it.

  @param style: the style to retrieve markup for
  @type  style: text

  @return: the ansi code markup for the given style
  @rtype: string
  """
  styles = style.split(",")
  markup = ""
  for mem in styles:
    mem = mem.strip()
    if STYLEMAP.has_key(mem):
      markup = markup + STYLEMAP[mem] + ";"
  return chr(27) + "[" + markup[:-1] + "m"


def convert_tuple_to_ansi(token):
  """
  Takes in a color tuple like what figure_color creates
  and converts it into an ANSI color sequence.

  @param token: the color tuple
  @type  token: tuple of ints

  @return: the ANSI color string
  @rtype: string
  """
  color = []

  if token[PLACE_BOLD] == 1:
    color.append("1")

  if token[PLACE_UNDERLINE] == 1:
    color.append("4")

  if token[PLACE_BLINK] == 1:
    color.append("5")

  if token[PLACE_REVERSE] == 1:
    color.append("7")

  if token[PLACE_FG] != -1:
    color.append(str(token[PLACE_FG]))

  if token[PLACE_BG] != -1:
    color.append(str(token[PLACE_BG]))

  if len(color) == 0:
    return chr(27) + "[0m"

  return chr(27) + "[" + ";".join(color) + "m"

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
