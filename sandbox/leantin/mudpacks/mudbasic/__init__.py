
class Player(object):
  """A boring object that just stores other stuff"""
  log_dir = None
  
  def __init__(self): pass
  def sess_init(self, sess):
    """called after the session has been set up,
    gives us a chance to attach to session interfaces"""
    return

class Mud(object):
  host = 'localhost'
  port = -1
  name = None
  name_prompt = None
  pass_prompt = None

  prompt = ''
  strip_prompt = 0
  def __init__(self): pass
  def sess_init(self, sess):
    """called after the session has been set up,
    gives us a chance to attach to session interfaces
    """
    return
