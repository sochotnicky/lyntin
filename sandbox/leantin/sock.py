""" our telnet class """

# python imports
import rtelnetlib as telnet
# our imports
import libmisc

class Sock(telnet.Telnet):
  def __init__(self, host=None, port=23, **opts):
    shutdown = opts.pop('shutdown', libmisc.Flag())
    echo_callback = opts.pop('echo_callback', None)
    telnet.Telnet.__init__(self, host, port, **opts)
    self.shutdown = shutdown
    
    self.handlers[telnet.ECHO] = telnet.NegoECHO(callback=echo_callback)
    naws = telnet.NegoNAWS(self.rawwrite)
    self.update_size = naws.update_size
    self.handlers[telnet.NAWS] = naws
    self.handlers[telnet.TTYPE] = telnet.NegoTTYPE(['lyntinCVS', 'vt102', 'ansi', 'stop asking'])
    self.handlers[telnet.MCCP2] = telnet.NegoMCCP(self) # he needs a self to do stuff with the buffer
    self.handlers[telnet.EOR] = telnet.will_nego
    self.handlers[telnet.TELOPT_EOR] = telnet.raise_prompt

  def do_shutdown(self):
    try:
      self.shutdown.flag_true()
    except: pass # in case we were passed an int instead
    return
