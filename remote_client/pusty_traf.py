#!/usr/bin/env python
from sys import argv, exit
from glob import glob
import os
from time import sleep

from subprocess import call
from config_remote import config_remote
from TalkToServer import TalkToServer

working_dir = config_remote['compute_directory']
jobid = argv[1]
pwd = os.getcwd()
S = TalkToServer(jobid)
out_path = os.path.join(working_dir, jobid)
os.chdir(out_path)
sleep(60*60) # czekaj 1h
if os.path.getsize("TRAF") < 300:
    S.saySomething("hop sa sa, pusty TRAF w "+jobid)
