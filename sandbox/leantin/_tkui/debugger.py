"""
This module defines what the deubbger looks like
and how debug events are created
"""
# python imports
import sys, traceback, cStringIO

# Tk imports
import Tkinter
import tkFont

# _tkui imports
import events
import scrollers
import entry

class _DebugEvent(events.Event):
  def __init__(self, exec_string):
    self.exec_string = exec_string
    return
  def execute(self, tkui):
    if (not tkui._debugger):
      tkui.write("FAIL: interactive DebugEvent, but the debugger isn't running\n")
    else:
      tkui._debugger.exec_input(self.exec_string)
    return

class Debugger(object):
  """Tk based UI for handling interactive debugging sessions"""
  def __init__(self, root, event_queue, use_globals, **opts):
    self.event_queue = event_queue
    self.globals = use_globals # environment the debugger will run in

    self.window = Tkinter.Toplevel(root) # make our own window to run in
    self.window.geometry("%dx%d" % (self.window.maxsize()))
    
    self.window.title("Leanlyn Interactive Debugger")
    self.output_f = Tkinter.Frame(self.window)
    self.command_f = Tkinter.Frame(self.window)
    
    self.font = opts.pop('font', tkFont.Font(family="Fixedsys", size=12)) # passed in, or punt and go with something safe
    
    self.command_txt = entry.HistoryEntry(self.command_f,
                                          input_callback = self.make_debug_event,
                                          # tk options
                                          font=self.font,
                                          fg='white', bg='black',
                                          insertbackground='yellow',
                                          insertwidth='2',
                                         )
    self.output_txt = scrollers.ScrolledANSI(self.output_f,
                                             transfer_focus_to=self.command_txt,
                                             transfer_events_to=self.command_txt,
                                            )

    # pack em all up
    self.command_txt.pack(side='bottom', fill='both')
    self.command_f.pack(side='bottom', fill='both')
    self.output_txt.pack(side='top', fill='both', expand=1)
    self.output_f.pack(side='top', fill='both', expand=1)
    return

  def make_debug_event(self, text):
    self.event_queue.put(_DebugEvent(text))
    return
    
  def exec_input(self, exec_str):
    """Handle user input
    If this looks identical to PLWM's inspect.py module it is just a coincidence *wink*
    """
    # We replace the standard files with temporary ones.  stdin is
    # redirected from /dev/null, and stdout and stderr is sent to
    # a StringIO object.
	
    old_stdin = sys.stdin
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    f = cStringIO.StringIO()
    try:
      sys.stdin = open('/dev/null', 'r')
      sys.stdout = sys.stderr = f

      # Compile and execute the expressions.  print statements
      # and expression values will be sent to the StringIO
      # object, as will any exception traceback
	    
      try:
        c = compile(exec_str, '<string>', 'single')
        exec c in self.globals
      except:
        traceback.print_exc(None, f)

    finally:
      # Restore the standard files
      sys.stdin = old_stdin 
      sys.stdout = old_stdout
      sys.stderr = old_stderr

    self.output_txt.write(f.getvalue())
    return
    
# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
