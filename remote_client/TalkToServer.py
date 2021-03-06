#!/usr/bin/env python
import requests
import re
import json
import urllib2
import os
from glob import glob
from multiprocessing import cpu_count
from config_remote import config_remote
from Psipred import Psipred


class TalkToServer:
    def __init__(self, jid):
        self.jid = str(jid)
        self.secret_key = config_remote['secret_key']
        self.webserver = config_remote['webserver_url']
        self.remoteuri = self.webserver + "_server_talking/" + self.secret_key + "/" + self.jid

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
            for filename in glob(d+"/*.gz") + ["klastry.txt", "energy.txt", "top1000.pdb.gz", "maps.tar.gz"]:
                fn = filename.replace("CLUST", "clusters")
                fn = fn.replace("MODELS", "models")
                fn = fn.replace("TRAFS", "replicas")
                to_send[fn] = open(filename, "rb")

        r = requests.post(self.remoteuri+"/SEND/", files=to_send)
        if r.status_code == requests.codes.ok:
            print("Results sent! %s" % (self.jid))
        else:
            print("Results NOT sent %s %s" + str(r.status_code, self.jid))

    def _replace_empty_chain(self,file_handler):
        d=file_handler.read().split("\n")
        chain_set = set()

        for line in d:
            if len(line)>21 and line.startswith("ATOM"):
                chain = line[21]
                chain_set.update(chain)
        uniq = ' ' # very rarely it stay as is
        for e in ['X','Y','Z','I','J','K','L','M']:
            if e not in chain_set:
                uniq = e
                break

        o=""
        if " " in chain_set:
            for line in d:
                if len(line)>21 and "ATOM" in line and line[21]==" ":
                    line = line[:21]+uniq+line[22:]+"\n"

                o += line
        else:
            o = "\n".join(d)

        return o

    def getStructureFile(self, output_path="input.pdb"):
        try:
            with open(output_path, "wb") as out:
                tmp = urllib2.urlopen(self.webserver+"compute_static/"
                                      + self.jid+"/input.pdb")
                out.write(self._replace_empty_chain(tmp))
                tmp.close()
        except:
            print("ERROR: Nothing found!")

    def _getJson(self, url):
        try:
            f = urllib2.urlopen(self.remoteuri+url)
            data = f.read()
            f.close()
            return json.loads(data)
        except:
            print("ERROR: problem with "+url)

    def getScalingFactor(self):
        return self._getJson('/SCALFACTOR/')['constraints_scaling_factor']

    def getJobName(self):
        return self._getJson('/JOBNAME/')['jobname']

    def getSimLength(self):
        return self._getJson('/LENGTH/')['sim_length']

    def getLigandInfo(self):
        j = self._getJson('/LIGANDSEQ/')

        if j['secstr'] == '':
            psipred = Psipred(j['sequence'])
            ss = psipred.getSS()
            # ss = "HHHHHH"
            j['secstr'] = ss
            self.putSecondaryStructureString(ss)
        return j

    def getRestraints(self):
        return self._getJson('/RESTRAINTS/')

    def getExcluded(self):
        return self._getJson('/EXCLUDED/')

    def getConsole(self):
        return self._getJson('/CONSOLE/')

    def getModelsToRemove(self):
        j = self._getJson('/SKIPMODELS/')
        if len(j) > 0:
            os.mkdir("junk")
        for i in range(len(j)):
            row = j[i]
            model_id = row['model_id'].strip()
            model_body = row['model_body']
            old_jid = row['prev_jid'].strip()
            with open("junk/cluster_skip_oldjid_"+old_jid+"__oldid_"+model_id+".pdb", "w") as fw:
                fw.write(model_body)

    def getRestraintsFile(self, output_file="restr.txt"):
        with open(output_file, "w") as fw:
            restr_s = self.getScalingFactor()
            fw.write("%5.2f\n" % (float(restr_s)))
            r = self.getRestraints()
            for row in r:
                for spl in row['def'].split(","):
                    fw.write("%50s WEIGHT %5.2f\n" % (spl.strip(),
                                                      row['force']))

    def getExcludedFile(self, output_file="excluded.txt"):
        with open(output_file, "w") as fw:
            r = self.getExcluded()
            for row in r:
                for spl in row['excluded'].split(","):
                    fw.write("%50s\n" % (spl.strip()))

    def getConsoleFile(self, output_file="console.txt"):
        with open(output_file, "w") as fw:
            r = self.getConsole()
            fw.write(r['console'])

    def getLigandInfoFile(self, output_file="ligand.txt"):
        r = self.getLigandInfo()
        sec = r['secstr']
        seq = r['sequence']
        with open(output_file, "w") as fw:
            for ss, sq in zip(sec, seq):
                fw.write("%1s %1s\n" % (sq, ss))

    def putLigandChain(self):
        with open("SEQ", "r") as seq:
            ll = seq.readlines()[-1].split()
            # 5   GLY A  1  1.00
            d = {'chain': ll[2]}
            r = requests.post(self.remoteuri+"/LIGCHAIN/", data=d)

            if r.status_code != requests.codes.ok:
                print("Ligand chain id not sent, %d" % (r.status_code))

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

    def _tell(self, url):
        try:
            r = requests.get(self.remoteuri+url)
            if r.status_code == requests.codes.ok:
                print("set "+url+" %d %s" % (r.status_code, self.jid))
            else:
                self.saySomething("error, check logs "+r.status_code)
                print("Not set >>"+url+"<<, status: %d %s" % (r.status_code, self.jid))
        except:
            print("error conn: "+url)

    def tellJobRunning(self):
        self._tell('/S_R/')

    def tellJobDone(self):
        self._tell('/S_D/')

    def tellJobError(self):
        self._tell('/S_E/')

    def tellJobWaiting(self):
        self._tell('/S_Q/')

    def saySomething(self, msg):
        try:
            d = {'msg': msg}
            r = requests.post(self.remoteuri+"/MSG/", data=d)
            if r.status_code == requests.codes.ok:
                print("set "+msg+" %d" % (r.status_code))
            else:
                print("Not set >>"+msg+"<<, status: %d" % (r.status_code))
        except:
            print("error conn: "+msg)

if __name__ == "__main__":
    a = TalkToServer("1360dac99d8d322")
    a.IamAlive()  # pinguj, ze zyje
    a.getStructureFile()
