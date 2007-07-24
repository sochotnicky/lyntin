#!/usr/bin/python

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
# $Id: argparser.py,v 1.7 2007/07/24 00:39:03 willhelm Exp $
#########################################################################
"""
This provides the ArgumentParser class which parses X{command argument}s
automatically into a dictionary as well as a series of Parser classes
which handle single arguments and TypeCheckers which handle validating
user input values and converting them into other types (string -> int...).

It's very complex, however, it allows us to nicely centralize a lot
of the duties involved in parsing user input into one place rather than
doing it in every single command over and over again.  This way commands
can specify their syntax line and the ArgParser handles the rest returning
to the commands a dict with the name/value pairs including argument 
defaults.

When building an arg spec, you can pass into the ArgumentParser several
options which change the way it parses the user input.

Supported options::

  stripBraces (default=on): whether all arguments should have 
            braces stripped before being parsed

  noparsing (default=off): doesn't insure that all arguments are
            parsed.  works well when matched with limitparsing=0 to 
            provide a syntax line for commands that parse their own 
            input

  limitparsing:int (default=-1): only parse this number of tokens 
            into dict, the rest of the input line goes into 
            argdict["input"]

  nodefaults:bool (default=off): turn off default lookups through variables.

Refer to the modules.lyntincmds and modules.tintincmds for examples
on arg specs and commands and how it all intertwines.
"""
import re, time
import utils

defaultOptions={ "stripBraces": 1, "noparsing": 0, "limitparsing": -1, "nodefaults":0 }
optionParser = None

class ParserException(Exception):
  pass

