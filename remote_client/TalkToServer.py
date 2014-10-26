#!/usr/bin/env python

import requests
from requests_toolbelt import MultipartEncoder
import bz2
import gzip
import json
import urllib2
from re import compile,match
from config_remote import config_remote

def arraytostring(ar):
    i = []
    for e in ar:
        i.append("%d-%d"%(e))
    return ", ".join(i)

class TalkToServer:
    def __init__(self,jid):
        self.jid = str(jid)
        self.secret_key = config_remote['secret_key']
        self.webserver = config_remote['webserver_url']
        self.remoteuri = self.webserver+"_server_talking/"+self.secret_key+"/"+self.jid

        # delete user jobs
        url = self.webserver+"_deleteOldJobs"
        try:
            r = requests.get(url)
            if r.status_code == requests.codes.ok:
                print "Probably (if any) deleted old user jobs "+str(r.status_code)
            else:
                print " ERROR Problem with deleting old user jobs "+str(r.status_code)
        except:
            print "problem with request to deleteOldJobs"
    def _bzip(self,filename):
        with open(filename, 'rb') as contentfile:
            content = contentfile.read()
            bzipped = bz2.compress(content)
            return bzipped
    #def getUserParameters(self):

    def getUserFile(self,output_path,filetype):
        if filetype=='pdb':

            print "downloading "+self.webserver+"compute_static/"+self.jid+"/input.pdb.bz2"
            tmp = urllib2.urlopen(self.webserver+"compute_static/"+self.jid+"/input.pdb.bz2")
        else:
            print "downloading "+self.webserver+"compute_static/"+self.jid+"/input.xyz.bz2"
            tmp = urllib2.urlopen(self.webserver+"compute_static/"+self.jid+"/input.xyz.bz2")

        out = open(output_path,"wb")
        out.write(tmp.read())
        out.close()

    def getUserParameters(self, jid):
        f = urllib2.urlopen(self.remoteuri+'/INFO/')
        data = f.read()
        f.close()
        j = json.loads(data)
        return j

    def uploadFile(self,filename): # TODO not very secure!!
        ''' 
            File will be uploaded to /compute_static/jid/results/filename on remote webserver
        '''

        url = self.remoteuri+"/SEND/"
        m = MultipartEncoder( # TODO w knotFinderze to bylo spierdolone i nie podawalo plikow (ale tam byly dwa - moze to cos znaczy)
                fields = {
                    'file': (filename+".bz2", self._bzip(filename), 'application/x-bzip2') 
                    }
                )
        try:
            r = requests.post(url, data = m, headers = {'Content-Type': m.content_type})
            if r.status_code == requests.codes.ok:
                print filename+" uploaded "+str(r.status_code)
            else:
                print filename+" NOT uploaded "+str(r.status_code)
        except:
            print "NOT uploaded, Probably server down"
    def updateUserJobDB(self,values,table):        
        url = self.remoteuri+"/UPD/"
        m = MultipartEncoder(fields={'values': values,'table':table})
        try:
            r = requests.post(url, data = m, headers = {'Content-Type': m.content_type})
            if r.status_code == requests.codes.ok:
                print values+" sent. "+str(r.status_code)
            else:
                print values+" not. "+str(r.status_code)
        except:
            print "NOT sent. Probably server down"

    def tellSomething(self,message):
        url = self.remoteuri+"/MSG/"
        m = MultipartEncoder(fields={'message': message})
        try:
            r = requests.post(url, data = m, headers = {'Content-Type': m.content_type})
            if r.status_code == requests.codes.ok:
                print message, " said",r.status_code
            else:
                print message, " NOT said, status: ", r.status_code
        except:
            print "NOT uploaded, Probably server down"
    def IamAlive(self): # PING PING PING
        try:
            r = requests.get(self.remoteuri+"/PING/")
            if r.status_code == requests.codes.ok:
                print "I am healthy, fresh and ready to work.. annonunced.."
            else:
                print "Not announced, webserver disconnected!?, status: ", r.status_code
        except:
            print "Not announced, webserver disconnected!?, status: " 
    def tellJobTimeout(self):
        try:
            r = requests.get(self.remoteuri+"/S_TOUT/")
            if r.status_code == requests.codes.ok:
                print "set job timeout "+str(r.status_code)
            else:
                print "Not set >>job timeout<<, webserver disconnected!?, status: ", r.status_code
        except:
            print "timeout Not announced, webserver disconnected!?, status: " 
    def tellJobPending(self):
        try:
            r = requests.get(self.remoteuri+"/S_P/")
            if r.status_code == requests.codes.ok:
                print  "set job pending "+str(r.status_code)
            else:
                print "Not set >>job pending<<, webserver disconnected!?, status: ", r.status_code
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
            r = requests.get(self.remoteuri+"/S_W/")
            if r.status_code == requests.codes.ok:
                print "set job waiting "+str(r.status_code)
            else:
                print "Not set >>job waiting<<, webserver disconnected!?, status: ", r.status_code
        except:
            print "Not announced, webserver disconnected!?, status: " 

if __name__ == "__main__":
    a = PdbParser("/home/mjamroz/aaa.xyz",fmt='xyz',bzip=False)
    #a.saveModelXYZ(argv[1]+".xyz")
    print a.getSequence()
