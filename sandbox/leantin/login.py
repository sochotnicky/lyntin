from mudpacks import mudbasic

class LoginMeta(type):
  """A tiny metaclass to help classes register themselves automagically"""

  def __init__(cls, name, bases, dict):
    cls.register(cls)
    if ('ui_init' in dict):
      setattr(cls, 'ui_init', staticmethod(dict['ui_init']))
    return

class Login(object):
  __metaclass__ = LoginMeta
  all = {}
  def register(ob):
    """ob can be a class or instance, we don't care"""
    if (ob.name):
      Login.all[ob.name] = ob
    return
  register = staticmethod(register)
  
  name = '' # name this pairing is called
  user_name = '' # user name
  password = '' # plain text password
  
  mud_class = mudbasic.Mud # Mud class to use for this login
  player_class = mudbasic.Player # Player class to use for this login
  def ui_init(session_ui): pass
