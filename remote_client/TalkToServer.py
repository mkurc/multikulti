#!/usr/bin/env python
import requests
import bz2
import re
import gzip
import json
import urllib2
import os
from glob import glob
from multiprocessing import cpu_count
from re import compile, match
from config_remote import config_remote
from Psipred import Psipred


class TalkToServer:
    def __init__(self, jid):
        self.jid = str(jid)
        self.secret_key = config_remote['secret_key']
        self.webserver = config_remote['webserver_url']
        self.remoteuri = self.webserver + "_server_talking/" + self.secret_key
        + "/" + self.jid

        # delete user jobs
        url = self.webserver+"_deleteOldJobs"
        try:
            r = requests.get(url)
            if r.status_code != requests.codes.ok:
                print(" ERROR Problem with deleting old user jobs "
                      + str(r.status_code))
        except:
            print("problem with request to deleteOldJobs")

    def putResults(self):
        to_send = {}
        for d in ["CLUST", "MODELS", "TRAFS"]:
            for filename in glob(d+"/*.gz"):
                fn = filename.replace("CLUST", "clusters").replace("MODELS",
                                      "models").replace("TRAFS", "replicas")
                to_send[fn] = open(filename, "rb")
        print(to_send.keys())

        r = requests.post(self.remoteuri+"/SEND/", files=to_send)
        if r.status_code == requests.codes.ok:
            print("Results sent!")
        else:
            print("Results NOT sent" + str(r.status_code))

    def getStructureFile(self, output_path="input.pdb"):
        try:
            with open(output_path, "wb") as out:
                tmp = urllib2.urlopen(self.webserver+"compute_static/"
                                      + self.jid+"/input.pdb")
                out.write(tmp.read())
                tmp.close()
        except:
            print("ERROR: Nothing found!")

    def getScalingFactor(self):
        try:
            f = urllib2.urlopen(self.remoteuri+'/SCALFACTOR/')
            data = f.read()
            f.close()
            j = json.loads(data)
            return j['constraints_scaling_factor']
        except:
            print("ERROR: problem with scaling factor fetch")

    def getLigandInfo(self):
        '''
            get ligand sequence/ss
        '''
        try:
            f = urllib2.urlopen(self.remoteuri+'/LIGANDSEQ/')
            data = f.read()
            f.close()
            j = json.loads(data)
            if j['secstr'] == '':
                psipred = Psipred(j['sequence'])
                ss = psipred.getSS()
                # ss = "HHHHHH"
                j['secstr'] = ss
                self.putSecondaryStructureString(ss)
            return j
        except:
            print("ERROR: problem with ligand seq fetch")

    def getRestraints(self):
        try:
            f = urllib2.urlopen(self.remoteuri+'/RESTRAINTS/')
            data = f.read()
            f.close()
            j = json.loads(data)
            return j
        except:
            print("ERROR: problem with restraints fetch")

    def getRestraintsFileNew(self, output_file="restr.txt"):
        with open(output_file, "w") as fw:
            restr_s = self.getScalingFactor()
            fw.write("%5.2f\n" % (float(restr_s)))
            r = self.getRestraints()
            for row in r:
                fw.write("%50s WEIGHT %5.2f\n" % (row['def'], row['force']))

    def getRestraintsFile(self, output_file="restr.txt"):
        with open(output_file, "w") as fw:
            r = self.getRestraints()
            for row in r:
                fw.write("%50s WEIGHT %5.2f\n" % (row['def'], row['force']))

    def getLigandInfoFile(self, output_file="ligand.txt"):
        r = self.getLigandInfo()
        sec = r['secstr']
        seq = r['sequence']
        with open(output_file, "w") as fw:
            for ss, sq in zip(sec, seq):
                fw.write("%1s %1s\n" % (sq, ss))

    def putSecondaryStructureString(self, ss_string):
        d = {'ss': ss_string}
        r = requests.post(self.remoteuri+"/SENDSS/", data=d)

        if r.status_code == requests.codes.ok:
            print("Psipred prediction sent")
        else:
            print("Psipred SS not sent, %d" % (r.status_code))

    def putSecondaryStructure(self, ss_file):
        '''
            Sec str (ss_file) in *.horiz format
        '''
        with open(ss_file) as f:
            data = f.read()
            d = re.findall(r'^Pred: (\w+)$', data, re.M)
            secondary = "".join(d)
            d = {'ss': secondary}
            r = requests.post(self.remoteuri+"/SENDSS/", data=d)

            if r.status_code == requests.codes.ok:
                print("Psipred prediction sent")
            else:
                print("Psipred SS not sent %d" % (r.status_code))

    def IamAlive(self):  # PING PING PING
        try:
            cc = cpu_count()
            load = os.getloadavg()[2]  # 15 minutes avg
            percentage = int(100*load/cc)
            hostn = os.uname()[1]
            d = {'load': percentage, 'hostname': hostn}

            r = requests.post(self.remoteuri+"/LOAD/", data=d)

            if r.status_code != requests.codes.ok:
                print("Not announced, webserver disconnected!?, status: %d"
                      % (r.status_code))
        except:
            print("error with iamlive")

    def tellJobRunning(self):
        try:
            r = requests.get(self.remoteuri+"/S_R/")
            if r.status_code == requests.codes.ok:
                print("set job running %d" % (r.status_code))
            else:
                print("Not set >>job running<<, status: %d" % (r.status_code))
        except:
            print("error telljobrunning")

    def tellJobDone(self):
        try:
            r = requests.get(self.remoteuri+"/S_D/")
            if r.status_code == requests.codes.ok:
                print("set job DONE %d" % (r.status_code))
            else:
                print("Not set >>job done<<, status: %d" % (r.status_code))
        except:
            print("error telljobdone")

    def tellJobError(self):
        try:
            r = requests.get(self.remoteuri+"/S_E/")
            if r.status_code == requests.codes.ok:
                print("set job ERROR " % (r.status_code))
            else:
                print("Not set >>job error<<, status: %d" % (r.status_code))
        except:
            print("error telljoberror")

    def tellJobWaiting(self):
        try:
            r = requests.get(self.remoteuri+"/S_Q/")
            if r.status_code == requests.codes.ok:
                print("set job in queue %d" % (r.status_code))
            else:
                print("Not set >>job in queue<< status: %d" % (r.status_code))
        except:
            print("error telljobwaiting")

if __name__ == "__main__":
    a = TalkToServer("1360dac99d8d322")
    a.IamAlive()  # pinguj, ze zyje
    a.getStructureFile()
