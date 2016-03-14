#!/usr/bin/env python
from sys import argv, exit
from shutil import rmtree
from glob import glob
import os
from subprocess import call
from config_remote import config_remote
from TalkToServer import TalkToServer
if len(argv) < 2:
    exit()

working_dir = config_remote['compute_directory']
jobid = argv[1]
pwd = os.getcwd()
scripts_dir = os.path.join(config_remote['currdir'], "cabsDock", "scripts")

S = TalkToServer(jobid)
S.tellJobRunning()

out_path = os.path.join(working_dir, jobid)
if not os.path.exists(out_path):
    os.makedirs(out_path)
os.chdir(out_path)

S.getStructureFile()
S.getLigandInfoFile()
S.getRestraintsFile()
S.getExcludedFile()
S.getConsoleFile()
S.getModelsToRemove()
simlen = S.getSimLength()

cabs_script = os.path.join(scripts_dir, "runThatShit.sh")
p = call(cabs_script+" "+str(simlen), shell=True)

# check if results exists
for d in ["CLUST", "MODELS", "TRAFS"]:
    if os.path.isdir(d):
        if len(glob(d+"/*")) == 0:
            S.tellJobError()
            exit(1)
    else:
        S.tellJobError()
        exit(1)
S.putResults()
S.putLigandChain()
S.tellJobDone()
rmtree(os.path.join(working_dir, jobid)) # remove working dir if job is done (succeeded)
