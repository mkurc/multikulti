# script for rebuilding from CA-trace to full atom of multimodel PDB file
# run by: $ python /path/to/this/script.py multimodel_file.pdb > out.log
# do not run by $ mod9vXX ./script.py or $ ./script.py

from modeller import *
from modeller.automodel import *    # Load the automodel class

from sys import argv
import tempfile
import re
import shutil
import os

# params
models_num = 3 # how many independent modeller runs to generate model and select one best scored by DOPE. Bigger number - longer run




class PdbParser:
    ''' Michal Jamroz 2015, BSD lic., not optimized '''
    def __init__(self, filename):
        self.data = open(filename, "r").read()
        self.codification = { "ALA" : 'A', "CYS" : 'C', "ASP" : 'D', "GLU" : 'E', "PHE" : 'F', "GLY" : 'G', "HIS" : 'H', "ILE" : 'I', "LYS" : 'K', "LEU" : 'L', "MET" : 'M', "MSE" : 'M', "ASN" : 'N', "PYL" : 'O', "PRO" : 'P', "GLN" : 'Q', "ARG" : 'R', "SER" : 'S', "THR" : 'T', "SEC" : 'U', "VAL" : 'V', "TRP" : 'W', "5HP" : 'E', "ABA" : 'A', "AIB" : 'A', "BMT" : 'T', "CEA" : 'C', "CGU" : 'E', "CME" : 'C', "CRO" : 'X', "CSD" : 'C', "CSO" : 'C', "CSS" : 'C', "CSW" : 'C', "CSX" : 'C', "CXM" : 'M', "DAL" : 'A', "DAR" : 'R', "DCY" : 'C', "DGL" : 'E', "DGN" : 'Q', "DHI" : 'H', "DIL" : 'I', "DIV" : 'V', "DLE" : 'L', "DLY" : 'K', "DPN" : 'F', "DPR" : 'P', "DSG" : 'N', "DSN" : 'S', "DSP" : 'D', "DTH" : 'T', "DTR" : 'X', "DTY" : 'Y', "DVA" : 'V', "FME" : 'M', "HYP" : 'P', "KCX" : 'K', "LLP" : 'K', "MLE" : 'L', "MVA" : 'V', "NLE" : 'L', "OCS" : 'C', "ORN" : 'A', "PCA" : 'E', "PTR" : 'Y', "SAR" : 'G', "SEP" : 'S', "STY" : 'Y', "TPO" : 'T', "TPQ" : 'F', "TYS" : 'Y', "TYR" : 'Y' }
        self.keys = self.codification.keys()
        self.seq = re.compile(r"^ATOM.{9}CA..(?P<seqid>.{3}).(?P<chainid>.{1})", flags=re.M)
        self.model_indices = re.compile(r'^MODEL.{6}(\d+)',flags=re.M)
        self.chains_order = []

    def getChains(self):
        if len(self.chains_order)==0:
            _ = self.getSequence()
        return self.chains_order

    def getModelIndices(self):
        return self.model_indices.findall(self.data)

    def getModel(self, model_idx):
        te = re.compile(r'MODEL.{6}'+str(model_idx)+'.*?ENDMDL',flags=re.DOTALL)
        out = te.search(self.data).group(0)
        return out[:-1]

    def getSequence(self):
        first_model = self.model_indices.findall(self.data)[0]
        model_body = self.getModel(first_model)
        s = self.seq.findall(model_body)
        chains_seq = {}
        chains_order = []
        for code, chain in s:
            if code not in self.keys:
                print("Unknown aminoacid: %s" % (code))
            if chain in chains_seq:
                chains_seq[chain] += self.codification[code]
            else:
                chains_seq[chain] = self.codification[code]
                chains_order.append(chain)
        self.chains_order = chains_order
        out = ""
        for c in chains_order:
            out += chains_seq[c]+"/"
        return out[:-1]

 
log.verbose()
env = environ()
env.io.atom_files_directory = ['.']

tempdir = tempfile.mkdtemp(suffix="tempmodeller_", dir=".")


parse = PdbParser(argv[1])
sequence = parse.getSequence()
chains = parse.getChains()
model_i = parse.getModelIndices()


class MyModel(automodel):
    global chains
    def special_patches(self, aln):
        self.rename_segments(segment_ids=chains)


def rob_model(model_idx) :
   global models_num 
   a = MyModel(env, alnfile  = model_idx+'PIR',knowns   = ("model"+model_idx), sequence = "refi", assess_methods=(assess.DOPE))
   a.md_level = refine.slow
   #a.auto_align()                      # get an automatic alignment
   a.starting_model= 1                 # index of the first tmp model
   a.ending_model  = models_num        # index of the last tmp model

   a.make()
   ok_models = filter(lambda x: x['failure'] is None, a.outputs)
   key = 'DOPE score'
   ok_models.sort(lambda a,b: cmp(a[key], b[key]))

   # Get top model
   m = ok_models[0]
   with open(m['name'],"r") as fr:
       with open("model"+model_idx+".pdb","w") as fw:
           for line in fr:
               fw.write(line)

for model in model_i:
    print("###################### REBUILDING OF MODEL %s ###################" %(model_i))
    input = "model"+model+".pdb"
    input2 = "model"+model
    with open(os.path.join(tempdir, input), "w") as mw:
        mw.write(parse.getModel(model))

    with open(os.path.join(tempdir, model+"PIR"),"w") as fpir:
        fpir.write(">P1;refi\n")
        fpir.write("sequence:refi::::::::\n")
        fpir.write(sequence+"*\n")
        fpir.write(">P1;"+input2+"\nstructureM:"+input2+":FIRST:@:END:@:::: \n"+sequence+"*\n\n")

    curr_dir = os.getcwd()
    os.chdir(tempdir)
    rob_model(model)
    os.chdir(curr_dir)


for model in model_i:
    shutil.copy(os.path.join(tempdir, "model"+model+".pdb"), argv[1]+"__"+"model_"+model+".pdb")
shutil.rmtree(tempdir)