class ArgumentParser:
  """
  This is the actual ArgumentParser class.  Each command gets its
  own ArgumentParser.  It handles taking in user input and parsing
  it into a series of arguments which are then placed in a dict and
  passed to the command function.  This centralizes parsing user
  input into one place and also enables us to centralize type checking,
  argument checking, and conversion in one place as well.
  """
  def __init__(self, argspec, argoptions=None):
    """
    Initializes the ArgParser instance so it can then parse user
    input for arguments.  It also generates the syntaxline which
    is used by the help system to tell the user what the command
    syntax is.

    @param argspec: the argument specification for the command
    @type  argspec: string

    @param argoptions: the options to use to parse the argspec
    @type  argoptions: string
    """
    # the syntax line is automatically generated from the argspec.
    # we print it out whenever we have a ParserException in the user input.
    self.syntaxline = ""

    if argoptions:
      self.buildOptions(argoptions)
    else:
      self.options = defaultOptions.copy()
    self.buildParsers(argspec)
    return

  def getOption(self, optionname):
    """
    Gets a specific option from the arg options hash as passed into the
    __init__.

    @param optionname: the name of the option
    @type  optionname: string

    @return: the value of the option or None
    @rtype: varies (string or int)
    """
    if self.options.has_key(optionname):
      return self.options[optionname]
    else:
      return None

  def buildOptions(self, argoptions):
    """
    Set the options for this ArgumentParser
    key=value values in argoptions get put directly into self.options
    other values in argoptions get set to 1 in self.options.

    example 1::

      argoptions="ignorall loud:boolean=true"
      self.options={"ignorall":1,"loud":1}

    example 2::

      argoptions="lalala wewewewe=hahaha"
      self.options={"lalala":1,"wewewewe"="hahaha")

    @param argoptions: the argoptions as passed into __init__.
    @type  argoptions: string
    """
    # FIXME - this should operate on a locally created dict and pass
    # that dict back to __init__ which should set self.options and
    # self.argoptions
    global optionParser
    self.argoptions=argoptions
    self.options=defaultOptions.copy()

    if optionParser == None:
      optionParser = ArgumentParser("otherOptions* otherValuedOptions**")
    argdict = optionParser.parse(argoptions)

    for key in argdict.keys():
      if key=="otherOptions":
        for otherOption in argdict[key]:
          self.options[otherOption] = 1
          if len(otherOption)>3 and otherOption[0:2]=="no":
            self.options[otherOption[2:]] = 0
      elif key=="otherValuedOptions":
        for otherKey in argdict[key].keys():
          self.options[otherKey] = argdict[key][otherKey]
      else:
        self.options[key] = argdict[key]

    # set types for certain options
    self.options["limitparsing"] = int(self.options["limitparsing"])

  def buildParsers(self, argspec):
    """
    Build up the set of parsers to be used for argument parsing.

    The argspec follows the following format:

      1. [argname[:argtype]]+ 
      2. [argname[:argtype]=defaultval]+ 
      3. [argname:argtype*] 
      4. [argname[:argtype]]+ 
      5. [argname[:argtype]=defaultval]+ 
      6. [argname:argtype**]

    Any of the arguments can be specified either by name or populated
    by position, except for arguments after the index collector
    argument.  Those must be specified by name only.

    Once one default value is given all further arguments must have
    default values (except collector arguments, which have implicit
    default arguments of the empty list and the empty map).

    For examples see the test code at the end of argparser.py.

    @param argspec: the argument specification to use to parse future
        user input
    @type  argspec: string
    """
    self.parsers = {}
    self.indexparsers = []
    self.extraindexparser = None
    self.extranamedparser = None

    self.argspec = self.split(argspec, buildsyntaxline=1)

    parsedspec = self.argspec

    doneWithIndices = 0
    defaultSeen = 0
    for i in range(0,len(parsedspec)):
      namedCollector = 0
      indexCollector = 0
      argname, argdef = parsedspec[i]
      if argname.find(":") > -1:
        argname,typespec = argname.split(":",1)
      else:
        # extra argname assignment here is just for consistency
        argname, typespec = argname, "string"

      if len(argname) >= 1 and argname.endswith("*"):
        if argdef != None:
          raise ParserException, "cannot specify a default value for a collection argument (%s=%s)" % (argname, argdef)

        if len(argname) >= 2 and argname.endswith("**"):
          argname = argname[:-2]
          if i < len(parsedspec) -1:
            raise ParserException, "named collection argument must be the last argument (%s)" % (argname)
          parser = ExtraNamedParser(self, argname)
          namedCollector = 1

        else: #this is an index collection argument
          argname = argname[:-1]
          parser = ExtraIndexParser(self, argname)
          indexCollector = 1
          doneWithIndices = 1
          
      else:
        parser = Parser(self,argname)

      typechecker = _createTypeChecker(typespec)
      if not typechecker:
        raise ParserException, "Unknown type specifier: %s" % (typespec)

      parser.setTypeChecker(typechecker)

      if argdef != None:
        parser.setDefault(parser.parse(argdef))
        defaultSeen = 1

      if defaultSeen and not parser.defaultset:
        raise ParserException, "Argument without default value (%s) seen after default values already specified" % (argname)
      
      if not namedCollector and not indexCollector:
        if not doneWithIndices:
          self.indexparsers.append(parser)
        if self.parsers.has_key(argname):
          raise ParserException, "Multiple argument named %s specified." % (argname)
        self.parsers[argname] = parser
      elif namedCollector:
        self.extranamedparser = parser
        self.parsers[argname] = parser
      elif indexCollector:
        self.extraindexparser = parser
        self.parsers[argname] = parser
    
  def parse(self, input, defaultresolver=None):
    """
    Takes an input string and produces the populated dictionary
    matching self's argspec.  

    @param input: the user input string
    @type  input: string

    @param defaultresolver: A function that will take an argument 
        name and return a default value (None if there should be none) 
        to override builtin defaults.
    @type  defaultresolver: function

    @return: the populated dictionary of all the args and values
    @rtype: dict

    @raise ParserException: if extra arguments are encountered without
        appropriate collection arguments specified, or if required arguments
        are missing, or if arguments passed in aren't valid
    """    
    argdict = {}

    arguments = self.split(input, self.getOption("limitparsing"))

    foundNamedArg = 0
    for i in range(0,len(arguments)):
        key,val = arguments[i]

        if val == None:
          if foundNamedArg and not self.extraindexparser:
            raise ParserException, "Non-named argument (%s) found after Named argument" % (key)
          if i < len(self.indexparsers):
            parser = self.indexparsers[i]
          elif self.extraindexparser:
            parser = self.extraindexparser
          else:
            raise ParserException, "Unexpected argument received %s" % (key)
          parser.parseInto(i, key, argdict)
        else:
          foundNamedArg = 1
          if self.parsers.has_key(key):
            parser = self.parsers[key]
          else:
            matchedkeys = [ arg for arg in self.parsers.keys() if arg.find(key) == 0 ]

            if len(matchedkeys) == 1:
              parser = self.parsers[matchedkeys[0]]
            elif self.extranamedparser:
              parser = self.extranamedparser
            else:
              if len(matchedkeys) == 0:
                raise ParserException("Invalid named argument: %s=%s" % (key,val))
              else:
                raise ParserException("Ambiguous named argument: %s=%s %s" % (key, val, matchedkeys))
            
          parser.parseInto(key, val, argdict)


    # now check that everything has been specified, putting in defaults 
    # where available
    for key in self.parsers.keys():
      if not argdict.has_key(key):
        # gotta be careful here with the extra defaultset value since
        # the parser may parse a string into None, or anything really
        default = None
        defaultset = 0
        parser = self.parsers[key]

        if not self.getOption("nodefaults") and defaultresolver:
          default = defaultresolver(key)
          if default != None:
            default = parser.parse(default)
            defaultset = 1
            
        if not defaultset and parser.defaultset:
          default = parser.default
          defaultset = 1
        
        if not defaultset and not self.getOption("noparsing"):
          raise ParserException, "Must specify a value for argument %s" % (key)
        else:
          argdict[key] = default
          
    return argdict

  def split(self, input, maxsplit=-1, buildsyntaxline=0):
    """
    Take an input string and tokenizes it into a list of pairs.
    Tokens with equal signs come back as (key,value) pairs, those
    without come back as (argument,None)

    {}s are treated like quotes, and everything between the {}s is
    ignored.

    Any amount of white space between arguments is ignored.  (No empty
    arguments are returned.)

    "\\" (single backslash) escapes anything, including =, {, }, 
    \\ (single backslash), and any character, so "\\a" (single 
    backslash then a) becomes "a" in the argument, and
    "\\n\\o\\t\\a\\d\\r\\a\\g\\o\\n" (a series of single backslashes 
    followed by a letter) is the same as "notadragon".

    After maxplit arguments are parsed (all of the arguments if maxsplit 
    < 0), we'll stop and return the rest of input as the final item.

    @param input: the user input to tokenize
    @type  input: string

    @param maxsplit: the maximum number of pairs to split
    @type  maxsplit: int (-1 if no maxplit)

    @param buildsyntaxline: whether or not to build the syntax
        line as we're going along (this method is used both when
        the ArgParser is initialized as well as for parsing
        user input)
    @type  buildsyntaxline: int (0 or 1)

    @return: the split input
    @rtype: list of 2-length-tuples

    @raises ParserException: if \\ (single backslash) is found at the end 
        of the line or if mismatched { or } are found
    """
    bracketdepth = 0
    arg = ""
    val = None
    equalsign = 0
    arguments = []
    while input and (maxsplit < 0 or len(arguments) < maxsplit):
      nextchar = input[0:1]
      input = input[1:]

      if nextchar == " " or nextchar == "\t":
        if not bracketdepth:
          # We've completed a full argument
          if arg!="":
            arguments.append( (arg,val) )
            if buildsyntaxline:
              synarg = arg.upper()
              if synarg.endswith("*"):
                synarg = synarg[:-1] + "..."

              if val and len(val) > 0:
                synarg = synarg + "=" + val

              if equalsign == 1:
                self.syntaxline += "[<%s>] " % synarg
              else:
                self.syntaxline += "[%s] " % synarg

          arg = ""
          val = None
          equalsign = 0
        else:
          if val != None:
            val = val + nextchar
          else:
            arg = arg + nextchar
      elif nextchar == "\\":
        if input == "":
          raise ParserException, "\\ at end of line."
        else:
          nextchar = input[0:1]
          input = input[1:]
          if val != None:
            val = val + nextchar
          else:
            arg = arg + nextchar
      elif nextchar == "}":
        bracketdepth = bracketdepth - 1
        if bracketdepth < 0:
          raise ParserException, "mismatched }"
        if val != None:
          val = val + nextchar
        else:
          arg = arg + nextchar
      elif nextchar == "{":
        bracketdepth = bracketdepth + 1
        if val != None:
          val = val + nextchar
        else:
          arg = arg + nextchar
      elif val == None and bracketdepth == 0 and nextchar == "=":
        val = ""
        equalsign = 1
      else:
        if val != None:
          val = val + nextchar
        else:
          arg = arg + nextchar

    if bracketdepth:
      raise ParserException, "Mismatched {"

    if arg != "":
      arguments.append( (arg, val) )
      if buildsyntaxline:
        synarg = arg.upper()
        if synarg.endswith("*"):
          synarg = synarg[:-1] + "..."

        if val and len(val) > 0:
          synarg = synarg + "=" + val

        if equalsign == 1:
          self.syntaxline += "[<%s>] " % synarg
        else:
          self.syntaxline += "[%s] " % synarg

      arg = ""
      val = ""

    if input:
      arguments.append( ("input", input) )
    
    return arguments

