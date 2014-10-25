#!/usr/bin/env python
import sqlite3
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
                status text check(status IN ('pending', 'pre_queue', 'queue', 'running', 'error') )  NOT NULL DEFAULT 'pending',
                project_name text NOT NULL,
                status_date integer(4) NOT NULL DEFAULT (strftime('%s', 'now')),
                status_init integer(4) NOT NULL DEFAULT (strftime('%s', 'now')),
                constraints_scaling_factor not null default 1.0
                ) ''')

    cur.execute("DROP TABLE IF EXISTS constraints")
    cur.execute('''
                CREATE TABLE constraints
                ( id integer primary key,   
                  jid text NOT NULL,
                  constraint_definition text,
                  force float not null default 1.0,
                  foreign key(jid) REFERENCES user_queue(jid)
                  ) ''')
createTables()
