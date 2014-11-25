#!/usr/bin/env python
from sys import argv, exit
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
scaling_factor = S.getScalingFactor()

cabs_script = os.path.join(scripts_dir,
                           "runThatShit.sh") + " %5.2f" % (float(scaling_factor))
p = call(cabs_script, shell=True)

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
S.tellJobDone()