class Parser:
  """
  This is the base class for the parsers that argumentparser uses to
  actually populate the dictionary with each argument.
  """
  def __init__(self, argparser, argname):    
    """
    Initializes the Parser.

    @param argparser: the argparser instance this belongs to
    @type  argparser: argparser.ArgParser

    @param argname: the name of the argument this parser handles type
        and value checking for.
    @type  argname: string
    """
    self.argname = argname
    self.default = None
    self.defaultset = 0
    self.typechecker = None
    self.argparser = argparser

  def setTypeChecker(self, typechecker):
    """
    Sets the typechecker.  The Parser then uses this to check the
    values coming in before setting them on the name/value dict.

    @param typechecker: the typechecker to set
    @type  typechecker: argparser.TypeChecker
    """
    self.typechecker = typechecker

  def parseInto(self, key, val, argdict):
    """
    Populates the argument dictionary with the appropriate value.

    @param key: the argument name
    @type  key: string

    @param val: the argument value
    @type  val: string

    @param argdict: the argument dictionary to populate
    @type  argdict: dict

    @raises ParserException: if multiple values were given for the argument
    """
    if argdict.has_key(self.argname):
      raise ParserException, "Multiple values for argument %s given" % (self.argname)
    else:
      argdict[self.argname] = self.parse(val)

  def parse(self, val):
    """
    Parses the value according to this parser and its associated 
    Typechecker.  We both typecheck it here (making sure it's valid)
    as well as convert it (i.e. strings -> ints, strings -> regexps...).

    @param val: the value to parse
    @type  val: string

    @return: the newly adjusted value
    @rtype: varies
    """
    if self.argparser.getOption("stripBraces"):
      val = utils.strip_braces(val)
    if self.typechecker:
      return self.typechecker.check(val)
    else:
      return val

  def setDefault(self, val):
    """
    Sets the default value for this Parser which is used when no
    other value is given.  Also sets the "defaultset" member which
    tells the Parser that it has a default value.

    @param val: the default value
    @type  val: string or int
    """
    self.default = val
    self.defaultset = 1
      
