#!/usr/bin/env python
from sys import argv, exit
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

# cabs_script = os.path.join(scripts_dir, "runThatShit.sh")
# + " input.pdb ligand.txt restr.txt " + scaling_factor
cabs_script = os.path.join(scripts_dir, "runThatShit.sh") + " %5.2f" % (scaling_factor)
p = call(cabs_script, shell=True)

# for files in .....
for f in ["clip.ogv", "clip.mp4", "clip.webm", "A3D.csv", "input.pdb"]:
    if not os.path.isfile(f):
        S.tellJobError()
        exit(1)

S.putResults()
S.tellJobDone()
