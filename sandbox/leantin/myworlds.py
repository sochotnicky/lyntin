from mudpacks import mudbasic, overdrive, threek
import login
import mytk

class EchoMud(mudbasic.Mud):
  host = 'localhost'
  port = 7 # echo
  name = 'echo'

class EchoLogin(login.Login):
  name = 'echo'
  mud_class = EchoMud
  def ui_init(sess_ui):
    mytk.priest_ui(sess_ui.top)
    return

class ODLogin(login.Login):
  name = 'overdrive'
  mud_class = overdrive.ODMud
  player_class = overdrive.ODPlayer
  
  user_name = 'guest'
  password = ''
  def ui_init(sess_ui):
    mytk.priest_ui(sess_ui.top)
    return
  
class ThreeK(login.Login):
  name = '3k'
  mud_class = threek.ThreeKMud

  user_name = 'guest'
  password = ''