class ExtraIndexParser(Parser):
  """
  This class captures the parsing behaviour for an index collector.
  for each call to parseInto an entry is put into the list value in
  the argument dictionary.
  """
  def __init__(self, argparser, argname):
    """
    Initializes the Parser.

    @param argparser: the argparser instance this belongs to
    @type  argparser: argparser.ArgParser

    @param argname: the name of the argument this parser handles type
        and value checking for.
    @type  argname: string
    """
    Parser.__init__(self,argparser,argname)
    self.default = []
    self.defaultset = 1
    
  def parseInto(self, key, val, argdict):
    """
    Populates the argument dictionary with the appropriate value.

    @param key: the argument name
    @type  key: string

    @param val: the argument value
    @type  val: string

    @param argdict: the argument dictionary to populate
    @type  argdict: dict

    @raises ParserException: if multiple values were given for the argument
    """
    val = self.parse(val)
    if argdict.has_key(self.argname):
      argdict[self.argname].append(val)
    else:
      argdict[self.argname] = [val]

class ExtraNamedParser(Parser):
  """
  This class captures the parsing behaviour for a named value collector.
  for each call to parseInto a new key=value pair is put into a map
  in the argument dictionary.
  """
  def __init__(self,argparser,argname):
    """
    Initializes the Parser.

    @param argparser: the argparser instance this belongs to
    @type  argparser: argparser.ArgParser

    @param argname: the name of the argument this parser handles type
        and value checking for.
    @type  argname: string
    """
    Parser.__init__(self,argparser,argname)
    self.default = {}
    self.defaultset = 1
    
  def parseInto(self, key, val, argdict):
    """
    Populates the argument dictionary with the appropriate value.

    @param key: the argument name
    @type  key: string

    @param val: the argument value
    @type  val: string

    @param argdict: the argument dictionary to populate
    @type  argdict: dict

    @raises ParserException: if multiple values were given for the argument
    """
    val=self.parse(val)
    if argdict.has_key(self.argname):
      if argdict.has_key(key) or argdict[self.argname].has_key(key):
        raise ParserException, "Multiple values given for argument %s" % (key)
      argdict[self.argname][key] = (val)
    else:
      argdict[self.argname] = {key:val}


