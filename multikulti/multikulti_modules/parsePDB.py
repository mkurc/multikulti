#!/usr/bin/env python

import bz2
import gzip
import json
import urllib2
from re import compile,match
def arraytostring(ar):
    i = []
    for e in ar:
        i.append("%d-%d"%(e))
    return ", ".join(i)

class PdbParser:
    def __init__(self,filehandler,fmt='pdb'):
        self.fmt = fmt
        self.codification = { "ALA" : 'A', "CYS" : 'C', "ASP" : 'D', "GLU" : 'E', "PHE" : 'F', "GLY" : 'G', "HIS" : 'H', "ILE" : 'I', "LYS" : 'K', "LEU" : 'L', "MET" : 'M', "MSE" : 'M', "ASN" : 'N', "PYL" : 'O', "PRO" : 'P', "GLN" : 'Q', "ARG" : 'R', "SER" : 'S', "THR" : 'T', "SEC" : 'U', "VAL" : 'V', "TRP" : 'W', "5HP" : 'E', "ABA" : 'A', "AIB" : 'A', "BMT" : 'T', "CEA" : 'C', "CGU" : 'E', "CME" : 'C', "CRO" : 'X', "CSD" : 'C', "CSO" : 'C', "CSS" : 'C', "CSW" : 'C', "CSX" : 'C', "CXM" : 'M', "DAL" : 'A', "DAR" : 'R', "DCY" : 'C', "DGL" : 'E', "DGN" : 'Q', "DHI" : 'H', "DIL" : 'I', "DIV" : 'V', "DLE" : 'L', "DLY" : 'K', "DPN" : 'F', "DPR" : 'P', "DSG" : 'N', "DSN" : 'S', "DSP" : 'D', "DTH" : 'T', "DTR" : 'X', "DTY" : 'Y', "DVA" : 'V', "FME" : 'M', "HYP" : 'P', "KCX" : 'K', "LLP" : 'K', "MLE" : 'L', "MVA" : 'V', "NLE" : 'L', "OCS" : 'C', "ORN" : 'A', "PCA" : 'E', "PTR" : 'Y', "SAR" : 'G', "SEP" : 'S', "STY" : 'Y', "TPO" : 'T', "TPQ" : 'F', "TYS" : 'Y', "TYR" : 'Y' }
        keys = self.codification.keys()
        seq = compile(r"^ATOM.{9}CA..(?P<seqid>.{3})")
        self.onlycalfa=""
        atm = compile(r"^ATOM.{9}(CA|N |C |O ).{7}(?P<resid>.{4})(?P<x>.{12})(?P<y>.{8})(?P<z>.{8})")
        mod = compile(r"^ENDMDL") # TODO nie jestem pewien
        ter = compile(r"^TER") # TODO nie jestem pewien
        self.trajectory = []
        self.sequence = ""
        model = []
        self.resindexes = []

        f = filehandler
        lines=f.readlines()
        end = len(lines)-1
        counter=0
        firstchain=True
        tmp = []
        for line in lines:
            data = atm.match(line)

            data_seq = seq.match(line)
            if data_seq and firstchain:
                seqid = data_seq.groups()[0]
                if seqid in keys:
                    self.sequence += self.codification[seqid]
                else:
                    self.sequence += "X"

            if data:
                self.onlycalfa+=line
                dg =  data.groups()
                if dg[0] == 'CA':
                    tmp.append(int(dg[1]))
            if ter.match(line):
                self.resindexes.append(tmp)
                tmp = []
                self.onlycalfa+=line
            if mod.match(line) or counter==end:
                break
            counter+=1    
        filehandler.seek(0)
    def getMissing(self):
        brk = []
        for indexes in self.resindexes:
            first = indexes[0]
            for i in range(1,len(indexes)):
                if indexes[i] -1 != first:
                    brk.append(str(first)+ "-" + str(indexes[i]) )
                first  = indexes[i]
        return ", ".join(brk)

    def getBody(self):
        return self.onlycalfa
    def savePdbFile(self,outfilename):
        fw = gzip.open(outfilename,"wb")
        if self.fmt=='pdb':
            fw.write(self.onlycalfa)
        fw.close()

    def getSequence(self):
        return self.sequence


if __name__ == "__main__":
    a = PdbParser("/home/mjamroz/aaa.xyz",fmt='xyz',bzip=False)
    #a.saveModelXYZ(argv[1]+".xyz")
    print a.getSequence()
