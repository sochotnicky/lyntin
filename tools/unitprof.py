import profile

def runlots(func, *vargs, **kargs):
  for mem in range(1000):
    func(vargs, kargs)

if __name__ == '__main__':
  import sys

  sys.path.insert(0, "../")