typecheckers = {}

def _createTypeChecker(typespec):
  """
  Factory method for instantiating TypeChecker subclasses based on the
  type being passed in.

  First the typespec is split at its first colon.

  The first element (the typename) of the typespec is used as a key
  into typecheckers to find the function/class object to call to
  create the typechecker. 

  The rest of the typespec (the typeargs) is used with the function to
  construct the typechecker desired.

  @param typespec: the type that we're checking.  i.e. "string", "int", ...
      This translates directly into a specific TypeChecker.
  @type  typespec: string

  @return: the TypeChecker subclass created
  @rtype: argparser.TypeChecker
  """
  typespec = typespec.split(":",1)
  if len(typespec) == 1:
    typename, typeargs = typespec[0],None
  else:
    typename, typeargs = typespec

  if not typecheckers.has_key(typename):
    return None
  typechecker = typecheckers[typename](typename,typeargs)

  return typechecker

class TypeChecker:
  """
  Trivial base class for argument checkers
  """
  def __init__(self, typename, typeargs):
    """
    Initializes the TypeChecker.  Over-ridden by all the TypeChecker 
    subclasses.

    @param typename: the name of the type
    @type  typename: string

    @param typeargs: the arguments passed to the TypeChecker to initialize
        it
    @type  typeargs: tuple
    """
    return

  def check(self, arg):
    """
    Over-ridden by all the TypeChecker subclasses.

    @param arg: the argument to check the type-hood and convert
    @type  arg: string

    @returns: the converted argument
    @rtype: varies
    """
    return arg

class StringChecker(TypeChecker):
  """
  Essentiallly the same as the trivial base class, but it's explicit
  that we just return the string we take in without any transformation.
  """
  def __init__(self, typename, typeargs):
    if typeargs:
      raise ParserException, "TypeArgs (%s) specified for non-configurable type (%s)" % (typeargs, typename)
    return

  def check(self, arg):
    """
    Returns the string we're looking at without any transformation.

    @param arg: the argument to pass back
    @type  arg: string

    @return: the argument
    @rtype:  string
    """
    return arg

