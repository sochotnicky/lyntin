"""The basic Sock class used for Telnet IO to the mud and do Telnet style negotiation"""

# python imports
import telnetlib, zlib
# telnetlib exports squat by default, import some telnet negotiation constants
from telnetlib import IAC,DONT,DO,WONT,WILL,SE,NOP,GA,SB,ECHO,EOR
# and define some non-official ones
MCCP2 = chr(86)
MCCP1 = chr(85)

# debugging imports
import time
# nego char to text
nego_names = {IAC:'IAC',DONT:'DONT',DO:'DO',WILL:'WILL',WONT:'WONT',SE:'SE',NOP:'NOP',GA:'GA',SB:'SB',ECHO:'ECHO',EOR:'EOR',
              MCCP2:'MCCP2', MCCP1:'MCCP1'}
def trans(val):
  try:
    return nego_names[val]
  except:
    return 'x%d' % (ord(val))

class Sock(telnetlib.Telnet):
  def __init__(self, host, port, **opts):
    telnetlib.Telnet.__init__(self, host, port)
    self.shutdown = opts['shutdown']
    self.set_option_negotiation_callback(self.negotiate)
    self.last_write = time.time()
    self.echo = 1
    self.mccp = None
    self.mccp_step = 0 # 1, 2, 3, GO
    return

  def read(self):
    try:
      inp = self.read_very_eager()
      if (inp):
        print "Time since last write %4.2f" % (time.time() - self.last_write)
      return inp
    except EOFError:
      self.shutdown.shutdown()
      self.close()
    return

  def write(self, text):
    self.last_write = time.time()
    print "Writing", text
    try:
      return telnetlib.Telnet.write(self, text)
    except (Exception), e:
      print "Error", str(e)
      self.shutdown.shutdown()
      return None

  def negotiate(self, sock, command, option):
    print "NEGO %s/%s" % (trans(command), trans(option))
    if (command == ECHO):
      if (option == WILL):
        self.echo = 0
      elif (option == WONT):
        self.echo = 1
    self.do_mccp(sock, command, option)
    return

  def do_mccp(self, sock, command, option):
    if (self.mccp_step == 0 and command == WILL and option == MCCP2):
      self.sock.sendall("%s%s%s" % (IAC, DO, TELOPT_COMPRESS2))
      self.sock.sendall("%s%s%s" % (IAC, DONT, TELOPT_COMPRESS1))
      self.mccp_step = 1
    elif (self.mccp_step == 1 and command == SB and self.read_sb_data() == MCCP2):
      self.mccp_step = 2
    elif (self.mccp_step == 2 and command == SE):
      self.mccp_step = 3
      self.mccp = zlib.decompressobj(15)
    return

  def fill_rawq(self):
    """This relies on the internals of telnetlib.Telnet, it is mostly a copy"""
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
