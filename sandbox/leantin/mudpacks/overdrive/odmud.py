from mudpacks import mudbasic
class ODMud(mudbasic.Mud):
  host = 'overdrive.concentric.net'
  port = 5195
  name = 'OD'

  name_prompt = 'Enter character name:'
  pass_prompt = 'Password:'
  prompt = '> '
  strip_prompt = 1
