#!/usr/bin/env python
import re
from sys import argv

prev_num = []
curr_num = []
# 1 - proper chains, 2 - modified chains, correct coordinates
with open(argv[1], "r") as f:
    d = f.read()
    for e in re.findall(r"^ATOM.{17}(\w).*$", d, re.M):
        if e not in prev_num:
            prev_num.append(e)

with open(argv[2], "r") as f:
    d = f.read()
    for e in re.findall(r"^ATOM.{17}(\w).*$", d, re.M):
        if e not in curr_num:
            curr_num.append(e)

    assert len(curr_num)==len(prev_num)

# replace
    for i in range(len(prev_num)):
        d = re.sub(r'^(ATOM.{17})'+curr_num[i]+'(.*)$', r'\1%s\2'%(prev_num[i]), d,flags=re.M)
    print d
#ATOM      1  N   LYS A 123      34.810  -5.552  17.870  1.00  0.00            
