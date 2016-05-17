#!/usr/bin/env python
import MySQLdb
from sys import exit
from os import path

#ALTER TABLE {tableName} ADD COLUMN COLNew {type};
db = MySQLdb.connect(host="localhost", user="cabsdock", passwd="cabsdock123", db="cabsdock")
cur = db.cursor()

def createTables():
    global cur,db
    cur.execute("DROP TABLE IF EXISTS server_load")
    cur.execute("DROP TABLE IF EXISTS excluded")
    cur.execute("DROP TABLE IF EXISTS models_skip")
    cur.execute("DROP TABLE IF EXISTS constraints")
    cur.execute("DROP TABLE IF EXISTS user_queue")
    cur.execute('''CREATE TABLE server_load(`id` integer NOT NULL DEFAULT 0, `status_date` timestamp default CURRENT_TIMESTAMP, `load` integer, `name` varchar(20))''')
#TODO chains/res mapping ? ur.execute("DROP TABLE IF EXISTS
    cur.execute("INSERT INTO server_load(`load`,`name`) VALUES(10,'disco')")
    cur.execute('''
                CREATE TABLE user_queue (
               `id` integer primary key auto_increment not null,
               `jid` varchar(150) NOT NULL,
               `email` varchar(150),
               `ligand_sequence` tinytext NOT NULL,
               `ligand_ss` tinytext,
               `receptor_sequence` text NOT NULL,
               `hide` integer(1) DEFAULT 0,
               `status` enum('pending', 'pre_queue', 'queue', 'running', 'error', 'done')  NOT NULL DEFAULT 'pending',
               `project_name` varchar(250) NOT NULL,
               `ligand_chain` varchar(2) NOT NULL DEFAULT 'A',
               `simulation_length` integer(4) NOT NULL DEFAULT 50,
               `ss_psipred` integer(1) NOT NULL DEFAULT 0,
               `status_date` timestamp NOT NULL DEFAULT current_timestamp,
               `status_init` timestamp NOT NULL DEFAULT current_timestamp,
               `console` text null,
               `constraints_scaling_factor` float not null default 1.0
                ) ''')
    cur.execute('''
                CREATE TABLE excluded
                ( `id` integer primary key auto_increment not null,
                  `jid` varchar(150) NOT NULL,
                  `excluded_region` text,
                  `excluded_region1` text,
                  `excluded_jmol` text
                  ) ''')
    cur.execute('''CREATE TABLE models_skip (`id` integer primary key not null auto_increment, `jid` varchar(150) NOT NULL, prev_jid varchar(150) NOT NULL, model_id varchar(200), removed_model longtext)''')
    cur.execute('''
                CREATE TABLE constraints
                ( `id` integer primary key auto_increment not null,
                  `jid` varchar(150) NOT NULL,
                  `constraint_definition` text,
                  `constraint_definition1` text,
                  `constraint_jmol` text,
                  `force` float not null default 1.0
                  ) ''')
createTables()
