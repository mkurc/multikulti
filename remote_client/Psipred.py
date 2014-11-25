#!/usr/bin/env python
import tempfile
import re
from os import remove
from subprocess import Popen
from config_remote import config_remote


class Psipred:
    def __init__(self, sequence):
        f = tempfile.NamedTemporaryFile(mode='w', delete=False, dir=".")
        f.file.write(sequence)
        f.file.close()

        psipred = config_remote['psipred_path']
        p = Popen([psipred, f.name])
        # wait for terminate psipred
        p.communicate()

        with open(f.name+".horiz") as ff:
            data = ff.read()
            d = re.findall(r'^Pred: (\w+)$', data, re.M)
            self.secondary = "".join(d)
        remove(f.name)
        remove(f.name+".ss")
        remove(f.name+".ss2")
        remove(f.name+".horiz")

    def getSS(self):
        return self.secondary


if __name__ == "__main__":
    a = Psipred("ALALALALA").a.getSS()
