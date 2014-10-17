#!/usr/bin/env python
import urllib2
from lxml import etree,objectify
from StringIO import StringIO
import gzip
from sys import argv
import re
from itertools import count,groupby
from sys import exit

def convertToRanges(L):
    G=(list(x) for _,x in groupby(L, lambda x,c=count(): next(c)-x))
    return ["-".join(map(str,(g[0],g[-1])[:len(g)])) for g in G]

def findxmlprefix(data):
    ''' GUPI XPATH!!!!! '''
    for r in re.finditer(r'xmlns:PDBx="(.*)"',data):
        if r:
            return r.group(1)
class getCoordinates:
    def __init__(self,pdbcode,localfile=False):
        self.pdb = pdbcode
	data = ""

        if not localfile:
            buraki = urllib2.urlopen('http://www.rcsb.org/pdb/files/'+self.pdb+'.xml.gz')
            b2 = buraki.read()
            ft = StringIO(b2)
            f = gzip.GzipFile(fileobj=ft,mode="rb")
            data = f.read()
            f.close()
            buraki.close()
        else:
            f = gzip.GzipFile(localfile,"rb")
            data = f.read()
            f.close()

        self.NS = {"PDBx":''+findxmlprefix(data)+''}
        self.root = etree.fromstring(data)
        print "linijek w xmlu", len(data)
        l = self.root.xpath("//PDBx:atom_siteCategory/PDBx:atom_site[PDBx:auth_atom_id='CA'][PDBx:pdbx_PDB_model_num='1' or PDBx:pdbx_PDB_model_num='0'][PDBx:group_PDB='ATOM']/PDBx:auth_asym_id",namespaces=self.NS) # TODO moze byc zle - dodalem model_num=0 jako or. mozliwe ze wyciagnie dwa na raz
        self.chains = set()
	for e in l:
	   if e is not None:
	      self.chains.update(e.text)
        #self.chains.update(e.text for e in l)
    def getChainIndexes(self):
        return self.chains
    def getCalfa(self,chain,output=''):
        l = self.root.xpath("//PDBx:atom_siteCategory/PDBx:atom_site[not(PDBx:label_alt_id/text()) or PDBx:label_alt_id='A'][PDBx:auth_atom_id='CA'][PDBx:pdbx_PDB_model_num='1' or PDBx:pdbx_PDB_model_num='0'][PDBx:group_PDB='ATOM' or (PDBx:group_PDB='HETATM' and PDBx:label_comp_id='MSE') or (PDBx:group_PDB='HETATM' and PDBx:label_comp_id='ORN') or (PDBx:group_PDB='HETATM' and PDBx:label_comp_id='PCA') or (PDBx:group_PDB='HETATM' and PDBx:label_comp_id='DGL')][PDBx:auth_asym_id='"+chain+"']",namespaces=self.NS) # TODO moze byc zle - dodalem model_num=0 jako or. mozliwe ze wyciagnie dwa na raz
