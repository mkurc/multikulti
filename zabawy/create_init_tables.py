#!/usr/bin/env python
from random import randint
from collections import Counter
from glob import glob
import sqlite3
from os import path,makedirs
from glob import glob
from shutil import copytree
from sys import exit
#ALTER TABLE {tableName} ADD COLUMN COLNew {type};
if not path.exists("database-full.db"):
    db = sqlite3.connect("database-full.db")
    cur = db.cursor()
else:
    print "Remove database-full.db before"
    exit(1)

def createTables():
    global cur,db

    cur.execute("DROP TABLE IF EXISTS user_queue")
    cur.execute('''
                CREATE TABLE user_queue ( 
                id integer primary key autoincrement,   
                jid text NOT NULL, 
                email text,
                ligand_sequence text NOT NULL, 
                ligand_ss text, 
                receptor_sequence text NOT NULL, 
                hide integer(1) DEFAULT 0,
                status text check(status IN ('pending', 'queue', 'running', 'error') )  NOT NULL DEFAULT 'pending',
                project_name text NOT NULL,
                status_date integer(4) NOT NULL DEFAULT (strftime('%s', 'now')),
                numbering_receptor integer DEFAULT 1,
                numbering_ligand integer DEFAULT 1
                ) ''')

    cur.execute("DROP TABLE IF EXISTS constraints")
    cur.execute('''
                CREATE TABLE constraints
                ( id integer primary key,   
                  jid text NOT NULL,
                  res_i integer not null,
                  res_i_chain text,
                  res_j integer not null,
                  res_j_chain text,
                  res_i_type text,
                  res_j_type text,
                  distance float not null,
                  force float not null default 1.0,
                  foreign key(jid) REFERENCES user_queue(jid)
                  )
    ''')
createTables()
