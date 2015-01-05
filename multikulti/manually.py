#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Michal Jamroz 2014/09

import os
from config import config, unique_id, gunzip
import sqlite3

from multikulti_modules.parsePDB import PdbParser
from multikulti_modules.restrRanges import restrRanges
###############################################################################


def query_db(query, args=(), one=False, insert=False):
    rv = sqlite3.connect(config['DATABASE'])
    rv.row_factory = sqlite3.Row
    mydb = rv
    cur = mydb.execute(query, args)
    if insert:
        rv.commit()
        cur.close()
        return cur.lastrowid
    else:
        rv = cur.fetchall()
        cur.close()
        return ((rv[0] if rv else None) if one else rv)


def add_init_data_to_db(ligand_seq, ligand_ss, name, receptor_fh):

    jid = unique_id()
    hide = 0

    # save receptor structure
    dest_directory = os.path.join(config['USERJOB_DIRECTORY'], jid)
    dest_file = os.path.join(dest_directory, "input.pdb.gz")
    os.mkdir(dest_directory)

    p = PdbParser(receptor_fh)
    receptor_seq = p.getSequence()
    p.savePdbFile(dest_file)
    gunzip(dest_file)

    query_db("INSERT INTO user_queue(status, jid, receptor_sequence, ligand_sequence, ligand_ss, hide, project_name) VALUES(?,?,?,?,?,?,?)", ['pre_queue', jid, receptor_seq, ligand_seq, ligand_ss, hide, name], insert=True)

    # generate constraints
    unzpinp = os.path.join(config['USERJOB_DIRECTORY'], jid, "input.pdb")
    r = restrRanges(unzpinp)
    r.parseRanges()
    for e, e1, e2 in zip(r.getLabelFormat(), r.getLabelFormatChains1(), r.getJmolFormat()):
        query_db("INSERT INTO constraints(jid,constraint_definition, constraint_definition1,constraint_jmol) VALUES(?,?,?,?)", [jid, e, e1, e2], insert=True)

    return True


with open("2pcy.pdb", "r") as fh:
    seq = "AAAAA"
    ss = "CCCCC"
    name = "test job"
    add_init_data_to_db(seq, ss, name, fh)
