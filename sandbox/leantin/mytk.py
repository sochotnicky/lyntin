from Tkinter import *
import tkFont

class EventItem(object):
  def __init__(self, func = None):
    if (func):
      self.execute = func
  
  def execute(self, gui):
    raise NotImplementedError()

class Option(Frame):
  def value(self):
    """return the value for this option"""
    raise NotImplementedError()

class MCheck(Option):
  def __init__(self, root, name, default = 1):
    Option.__init__(self, root)
    var = IntVar()
    var.set(default)
    self.__chk = Checkbutton(self, text=name, variable=var)
    self.__val = var
    self.repack()
  
  def repack(self):
    self.__chk.pack(side=LEFT)
    self.pack(side=LEFT, fill=X)
    return
  
  def value(self):
    return self.__val.get()

class MNum(Option):
  def __init__(self, root, label, default):
    Option.__init__(self, root)
    ent = Entry(self, width = 3)
    ent.insert(0, default)
    self.__val = ent
    self.__lab = Label(self, text=label)
    self.repack()

  def repack(self):
    self.__val.pack(side=LEFT)
    self.__lab.pack(side=RIGHT)
    self.pack(side=LEFT)
    return

  def value(self):
    try:
      return int(self.__val.get())
    except ValueError:
      return 0

class MDropDown(Option):
  def __init__(self, root, labels, default = None):
    Option.__init__(self, root)
    self.__val = StringVar()
    if (default and default in labels):
      self.__val.set(default)
    else:
      self.__val.set(labels[0])
    self.__opt = OptionMenu(self, self.__val, *labels)
    self.repack()

  def repack(self):
    self.__opt.pack(side=TOP, fill=X)
    self.pack(side=LEFT)
    return

  def value(self):
    return self.__val.get()

class MDialog(Frame):
  def __init__(self, root):
    Frame.__init__(self, root)
    self.obs = {}
    self.displayed = []
    self.pack(side='top', fill=X)
    return

  def add(self, name, ob):
    self.obs[name] = ob
    return
  
  def __getitem__(self, name):
    return self.obs[name].value()

  def dump(self):
    for (k, v) in self.obs.items():
      print k, v.value()

def alter_ui(ui_ob, root, when, what):
  if (when == 'before' and what == 'text'):
    if 1:
      fnt = tkFont.Font(family="Courier", size=12)
    else:
      fnt = tkFont.Font(family="Fixedsys", size=12)

    ui_ob._status = Text(root, fg='white', bg='black', font=fnt, height=3)
    ui_ob._status.pack(side='bottom', fill='both')

    myframe = Frame(root)
    ui_ob._myopt = make_mywin(myframe)
    myframe.pack(side='top',fill=X)
  return

def make_mywin(root):
  s = MDialog(root)
  s.add('loot', MCheck(root, 'Loot', 0))
  s.add('jinx', MCheck(root, 'Jinx', 0))
  s.add('ff', MCheck(root, 'Fearie', 0))
  s.add('heal', MNum(root, 'Heal Below % HP', '65'))
  s.add('boozle', MNum(root, 'Boozle below # SP', '130'))
  s.add('spell_above1', MNum(root, 'primary spell %', '0'))
  s.add('spell_above2', MNum(root, 'second spell %', '0'))
  #s.add('spell', MDropDown(root, ('None', 'Spirit Disease', 'Soultap', 'Flamestrike', 'Hammer', 'Gloriole', 'Mixed SD/FS', 'Mixed SD/Soultap', 'Mixed SD/Hammer', 'Ice'), 'Spirit Disease'))
  s.add('spell', MDropDown(root, ('None', 'Spirit Disease', 'Soultap', 'Flamestrike', 'Hammer', 'Gloriole', 'Mixed SD/FS', 'Mixed SD/Soultap', 'Mixed SD/Hammer', 'Mixed SD/Glor', 'Ice'), 'Spirit Disease'))
  s.add('waterbreath', MCheck(root, 'wb', 0))
  s.add('shroud', MCheck(root, 'shroud', 0))
  s.add('blur', MCheck(root, 'blur', 0))
  s.add('armor', MDropDown(root, ('None', 'General', 'Slash', 'Crush', 'Thrust'), 'None'))
  s.add('sp_reserve', MNum(root, 'reserve', '0'))
  return s

def priest_ui(root):
  s = MDialog(root)
  s.add('loot', MCheck(root, 'Loot', 0))
  s.add('jinx', MCheck(root, 'Jinx', 0))
  s.add('ff', MCheck(root, 'Fearie', 0))
  s.add('heal', MNum(root, 'Heal Below % HP', '65'))
  s.add('boozle', MNum(root, 'Boozle below # SP', '130'))
  s.add('spell_above1', MNum(root, 'primary spell %', '0'))
  s.add('spell_above2', MNum(root, 'second spell %', '0'))
  s.add('spell', MDropDown(root, ('None', 'Spirit Disease', 'Soultap', 'Flamestrike', 'Hammer', 'Gloriole', 'Mixed SD/FS', 'Mixed SD/Soultap', 'Mixed SD/Hammer', 'Mixed SD/Glor'), 'Spirit Disease'))
  s.add('waterbreath', MCheck(root, 'wb', 0))
  s.add('shroud', MCheck(root, 'shroud', 0))
  s.add('sp_reserve', MNum(root, 'reserve', '0'))
  return s
