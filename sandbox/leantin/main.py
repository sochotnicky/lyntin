#!/usr/bin/python2.3
# python imports
import socket, Queue, time
# our imports
import sock, ui, tkui, mudcommands, engine, catcher, libmisc
import session
import mytk

__version__ = "$Revision: 1.1 $"

"""This is the main loop for leanlyn, currently it is just a test harness"""

class Config(object):
  def __init__(self, parent = None):
    self.__parent = None
    return
  def __getattribute__(self, name):
    if (hasattr(self, name)):
      return getattr(self, name)
    if (self.__parent is not None and hassattr(self.__parent, name)):
      return getattr(self.__parent, name)
    raise AttributeError()

def test_main():
  import myworlds
  e = engine.Engine()
  e.launch_ui(tkui.Tkui)
  session.Connect.do_command(e, '_default') # not-so secret name for an unattached session
  e.ui.launch_debugger(engine=e)
  e.ui.run()

if (__name__ == '__main__'):
  test_main()
