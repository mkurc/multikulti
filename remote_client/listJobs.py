#!/usr/bin/env python
from subprocess import call
from os import environ
import os
import urllib2
from multiprocessing import cpu_count
from os import getloadavg
from config_remote import config_remote
from TalkToServer import TalkToServer
from sys import exit

runs = os.path.join(config_remote['currdir'],"runJob.py")
server = config_remote['webserver_url']+"_queue"
maxjobs = config_remote['userjob_pool_max_cpus']

TalkToServer("pingtoserverrrr").IamAlive()
# check server load
current_load = int(getloadavg()[0])
cpus_num = int(cpu_count())
free_cpus = cpus_num - current_load
maxjobs = min(free_cpus, maxjobs)
if maxjobs<1:
    exit(1)


response = urllib2.urlopen(server)
itere = 0
for line in response:
    i = line.rstrip()
    command = '%s' %(i)
    print command
    itere += 1
    if itere == maxjobs:
        break
    #qsub = call(command,shell=True) TODO
response.close()
