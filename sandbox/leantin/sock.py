"""The basic Sock class used for Telnet IO to the mud and do Telnet style negotiation"""

# python imports
import telnetlib, zlib
# telnetlib exports squat by default, import some telnet negotiation constants
from telnetlib import IAC,DONT,DO,WONT,WILL,SE,NOP,GA,SB,ECHO,EOR,AYT
# and define some non-official ones
MCCP2 = chr(86)
MCCP1 = chr(85)

# debugging imports
import time
# nego char to text
nego_names = {IAC:'IAC',DONT:'DONT',DO:'DO',WILL:'WILL',WONT:'WONT',SE:'SE',NOP:'NOP',GA:'GA',SB:'SB',ECHO:'ECHO',EOR:'EOR',
              MCCP2:'MCCP2', MCCP1:'MCCP1', AYT:'AYT'}
def trans(val):
  try:
    return nego_names[val]
  except:
    return 'x%d' % (ord(val))

class Sock(telnetlib.Telnet):
  def __init__(self, host, port, **opts):
    """ Connect a TCP/IP socket to host:port
        The 'shutdown' option should be a libMisc.Flag object
        If the 'echo_callback' option is passed we will call echo_callback(0|1) immediately
        If the 'timeout' option is passed we will switch to non-blocking IO with that timeout
        after our ECHO state changes
    """
    telnetlib.Telnet.__init__(self, host, port)
    self.shutdown = opts.get('shutdown', None)
    self.echo_callback = opts.get('echo_callback', None)
    self.set_option_negotiation_callback(self.read_negotiate)
    self.last_write = time.time()
    self.echo = 1
    self.mccp = None
    self.mccp_step = 0 # 1, 2, 3, GO

    # we do this to help guess if a line is a prompt, instead of newline terminated
    real_sock = self.get_socket()
    timeout = opts.get('timeout', 0)
    if (timeout):
      real_sock.settimeout(timeout)
    return

  def read(self):
    """ read some data from the socket
        no length of data is garunteed
        will raise a socket.timeout if the 'timeout' option was used
    """
    try:
      inp = self.read_some()      
      return inp
    except EOFError:
      self.shutdown.flag_true()
      self.close()
    return

  def write(self, text):
    """ Write text to the socket.
        Handles escaping of telnet special chars like IAC
    """
    self.last_write = time.time()
    try:
      return telnetlib.Telnet.write(self, text)
    except (Exception), e:
      print "Error", str(e)
      if (self.shutdown is not None):
        self.shutdown.flag_true()
      return None

  def send_negotiate(self, command, option = ''):
    """ Utitily function to send an IAC + command + option to the socket """
    self.sock.sendall('%s%s%s' % (IAC, command, option))
    return

  def read_negotiate(self, sock, command, option):
    """ Called whenever there is a negotation on the stream """
    print "NEGO %s/%s" % (trans(command), trans(option))
    if (option == ECHO):
      # change our state
      if (command == WILL):
        self.echo = 0
        self.send_negotiate(DO, ECHO)
      elif (command == WONT):
        self.echo = 1
        self.send_negotiate(DONT, ECHO)
      # all let the callback know about it, if any
      if (self.echo_callback):
        self.echo_callback(self.echo)

    # and give MCCP and chance to handle this too
    self.do_mccp(sock, command, option)
    return

  def do_mccp(self, sock, command, option):
    if (self.mccp_step == 0 and command == WILL and option == MCCP2):
      self.send_negotiate(DO, MCCP2)
      self.send_negotiate(DONT, MCCP1)
      self.mccp_step = 1
    elif (self.mccp_step == 1 and command == SB):
      self.mccp_step = 2
    elif (self.mccp_step == 2 and command == SE and self.read_sb_data() == MCCP2):
      self.mccp_step = 3
      self.mccp = zlib.decompressobj(15)
    return

  def fill_rawq(self):
    """This relies on the internals of telnetlib.Telnet, it is mostly a copy.
       We have to override this because MCCP needs to decompress the stream
       before it is scanned for telnet special characters.
    """
    if self.irawq >= len(self.rawq):
      self.rawq = ''
      self.irawq = 0
      buf = self.sock.recv(50)
    self.msg("recv %s", `buf`)
    self.eof = (not buf)
    if (self.mccp):
      self.rawq = self.rawq + self.mccp.decompress(buf)
    else:
      self.rawq = self.rawq + buf
    return

def test_mccp():
  tob = Sock('lensmoor.org', 3500)
  tob.interact()

if (__name__ == '__main__'):
  dummy = 1
  #test_mccp()
  
