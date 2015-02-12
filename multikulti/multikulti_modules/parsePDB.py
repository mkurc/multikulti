#!/usr/bin/env python

import gzip
import json
from re import compile, sub


def arraytostring(ar):
    i = []
    for e in ar:
        i.append("%d-%d" % (e))
    return ", ".join(i)


class PdbParser:
    def __init__(self, filehandler, chain=''):
        self.codification = {"ALA" : 'A', "CYS" : 'C', "ASP" : 'D', "GLU" : 'E', "PHE" : 'F', "GLY" : 'G', "HIS" : 'H', "ILE" : 'I', "LYS" : 'K', "LEU" : 'L', "MET" : 'M', "MSE" : 'M', "ASN" : 'N', "PYL" : 'O', "PRO" : 'P', "GLN" : 'Q', "ARG" : 'R', "SER" : 'S', "THR" : 'T', "SEC" : 'U', "VAL" : 'V', "TRP" : 'W', "5HP" : 'E', "ABA" : 'A', "AIB" : 'A', "BMT" : 'T', "CEA" : 'C', "CGU" : 'E', "CME" : 'C', "CRO" : 'X', "CSD" : 'C', "CSO" : 'C', "CSS" : 'C', "CSW" : 'C', "CSX" : 'C', "CXM" : 'M', "DAL" : 'A', "DAR" : 'R', "DCY" : 'C', "DGL" : 'E', "DGN" : 'Q', "DHI" : 'H', "DIL" : 'I', "DIV" : 'V', "DLE" : 'L', "DLY" : 'K', "DPN" : 'F', "DPR" : 'P', "DSG" : 'N', "DSN" : 'S', "DSP" : 'D', "DTH" : 'T', "DTR" : 'X', "DTY" : 'Y', "DVA" : 'V', "FME" : 'M', "HYP" : 'P', "KCX" : 'K', "LLP" : 'K', "MLE" : 'L', "MVA" : 'V', "NLE" : 'L', "OCS" : 'C', "ORN" : 'A', "PCA" : 'E', "PTR" : 'Y', "SAR" : 'G', "SEP" : 'S', "STY" : 'Y', "TPO" : 'T', "TPQ" : 'F', "TYS" : 'Y', "TYR" : 'Y' }
        keys = self.codification.keys()
        self.sequences = {}
        self.onlycalfa = ""
        self.chain = chain

        self.canumber = 0
        self.allnumber = 0
        seq = compile(r"^ATOM.{9}CA..(?P<seqid>.{3}).(?P<chain>.{1})(?P<resid>.{4})") # TODO zle dla alternatywnych
        if chain != '':
            ch = "|".join(list(chain))
            seq_c = compile(r"^ATOM.{9}CA.( |A).{4}("+ch+")")
            atm = compile(r"^ATOM.{9}(.{2}).( |A).{4}("+ch+")(?P<resid>.{4})(?P<x>.{12})(?P<y>.{8})(?P<z>.{8})")
        else:
            atm = compile(r"^ATOM.{9}(.{2}).( |A).{5}(?P<resid>.{4})(?P<x>.{12})(?P<y>.{8})(?P<z>.{8})")
            seq_c = compile(r"^ATOM.{9}CA.( |A).{4}")

        ter = compile(r"^TER")  # TODO nie jestem pewien
        mod = compile(r"^ENDMDL")  # TODO nie jestem pewien
        self.trajectory = []
        self.sequence = ""
        self.resindexes = []

        f = filehandler
        lines = f.readlines()
        end = len(lines)-1
        counter = 0
        tmp = []
        chains_order = []

        for line in lines:
            line = sub(r'^HETATM(.{7})', r'ATOM  \1',line)
            data = atm.match(line)
            data_seq = seq.match(line)
            if seq_c.match(line):
                self.canumber += 1
            if data_seq:
                seqid = data_seq.group('seqid').strip()
                chainid = data_seq.group('chain').strip()
                if chainid not in chains_order:
                    chains_order.append(chainid)
                resid = data_seq.group('resid').strip()

                if seqid in keys:
                    self.sequence += self.codification[seqid]
                    s = self.codification[seqid]
                else:
                    s = "X"
                    self.sequence += "X"

                if chainid in self.sequences.keys():
                    self.sequences[chainid] += s
                else:
                    self.sequences[chainid] = s

            if data:
                self.allnumber += 1
                self.onlycalfa += line
                dg = data.groups()
                if dg[0] == 'CA':
                    tmp.append(int(data.group('resid')))
            if ter.match(line) or counter == end:
                self.resindexes.append(tmp)
                tmp = []
                self.onlycalfa += line
            if (mod.match(line) and len(self.onlycalfa) > 1) or counter == end:
                break
            counter += 1
        filehandler.seek(0)

# chain numbering
        o = {}
        for i in range(len(chains_order)):
            o[chains_order[i]] = self.resindexes[i]
        self.numb = o

    def isSingleChain(self):
        if self.chain != '' or len(self.sequences.keys()) == 1:
            return True
        else:
            return False

    def containsOnlyCA(self):
        if self.allnumber == self.canumber:
            return True
        else:
            return False

    def getMissing(self):
        return self.isBroken()+len(self.sequences.keys())

    def isBroken(self):
        brk = []
        for j in self.numb.keys():
            indexes = self.numb[j]
            first = indexes[0]
            for i in range(1, len(indexes)):
                if indexes[i] - 1 != first:
                    brk.append(str(first) + "-" + str(indexes[i]))
                first = indexes[i]
        return len(brk)

    def getResIndexes(self):
        t = [str(i) for i in self.numb[self.chain]]
        return ",".join(t)

    def getBody(self):
        return self.onlycalfa

    def savePdbFile(self, outfilename):
        with gzip.open(outfilename, "wb") as fw:
            fw.write(self.onlycalfa)

    def containsChain(self, chain):
        if chain in self.sequences.keys():
            return True

    def getSequence(self):
        if self.chain != '':
            o = ""
            for e in list(self.chain):
                o += self.sequences[e]
            return o
        else:
            out = ""
            for k in self.sequences.keys():
                out += "".join(self.sequences[k])
            return out

if __name__ == "__main__":
    f = open("/home/mjamroz/2iv9.pdb")
    a = PdbParser(f, chain="AB")
    print len(a.getSequence())
    #print a.getBody()
    #t= a.getMissing()
    #print t
