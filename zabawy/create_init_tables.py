#!/usr/bin/env python
import sqlite3
from sys import exit
from os import path

#ALTER TABLE {tableName} ADD COLUMN COLNew {type};
if not path.exists("database-full.db"):
    db = sqlite3.connect("database-full.db")
    cur = db.cursor()
else:
    print "Remove database-full.db before"
    exit(1)

def createTables():
    global cur,db
    cur.execute("DROP TABLE IF EXISTS server_load")
    cur.execute('''CREATE TABLE server_load(id NOT NULL DEFAULT 0, \
            status_date integer(4) NOT NULL DEFAULT \
            (strftime('%s', 'now')), load integer, name text)''')
#TODO chains/res mapping ? ur.execute("DROP TABLE IF EXISTS 
    cur.execute("INSERT INTO server_load(load,name) VALUES(10,'disco')")
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
                status text check(status IN ('pending', 'pre_queue', 'queue', 'running', 'error', 'done') )  NOT NULL DEFAULT 'pending',
                project_name text NOT NULL,
                ligand_chain text NOT NULL DEFAULT 'A',
                simulation_length integer(4) NOT NULL DEFAULT 50,
                ss_psipred integer(1) NOT NULL DEFAULT 0,
                status_date integer(4) NOT NULL DEFAULT (strftime('%s', 'now')),
                status_init integer(4) NOT NULL DEFAULT (strftime('%s', 'now')), 
                constraints_scaling_factor not null default 1.0
                ) ''')
    cur.execute("DROP TABLE IF EXISTS excluded")
    cur.execute('''
                CREATE TABLE excluded
                ( id integer primary key,
                  jid text NOT NULL,
                  excluded_region text,
                  excluded_region1 text,
                  excluded_jmol text,
                  foreign key(jid) REFERENCES user_queue(jid)
                  ) ''')
# chyba ten definition1 zbedny, bo i tak user bedzie podawal wzgledem pdb
    cur.execute("DROP TABLE IF EXISTS constraints")
    cur.execute('''
                CREATE TABLE constraints
                ( id integer primary key,
                  jid text NOT NULL,
                  constraint_definition text,
                  constraint_definition1 text,
                  constraint_jmol text,
                  force float not null default 1.0,
                  foreign key(jid) REFERENCES user_queue(jid)
                  ) ''')
createTables()