# mozna by pewnie zrobic inaczej or hetatom and (xxx or xxx or xxx ....)
        o = ''
        #r = []
        prev_seqid=999999999999999
        first_resid = -1
        for e in l:
            d = e.find("PDBx:label_seq_id",namespaces=self.NS)
            if d is not None and d.text:
                first_resid = int(d.text)
                break
        prev_seqid = first_resid-9999999999999     
        for e in l:
            x = e.find("PDBx:Cartn_x",namespaces=self.NS)
            y = e.find("PDBx:Cartn_y",namespaces=self.NS)
            z = e.find("PDBx:Cartn_z",namespaces=self.NS)
            seqid = e.find("PDBx:label_seq_id",namespaces=self.NS)
            if (seqid is None) or (seqid.text is None): # or not seqid.text:
                continue
            if int(seqid.text)==prev_seqid:
                prev_seqid = int(seqid.text)
                continue
	    prev_seqid = int(seqid.text)
            l = [seqid,x,y,z]
            if None not in l:
                o+= "%4d %8.3f %8.3f %8.3f\n"% (int(l[0].text)-first_resid+1, float(l[1].text), float(l[2].text), float(l[3].text) )
        if output !='':
            f = open(output,"w")
            f.write(o)
            f.close()
        else:
            return o

    def getCalfaPdbFormat(self,chain,output=''):
        l = self.root.xpath("//PDBx:atom_siteCategory/PDBx:atom_site[not(PDBx:label_alt_id/text()) or PDBx:label_alt_id='A'][PDBx:auth_atom_id='CA'][PDBx:pdbx_PDB_model_num='1' or PDBx:pdbx_PDB_model_num='0'][PDBx:group_PDB='ATOM' or (PDBx:group_PDB='HETATM' and PDBx:label_comp_id='MSE') or (PDBx:group_PDB='HETATM' and PDBx:label_comp_id='ORN') or (PDBx:group_PDB='HETATM' and PDBx:label_comp_id='PCA') or (PDBx:group_PDB='HETATM' and PDBx:label_comp_id='DGL')][PDBx:auth_asym_id='"+chain+"']",namespaces=self.NS) # TODO moze byc zle - dodalem model_num=0 jako or. mozliwe ze wyciagnie dwa na raz
        o = ''
        r = []
        prev_seqid=999999999999999
        first_resid = -1
        for e in l:
            d = e.find("PDBx:label_seq_id",namespaces=self.NS)
            if d.text:
                first_resid = int(d.text)
                break
        prev_seqid = first_resid-9999999999999     
                
        for e in l:
            x = e.find("PDBx:Cartn_x",namespaces=self.NS)
            y = e.find("PDBx:Cartn_y",namespaces=self.NS)
            z = e.find("PDBx:Cartn_z",namespaces=self.NS)
            seqname = e.find("PDBx:label_comp_id",namespaces=self.NS)
            seqid = e.find("PDBx:label_seq_id",namespaces=self.NS)
            if not seqid.text:
                continue
            if int(seqid.text)==prev_seqid:
                prev_seqid = int(seqid.text)
                continue
            prev_seqid = int(seqid.text)
            bfactor = e.find("PDBx:B_iso_or_equiv",namespaces=self.NS) 
            l = (seqid,seqname,chain,seqid,x,y,z,bfactor)
            if None not in l:
                l = (int(seqid.text)-first_resid+1,str(seqname.text),str(chain),int(seqid.text)-first_resid+1,float(x.text),float(y.text),float(z.text),float(bfactor.text)) # chyba przenumerowanie
                o+= "ATOM%7d  CA%5s%2s%4d%12.3f%8.3f%8.3f  1.00%6.2f           C\n"%l
        if output !='':
            f = open(output,"w")
            f.write(o)
            f.close()
        else:
            return o





class fetchPDBinfo:
    def __init__(self,pdbcode,chain='A',localfile=False):
        self.pdb = pdbcode
        self.chain = chain
        if not localfile:
            ft = StringIO(urllib2.urlopen('http://www.rcsb.org/pdb/files/'+self.pdb+'.xml.gz').read())
            f = gzip.GzipFile(fileobj=ft,mode="rb")
        else:
            f = gzip.GzipFile(localfile,"rb")
        data = f.read()
        f.close()
        self.NS = {"PDBx":''+findxmlprefix(data)+''}
        self.root = etree.fromstring(data)
        self.codification = { "ALA" : 'A',
                 "CYS" : 'C',
                 "ASP" : 'D',
                 "GLU" : 'E',
                 "PHE" : 'F',
                 "GLY" : 'G',
                 "HIS" : 'H',
                 "ILE" : 'I',
                 "LYS" : 'K',
                 "LEU" : 'L',
                 "MET" : 'M',
                 "MSE" : 'M',
                 "ASN" : 'N',
                 "PYL" : 'O',
                 "PRO" : 'P',
                 "GLN" : 'Q',
                 "ARG" : 'R',
                 "SER" : 'S',
                 "THR" : 'T',
                 "SEC" : 'U',
                 "VAL" : 'V',
                 "TRP" : 'W',
                 "5HP" : 'E',
                 "ABA" : 'A',
                 "AIB" : 'A',
                 "BMT" : 'T',
                 "CEA" : 'C',
                 "CGU" : 'E',
                 "CME" : 'C',
                 "CRO" : 'X',
                 "CSD" : 'C',
                 "CSO" : 'C',
                 "CSS" : 'C',
                 "CSW" : 'C',
                 "CSX" : 'C',
                 "CXM" : 'M',
                 "DAL" : 'A',
                 "DAR" : 'R',
                 "DCY" : 'C',
                 "DGL" : 'E',
                 "DGN" : 'Q',
                 "DHI" : 'H',
                 "DIL" : 'I',
                 "DIV" : 'V',
                 "DLE" : 'L',
                 "DLY" : 'K',
                 "DPN" : 'F',
                 "DPR" : 'P',
                 "DSG" : 'N',
                 "DSN" : 'S',
                 "DSP" : 'D',
                 "DTH" : 'T',
                 "DTR" : 'X',
                 "DTY" : 'Y',
                 "DVA" : 'V',
                 "FME" : 'M',
                 "HYP" : 'P',
                 "KCX" : 'K',
                 "LLP" : 'K',
                 "MLE" : 'L',
                 "MVA" : 'V',
                 "NLE" : 'L',
                 "OCS" : 'C',
                 "ORN" : 'A',
                 "PCA" : 'E',
                 "PTR" : 'Y',
                 "SAR" : 'G',
                 "SEP" : 'S',
                 "STY" : 'Y',
                 "TPO" : 'T',
                 "TPQ" : 'F',
                 "TYS" : 'Y',
                 "TYR" : 'Y' }
        self._getCAmissing()
        l = self.root.xpath("//PDBx:atom_siteCategory/PDBx:atom_site[PDBx:auth_atom_id='CA'][PDBx:pdbx_PDB_model_num='1' or PDBx:pdbx_PDB_model_num='0'][PDBx:group_PDB='ATOM']/PDBx:auth_asym_id",namespaces=self.NS) # TODO moze byc zle - dodalem model_num=0 jako or. mozliwe ze wyciagnie dwa na raz
        self.chains = set()
        self.firstchain = ""
	for e in l:
	   if e is not None:
	      self.chains.update(e.text)
              if self.firstchain == "":
                  self.firstchain = e.text
        #self.chains.update(e.text for e in l)
    def getFirstChain(self):
        return self.firstchain
    def getChainIndexes(self):
        return self.chains
    def getCalfaBreaks(self):
        l = self.root.xpath("//PDBx:atom_siteCategory/PDBx:atom_site[not(PDBx:label_alt_id/text()) or PDBx:label_alt_id='A'][PDBx:auth_atom_id='CA'][PDBx:pdbx_PDB_model_num='1' or PDBx:pdbx_PDB_model_num='0'][PDBx:group_PDB='ATOM' or (PDBx:group_PDB='HETATM' and PDBx:label_comp_id='MSE') or (PDBx:group_PDB='HETATM' and PDBx:label_comp_id='ORN') or (PDBx:group_PDB='HETATM' and PDBx:label_comp_id='PCA') or (PDBx:group_PDB='HETATM' and PDBx:label_comp_id='DGL')][PDBx:auth_asym_id='"+self.chain+"']",namespaces=self.NS) # TODO moze byc zle - dodalem model_num=0 jako or. mozliwe ze wyciagnie dwa na raz
