#!/usr/bin/env python
import re
import os
from subprocess import Popen,PIPE


class restrRanges:
    def __init__(self, f):
        self.pdb = f
        uniq_chains = []
        with open(f) as fh:
            for chain in re.findall(r'^ATOM.{9}CA.{6}(\S+).*$', fh.read(), re.M):
                if chain not in uniq_chains:
                    uniq_chains.append(chain)

        self.uniq_chains_i = {}
        for i in range(len(uniq_chains)):
            self.uniq_chains_i[i+1] = uniq_chains[i]

    def parseRanges(self,restr_params=["-max=5.0"]):
        res = {}
        # TODO nie wyciaga wag! 
        # get constraints

        prefix_bin = os.path.join(os.path.dirname(os.path.realpath(__file__)),"bin","restr")
        p = Popen([prefix_bin, "-i="+self.pdb] + restr_params, stdout=PIPE)
        data, err = p.communicate()
        if err:
            print err, "BLAD restr !!!!!!!!!!"

        d = re.findall(r'^(|\s+)(\d+)\s+(\d+)\s+(\d+)\s+(\d+).*$', data,re.M)
        for i in d:
            key = (int(i[1]), int(i[3]))
            if key in res:
                res[key][0].append(int(i[2]))
                res[key][1].append(int(i[4]))
            else:
                res[key] = [ [int(i[2])], [int(i[4])] ]

        self.ranges = {}
        self.ranges1 = {}
        for k in res.keys():
            fc = res[k][0]
            sc = res[k][1]

            min_i = min(fc)
            max_i = max(fc)

            min_j = min(sc)
            max_j = max(sc)
            k2 = (self.uniq_chains_i[k[0]], self.uniq_chains_i[k[1]])
            k21 = (k[0],k[1])
            self.ranges[k2] = [ (min_i, max_i), (min_j, max_j) ]
            self.ranges1[k21] = [ (min_i, max_i), (min_j, max_j) ]
    def getJmolFormat(self):
        o = []
        for k in self.ranges.keys():
            chain_i = k[0]
            chain_j = k[1]
            r_i_n = self.ranges[k][0]
            r_j_n = self.ranges[k][1]
            if chain_i == chain_j and r_i_n[1]>r_j_n[0]:
                o.append("%d - %d:%s" % (r_i_n[0], r_j_n[1], chain_i) )
            else:
                o.append("%d - %d:%s, %d - %d:%s" % (r_i_n[0], r_i_n[1], 
                        chain_i, r_j_n[0], r_j_n[1], chain_j) )
        return o
    def getLabelFormatChains1(self):
        '''
            Restraint ranges, numbering as in CABS: chain 1....n
        '''
        o = []

        for k in self.ranges1.keys():
            chain_i = k[0]
            chain_j = k[1]
            r_i_n = self.ranges1[k][0]
            r_j_n = self.ranges1[k][1]
            if chain_i == chain_j and r_i_n[1]>r_j_n[0]:
                o.append("%d:%s - %d:%s" % (r_i_n[0], chain_i, r_j_n[1], chain_i))
            else:
                o.append("%d:%s - %d:%s, %d:%s - %d:%s" % (r_i_n[0], chain_i, r_i_n[1], 
                        chain_i, r_j_n[0], chain_j, r_j_n[1], chain_j))
        return o

    def getLabelFormat(self):
        '''
            Restraint ranges, chain numbering as original PDB ( A, B, ...)
        '''
        o = []
        for k in self.ranges.keys():
            chain_i = k[0]
            chain_j = k[1]
            r_i_n = self.ranges[k][0]
            r_j_n = self.ranges[k][1]
            if chain_i == chain_j and r_i_n[1]>r_j_n[0]:
                o.append("%d:%s - %d:%s" % (r_i_n[0], chain_i, r_j_n[1], chain_i))
            else:
                o.append("%d:%s - %d:%s, %d:%s - %d:%s" % (r_i_n[0], chain_i, r_i_n[1], 
                        chain_i, r_j_n[0], chain_j, r_j_n[1], chain_j))
        return o
if __name__ == '__main__':
    t = restrRanges("/home/nme/input.pdb")
    t.parseRanges([])
    print "do bazy"
    print t.getLabelFormat()
    print "jmol"
    print t.getJmolFormat()
    print "co jezsd"
    print t.getLabelFormatChains1()


