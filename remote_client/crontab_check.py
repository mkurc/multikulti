#!/usr/bin/env python
from subprocess import call
from os import environ
import os
import urllib2
from config_remote import config_remote
from TalkToServer import TalkToServer
from sys import exit

runs = os.path.join(config_remote['currdir'],"runJob.py")
server = config_remote['webserver_url']+"_queue"
environ['SGE_CELL']='default'
environ['SGE_ROOT']='/var/lib/gridengine'

TalkToServer("pingtoserverrrr").IamAlive()

response = urllib2.urlopen(server)
for line in response:
    i = line.rstrip()
    command = 'qsub -N "A3D_%s" %s %s' %(i,runs,i)
    print command
    #qsub = call(command,shell=True) TODO
response.close()