# mozna by pewnie zrobic inaczej or hetatom and (xxx or xxx or xxx ....)
        o = []
        #r = []
        prev_seqid=999999999999999
        first_resid = -1
        for e in l:
            d = e.find("PDBx:label_seq_id",namespaces=self.NS)
            if d.text:
                first_resid = int(d.text)
                break
        prev_seqid = first_resid-9999999999999     
        for e in l:
            x = e.find("PDBx:Cartn_x",namespaces=self.NS)
            y = e.find("PDBx:Cartn_y",namespaces=self.NS)
            z = e.find("PDBx:Cartn_z",namespaces=self.NS)
            seqid = e.find("PDBx:label_seq_id",namespaces=self.NS)
            if not seqid.text:
                continue
            if int(seqid.text)==prev_seqid:
                prev_seqid = int(seqid.text)
                continue
            prev_seqid = int(seqid.text)
            l = [seqid,x,y,z]
            if None not in l:
                o.append( (int(l[0].text)-first_resid+1, float(l[1].text), float(l[2].text), float(l[3].text) ) )
        # check chain breaks
        eps = 4.2*4.2
        brk = []
        for i in range(1,len(o)):
            i1 = o[i-1][0]
            i2 = o[i][0]
            x1 = o[i-1][1]
            y1 = o[i-1][2]
            z1 = o[i-1][3]

            x2 = o[i][1]
            y2 = o[i][2]
            z2 = o[i][3]
    
            d = (x1-x2)**2  + (y2-y1)**2 + (z1-z2)**2
            if d>eps:
                brk.append(i1)
                brk.append(i2)
        return brk
    def getFirstResidueIndex(self):
        return 1
    def getSeqOneLetterCode(self):
        l = self.root.xpath("//PDBx:atom_siteCategory/PDBx:atom_site[PDBx:auth_atom_id='CA'][PDBx:auth_asym_id='"+self.chain+"'][PDBx:pdbx_PDB_model_num='1' or PDBx:pdbx_PDB_model_num='0'][PDBx:group_PDB='ATOM' or (PDBx:group_PDB='HETATM' and PDBx:label_comp_id='MSE') or (PDBx:group_PDB='HETATM' and PDBx:label_comp_id='ORN') or (PDBx:group_PDB='HETATM' and PDBx:label_comp_id='PCA') or (PDBx:group_PDB='HETATM' and PDBx:label_comp_id='DGL')][not(PDBx:label_alt_id/text()) or PDBx:label_alt_id='A']/PDBx:label_comp_id",namespaces=self.NS) # TODO moze byc zle - dodalem model_num=0 jako or. mozliwe ze wyciagnie dwa na raz
        k = self.codification.keys()
        seq = ""
        for e in l:
            s = e.text
            if s in k:
                seq += self.codification[s]
            else:
                seq += "X"
        return seq
    def getMissingArray(self):
        return self.missing_array
    def _getCAmissing(self):
        seq=[]
        l = self.root.xpath("//PDBx:atom_siteCategory/PDBx:atom_site[PDBx:auth_atom_id='CA'][PDBx:auth_asym_id='"+self.chain+"'][PDBx:pdbx_PDB_model_num='1' or PDBx:pdbx_PDB_model_num='0'][PDBx:group_PDB='ATOM' or (PDBx:group_PDB='HETATM' and PDBx:label_comp_id='MSE') or (PDBx:group_PDB='HETATM' and PDBx:label_comp_id='ORN') or (PDBx:group_PDB='HETATM' and PDBx:label_comp_id='PCA') or (PDBx:group_PDB='HETATM' and PDBx:label_comp_id='DGL')][not(PDBx:label_alt_id/text()) or PDBx:label_alt_id='A']/PDBx:label_seq_id",namespaces=self.NS) # TODO moze byc zle - dodalem model_num=0 jako or. mozliwe ze wyciagnie dwa na raz
        for e in l:
            if e.text: seq.append(int(e.text))
        first = seq[0]    
        for e in range(len(seq)):
            seq[e] = seq[e] - first + 1 # przenumerowanie od 1 z zachowaniem przerw
        
        self.crystlen = len(seq)
        if len(seq)>0:
            self.missing = [x for x in range(seq[0],seq[-1]+1) if x not in seq]
            self.missing_array = self.missing
            self.missing = convertToRanges(self.missing)
            self.seq_idx = seq
            self.seq_len = seq[-1]
        else:
            self.missing=[]
    def getSeqLength(self):
        return self.seq_len
    def getPdbCreationDate(self):
        self.date = self.root.xpath("//PDBx:database_PDB_revCategory/PDBx:database_PDB_rev/PDBx:date_original",namespaces=self.NS)[0].text
        try:
            return self.date
        except:
            return None
    def getCAlen(self):
        return self.crystlen
    def getMissing(self):
        return self.missing


    def getPubtitlePubmed(self):
        pubmed = self.root.xpath("//PDBx:citationCategory/PDBx:citation[1]/PDBx:pdbx_database_id_PubMed",namespaces=self.NS)
        doi = self.root.xpath("//PDBx:citationCategory/PDBx:citation[1]/PDBx:pdbx_database_id_DOI",namespaces=self.NS)
        title = self.root.xpath("//PDBx:citationCategory/PDBx:citation[1]/PDBx:title",namespaces=self.NS)
        desc = self.root.xpath("//PDBx:structCategory/PDBx:struct/PDBx:title",namespaces=self.NS)
        src = self.root.xpath("//PDBx:entity_src_genCategory/PDBx:entity_src_gen/PDBx:pdbx_gene_src_scientific_name",namespaces=self.NS)
        key = self.root.xpath("//PDBx:struct_keywordsCategory/PDBx:struct_keywords/PDBx:pdbx_keywords",namespaces=self.NS)
        molecutag = self.root.xpath("//PDBx:entityCategory/PDBx:entity/PDBx:pdbx_description",namespaces=self.NS)

        doi = doi[0].text if doi else None
        molecutag = molecutag[0].text if molecutag else None
        key = key[0].text.capitalize() if key else None
        src = src[0].text if src else None
        pubmed = pubmed[0].text if pubmed else None
        title = title[0].text if title else None
        desc = desc[0].text.capitalize() if desc else None
        
        return (doi,pubmed,desc,title,src,key,molecutag)

if __name__ == "__main__":
    with open("unknottedexists.txt") as f:
        for i in f.readlines():

            pdb=i.split(".")[0]
            chain = i.split(".")[1].strip()#.upper()
            fi = pdb+".xml.gz"
            pdb = pdb.upper()
            print pdb,chain,fi

            a = getCoordinates(pdb,localfile=fi)
            _ =  a.getCalfa(chain,output=pdb+"_"+chain+".xyz")