typecheckers["string"] = StringChecker

class IntChecker(TypeChecker):
  """
  Accept only integer values and return integer objects.
  """
  def __init__(self, typename, typeargs):
    """
    Initializes the TypeChecker.  Over-ridden by all the TypeChecker 
    subclasses.

    @param typename: the name of the type
    @type  typename: string

    @param typeargs: the arguments passed to the TypeChecker to initialize
        it
    @type  typeargs: tuple

    @raises ParserException: If typeargs are passed in--this is 
        non-configurable.
    """
    if typeargs:
      raise ParserException, "TypeArgs (%s) specified for non-configurable type (%s)" % (typeargs, typename)

  def check(self,arg):
    """
    Verifies the arg is of type int and converts it to an int.

    @param arg: the argument to check the type-hood and convert
    @type  arg: string

    @returns: the converted argument from string to int
    @rtype: int
    """
    return int(arg)

typecheckers["int"] = IntChecker

class BooleanChecker(TypeChecker):
  """
  Accept only boolean values using the utils.convert_boolean function.
  """
  def __init__(self, typename, typeargs):
    if typeargs:
      raise ParserException, "TypeArgs (%s) specified for non-configurable type (%s)" % (typeargs, typename)

  def check(self,arg):
    """
    Verfies the argument is a boolean (using utils.convert_boolean function)
    and converts it to a boolean value (0 or 1).

    @param arg: the argument to check the type-hood and convert
    @type  arg: string

    @returns: the converted argument
    @rtype: int (0 or 1)

    @raises ParserException: if the arg is not a valid boolean
    """
    ret = utils.convert_boolean(arg)
    if ret == 1 or ret == 0:
      return ret

    raise ParserException("Invalid boolean value specified: %s" % (arg))

typecheckers["boolean"] = BooleanChecker

class BooleanOrNoneChecker(TypeChecker):
  """
  Accept only boolean values or special "not specified" values.  Booleans
  are handled by utils.convert_boolean.  Values not handled by that
  function will throw an exception.
  """
  def __init__(self, typename, typeargs):
    if typeargs:
      raise ParserException, "TypeArgs (%s) specified for non-configurable type (%s)" % (typeargs, typename)

  def check(self,arg):
    """
    Verfies the argument is a boolean (using utils.convert_boolean function)
    and converts it to a boolean value (0 or 1).  Also handles None, "-"
    and the empty string as None.

    @param arg: the argument to check the type-hood and convert
    @type  arg: string

    @returns: the converted argument
    @rtype: int (0 or 1) or None

    @raises ParserException: if the arg is not a valid boolean
    """
    ret = utils.convert_boolean(arg)
    if ret == 1 or ret == 0:
      return ret
    elif arg == "None" or arg == "-" or arg == "":
      return None
    else:
      raise ParserException, "Invalid boolean value specified: %s" % (arg)

typecheckers["booleanornone"] = BooleanOrNoneChecker

class EvalChecker(TypeChecker):
  """
  Evaluate its input argument as python code and return the resulting object.
  """
  def __init__(self, typename, typeargs):
    if typeargs:
      raise ParserException, "TypeArgs (%s) specified for non-configurable type (%s)" % (typeargs, typename)

  def check(self,arg):
    """
    Assumes the argument is valid python code.  It evaluates the code
    and returns the result.

    @param arg: the argument to evaluate
    @type  arg: string

    @returns: the result of eval(arg)
    @rtype: varies

    @raises ParserException: if we can't eval the argument
    """
    try:
      return eval(arg)
    except Exception, e:
      raise ParserException, "Error eval-ing argument (%s): %s" % (arg, e)

typecheckers["eval"] = EvalChecker 

