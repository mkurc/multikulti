#!/usr/bin/env python

import requests
import bz2
import gzip
import json
import urllib2
import os
from multiprocessing import cpu_count
from re import compile,match
from config_remote import config_remote

class TalkToServer:
    def __init__(self,jid):
        self.jid = str(jid)
        self.secret_key = config_remote['secret_key']
        self.webserver = config_remote['webserver_url']
        self.remoteuri = self.webserver+"_server_talking/"+self.secret_key+"/"+self.jid

#        # delete user jobs
#        url = self.webserver+"_deleteOldJobs"
#        try:
#            r = requests.get(url)
#            if r.status_code == requests.codes.ok:
#                print "Probably (if any) deleted old user jobs "+str(r.status_code)
#            else:
#                print " ERROR Problem with deleting old user jobs "+str(r.status_code)
#        except:
#            print "problem with request to deleteOldJobs"

    def getStructureFile(self,output_path="input.pdb.gz"):
        try:
            with open(output_path,"wb") as out:
                tmp = urllib2.urlopen(self.webserver+"compute_static/"+self.jid+"/input.pdb.gz")
                out.write(tmp.read())
                tmp.close()
        except:
            print "ERROR: Nothing found!"
    def getScalingFactor(self):
        try:
            f = urllib2.urlopen(self.remoteuri+'/SCALFACTOR/')
            data = f.read()
            f.close()
            j = json.loads(data)
            return j
        except:
            print "ERROR: problem with scaling factor fetch"

    def getLigandInfo(self):
        '''
            get ligand sequence/ss
        '''
        try:
            f = urllib2.urlopen(self.remoteuri+'/LIGANDSEQ/')
            data = f.read()
            f.close()
            j = json.loads(data)
            return j
        except:
            print "ERROR: problem with ligand seq fetch"

    def IamAlive(self): # PING PING PING
        cc = cpu_count()
        load = os.getloadavg()[2] # 15 minutes avg
        percentage = int(100*load/cc)
        hostn = os.uname()[1]
        d = {'load': percentage, 'hostname': hostn}

        r = requests.post(self.remoteuri+"/LOAD/", data = d)

        if r.status_code == requests.codes.ok:
            print "I am healthy, fresh and ready to work.. annonunced.."
        else:
            print "Not announced, webserver disconnected!?, status: ", r.status_code
        try:
            pass
        except:
            print "Not announced, webserver disconnected!?, status: " 
    def tellJobRunning(self):
        try:
            r = requests.get(self.remoteuri+"/S_R/")
            if r.status_code == requests.codes.ok:
                print "set job running "+str(r.status_code)
            else:
                print "Not set >>job running<<, webserver disconnected!?, status: ", r.status_code
        except:
            print "Not announced, webserver disconnected!?, status: " 
    def tellJobDone(self):
        try:
            r = requests.get(self.remoteuri+"/S_D/")
            if r.status_code == requests.codes.ok:
                print "set job DONE "+str(r.status_code)
            else:
                print "Not set >>job done<<, webserver disconnected!?, status: ", r.status_code
        except:
            print "Not announced, webserver disconnected!?, status: " 
    def tellJobError(self):
        try:
            r = requests.get(self.remoteuri+"/S_E/")
            if r.status_code == requests.codes.ok:
                print "set job ERROR "+str(r.status_code)
            else:
                print "Not set >>job error<<, webserver disconnected!?, status: ", r.status_code
        except:
            print "Not announced, webserver disconnected!?, status: " 
    def tellJobWaiting(self):
        try:
            r = requests.get(self.remoteuri+"/S_Q/")
            if r.status_code == requests.codes.ok:
                print "set job in queue  "+str(r.status_code)
            else:
                print "Not set >>job in queue<<, webserver disconnected!?, status: ", r.status_code
        except:
            print "Not announced, webserver disconnected!?, status: " 

if __name__ == "__main__":
    a = TalkToServer("5b2d094fe276eb")
    a.IamAlive() # pinguj, ze zyje
    a.getStructureFile() # pobierz plik struktury (gzipowany). Domyslnie do ./input.pdb.gz
    print a.getLigandInfo()
    print a.getScalingFactor()
    a.tellJobError()
    a.tellJobRunning()

