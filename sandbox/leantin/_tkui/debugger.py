"""
This module defines what the deubbger looks like
and how debug events are created
"""
# python imports
import sys, traceback, cStringIO, code

# Tk imports
import Tkinter
import tkFont

# _tkui imports
import scrollers
import entry

class Debugger(object):
  """Tk based UI for handling interactive debugging sessions"""
  def __init__(self, root, run_this_soon, use_globals, **opts):
    self.run_this_soon = run_this_soon # we can call this directly, since we always catch our own exceptions
    self.globals = use_globals # environment the debugger will run in
    self.interp = code.InteractiveConsole(self.globals)

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
    def debug_callback():
      self.exec_input(text)
    self.run_this_soon(debug_callback)
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
      self.interp.push(exec_str.rstrip())
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