class TimeSpanChecker(TypeChecker):
  """
  Accepts an amount of time and converts it to a number of seconds.
  """
  def __init__(self, typename, typeargs):
    if typeargs:
      raise ParserException, "TypeArgs (%s) specified for non-configurable type (%s)" % (typeargs, typename)

  def check(self, arg):
    """
    Assumes the argument is a time span.

    @param arg: the timespan
    @type  arg: string

    @returns: the number of seconds in the timespan
    @rtype: int

    @raise ParserException: if the timespan is invalid
    """
    try:
      time = utils.parse_timespan(arg)
      return time
    except:
      raise ParserException, "Invalid timespan specified %s" % (arg,)

typecheckers["timespan"] = TimeSpanChecker
  
class TimeChecker(TypeChecker):
  """
  Accepts a date specification.

  Will also accept a time specification and apply it as a delta from
  _now_.  converts to the standard seconds-from_epoch. 
  """
  def __init__(self, typename, typeargs):
    if typeargs:
      raise ParserException, "TypeArgs (%s) specified for non-configurable type (%s)" % (typeargs, typename)

  def check(self, arg):
    """
    Assumes the argument is valid python code.  It evaluates the code
    and returns the result.

    @param arg: the time argument
    @type  arg: string

    @returns: the number of seconds since the epoch
    @rtype: int

    @raise ParserException: if the arg is not a valid time
    """
    time = utils.parse_time(arg)
    if time != None:
      return time
    else:
      raise ParserException, "Invalid time specified %s" % (arg,)

typecheckers["time"] = TimeChecker
  
class ChoiceChecker(TypeChecker):
  """
  Allows for a value to come from a selection of different strings.
  Automatically expands to one of them if it is uniquely specified.

  Typeargs should be a |-delimitted list of possibly values
  """
  def __init__(self, typename, typeargs):
    """
    Uses the typeargs to set the choices availble.
    """
    if not typeargs:
      raise ParserException("TypeArgs (%s) not specified for %s type - must allow at least one choice." % (typeargs, typename) )
    self._choices = typeargs.split("|")

  def check(self, arg):
    """
    Checks the arg against a series of choices that were presented
    when this checker was instantiated.  So you could say that valid
    values of this argument are "high" and "low" and if the argument
    value the user passed in was "blue", then we would raise a 
    ParserException since that's not a valid value.

    @param arg: the argument
    @type  arg: string

    @raise ParserException: if the arg is not a valid choice
    """
    possibilities = []
    for item in self._choices:
      if item.find(arg) == 0:
        possibilities.append(item)
        if len(item) == len(arg):
          return item
    if len(possibilities) == 0 or len(possibilities) > 1:
      raise ParserException, "Invalid argument, must be one of %s." % (self._choices,)
    else:
      return possibilities[0]

typecheckers["choice"] = ChoiceChecker

class ReChecker(TypeChecker):
  """
  Compiles the incoming argument as a regular expression.
  """
  def __init__(self, typename, typeargs):
    if typeargs:
      raise ParserException, "TypeArgs (%s) specified for non-configurable type (%s)" % (typeargs, typename)

  def check(self, arg):
    """
    Converts the string into a regular expression.  Raises whatever
    exceptions re.compile raises.

    @param arg: the argument
    @type  arg: string

    @return: the compiled regular expression
    @rtype: Re
    """
    return re.compile(arg)

typecheckers["re"] = ReChecker

if __name__ == '__main__':
  testargs = {
    ("arg1 arg2 arg3* arg4**",None):["test1 test3 test5 test7 help=wahoo woo=weewee"],
    ("mapname*",None):["3k mapper by notadragon","lalala"],
    ("mapname*","noparsing"):["3k mapper by notadragon"],
    ("option* quiet:boolean=true",None):["a b c quiet=false d","a b c quiet=true","x b c"]} 

  for argspec,argoptions in testargs.keys():
    argparser = ArgumentParser(argspec,argoptions)
    print "Argspec: %s" % (argspec)
    if argoptions: print "Argopts: %s" % (argoptions)
    for args in testargs[(argspec,argoptions)]:
      print "Args   : %s" % (args)
      print "Dict   : %s" % (`argparser.parse(args)`)

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
