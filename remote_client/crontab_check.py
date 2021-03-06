#!/usr/bin/env python
from subprocess import call
from os import environ
import os
import urllib2
from config_remote import config_remote
from TalkToServer import TalkToServer

runs = os.path.join(config_remote['currdir'], "runJob.sh")
server = config_remote['webserver_url']+"_queue"
environ['SGE_CELL'] = 'default'
environ['SGE_ROOT'] = '/var/lib/gridengine'

TalkToServer("pingtoserverrrr").IamAlive()

response = urllib2.urlopen(server)
for line in response:
    i = line.rstrip()
    command = 'qsub -N "Cdock_%s" %s %s' % (i, runs, i)
    check_if_exists = "qstat -j Cdock_%s" % (i)
    ret = call(check_if_exists, shell=True)
    if ret == 1:
        TalkToServer(i).tellJobWaiting()
        qsub = call(command, shell=True)
response.close()
