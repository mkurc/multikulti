#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright Michal Jamroz, 2014, jamroz@chem.uw.edu.pl

from supelek import app
from flask import render_template, g, url_for, request, jsonify, flash, \
    session, Response, redirect, send_from_directory
from flask.ext.uploads import UploadSet, configure_uploads, \
    UploadNotAllowed, patch_request_class
from config import config, \
    connect_user_db,query_user_db,get_user_db,send_mail,query_db,update_keywords_table
                                    # config file plus few db helper tools
from werkzeug import secure_filename

import os
import bz2
import uuid
import json
import re
import gzip
import sqlite3
from shutil import move, copyfileobj, rmtree,copy
from subprocess import PIPE,Popen

from os import path

app.secret_key = \
    'sialababamakniewiedzialajakaadziadwiedzialniepowiedzialitobylotak'

trajectories = UploadSet('trajectories', extensions=('pdb', 'bz2','gro','xtc','xyz'))
clientdata = UploadSet('clientdata',extensions=('bz2'))
configure_uploads(app,clientdata)
configure_uploads(app, trajectories)
patch_request_class(app, app.config['MAX_CONTENT_LENGTH'])

def bzip_file(filename):
    with open(filename,'rb') as input:
        fo = filename+".bz2"
        with bz2.BZ2File(fo,"wb",compresslevel=9) as output:
            copyfileobj(input,output)
    os.unlink(filename)        

def arraytostring(ar):
    i = []
    for e in ar:
        i.append("%d-%d"%(e))
    return ", ".join(i)

@app.route('/clientIP')
def client_ip():
    ip = request.remote_addr
    resu = "NO"
    if ip in app.config['REMOTE_PDBPARSER_SERVER_IP']:
        resu = "YES"
    return Response(resu+" "+ip, mimetype="text/plain")    

@app.route('/_deleteOldJobs')
def delete_old():
    days="-"+str(app.config['DELETE_USER_JOBS_AFTER'])
    for keyid in query_user_db("SELECT key FROM user_jobs WHERE date<=date('now',?) AND ip!='exampleIP'",[days]):
        pat_k = path.join(app.config['USERJOB_DIRECTORY'],keyid[0])
        rmtree(pat_k)
    query_user_db("DELETE FROM knots_info where key in (select key FROM user_jobs \
            WHERE date<=date('now',?) AND ip!='exampleIP')",[days],insert=True)
    query_user_db("DELETE FROM user_jobs WHERE date<=date('now',?) AND ip!='exampleIP'",[days],insert=True)
    return Response("HEIL ERIS!",mimetype='text/plain')

def checkUserIPAndDate(ip):
    # select count(*) from user_jobs where datetime(date,'+48 hour')<datetime('now')
    q = query_user_db("SELECT COUNT(*) FROM user_jobs WHERE ip=? AND date>DATETIME('now',?)",[ip,app.config['WAIT_BEFORE_SUBMIT']],one=True)
    if int(q[0])==0: # if there is no records 
        return True
    else:
        return False

@app.route('/_queue')
def index_queue():
    q = query_user_db("SELECT key FROM user_jobs WHERE status=0")
    d = ""
    for i in q:
        d += str(i[0]) + "\n"
    return Response(d,mimetype='text/plain')    

@app.route('/_server_talking/<secret_key>/<jid>/<task>/',methods=['POST','GET'])
def parse_server_talking(task,secret_key,jid):
    
    k = app.config['REMOTE_SERVER_SECRET_KEY'] 
    # must be known by comp. server. It is not very secure, but connection between server and site should be mostly on local net.
    if k==secret_key and request.remote_addr in app.config['REMOTE_PDBPARSER_SERVER_IP']: # added "firewall" (he he) for selected IP only
        # status commander
        if   task=='S_P': # pending
             query_user_db("UPDATE user_jobs set status=1, comp_date=DATETIME()\
                     WHERE key=?",[jid],insert=True)
        elif task=='S_R': # running
             query_user_db("UPDATE user_jobs set status=2, comp_date=DATETIME()\
                     WHERE key=?",[jid],insert=True)
        elif task=='S_D': # done
             query_user_db("UPDATE user_jobs set status=3, comp_date=DATETIME()\
                     WHERE key=?",[jid],insert=True)
             user_mail = query_user_db("SELECT email FROM user_jobs WHERE key=?",\
                     [jid],one=True)[0]
             user_pname = query_user_db("SELECT name FROM user_jobs WHERE key=?",\
                     [jid],one=True)[0]
             if "@" in user_mail:
                 send_mail(to=user_mail,subject="DONE ("+jid+", "+user_pname+")",body="Check results here: \
                         \n" + url_for('index_computing', jobid=jid,_external=True)) 
        elif task=='S_E': # error
             query_user_db("UPDATE user_jobs set status=4, comp_date=DATETIME()\
                     WHERE key=?",[jid],insert=True)
             send_mail(subject="ERROR comp for job "+jid,body=\
                     "Ooops...\n"+url_for('index_computing',jobid=jid,_external=True))
             user_mail = query_user_db("SELECT email FROM user_jobs WHERE key=?",\
                     [jid],one=True)[0]
             if "@" in user_mail:
                 user_pname = query_user_db("SELECT name FROM user_jobs WHERE key=?",\
                         [jid],one=True)[0]
                 send_mail(to=user_mail,subject="ERROR ("+jid+", "+user_pname+")",body="Sorry, \
                         some problems with your job:\n" + url_for('index_computing', jobid=jid,_external=True)) 
        elif task=='S_W': # waiting
             query_user_db("UPDATE user_jobs set status=0, comp_date=DATETIME() WHERE key=?",[jid],insert=True)

        # ping pong command
        elif task=="PING": # ping, server alive!. Creates file (updating modification time)
            pingfile = os.path.join(os.path.dirname(os.path.abspath(__file__)),"ping_check.lck")
            if not os.path.exists(pingfile):
                open(pingfile,'w').close()
            os.utime(pingfile,None)        
        elif task=="PINGPDB": # ping, server for pdb database parsing alive!. Creates file (updating modification time)
            pingfile = os.path.join(os.path.dirname(os.path.abspath(__file__)),"ping_pdbparser_check.lck")
            if not os.path.exists(pingfile):
                open(pingfile,'w').close()
            os.utime(pingfile,None) 
        elif task=="MSG":
            message = request.form['message']
            send_mail(subject="MSG from PDBparser",body=message)
        elif task=="S_TOUT":
            t = query_user_db("UPDATE user_jobs SET results_type=3 WHERE key=?",[jid],insert=True)
        elif task=="UPD":
            values = request.form['values']
            table = request.form['table']
            if table=="user_jobs":
                t = query_user_db("UPDATE user_jobs SET results_type=? WHERE key=?",[values,jid],insert=True)
            elif table=="knots_info":    
                t = "INSERT INTO knots_info(key, knot_types, knots_range, knot_tails, sknot_tails, \
                        sknot_loops, sknot_if) VALUES ('"+values+"')" 
                # TODO MUST BE UNSECURE!
                t2 = query_user_db(t,[],insert=True)
        elif task=="INFO":
            t = query_user_db("SELECT chain_index,closing,start_idx,stop_idx FROM user_jobs WHERE key=?",[jid])[0]
            out = {}
            dest_directory = os.path.join(app.config['USERJOB_DIRECTORY'],jid)
            if os.path.exists(os.path.join(dest_directory,"input.pdb.bz2")):
                out['format'] = 'pdb'
            elif os.path.exists(os.path.join(dest_directory,"input.xyz.bz2")):
                out['format'] = 'xyz'

            for k in t.keys():
                if t[k]!='':
                    out[k] = t[k]
                else:
                    out[k] = 'NONE'
            return Response(json.dumps(out),mimetype='application/json')


        elif task=="SEND" and request.method=='POST':
            # file arrived as bzip compressed
            data = request.files['file']
            #create results directory
            resdir = os.path.join(app.config['USERJOB_DIRECTORY'],jid,"results")
            if not os.path.exists(resdir):
                os.mkdir(resdir)
            # save data in temp upload folder
            clientdata.save(request.files['file']) # TODO may be insecure
            # unzip
            saved_file = clientdata.path(request.files['file' ].filename)
            outpath = os.path.join(resdir,request.files['file'].filename[:-4]) # -4 since .bz2 extension
            with bz2.BZ2File(saved_file, 'rb') as contentfile:
                content = contentfile.read()
                with open(outpath,'wb') as fw:
                    fw.write(content)
            # remove temp file
            os.remove(saved_file)
        elif task=="NOKNOT" and request.method=='POST':
            pdbcode = request.form['pdbcode']
            chain = request.form['chain']
            print " NO KNOT IN: "+pdbcode+" "+chain
            query_db("INSERT INTO unknotted(pdbcode,chain) VALUES (?,?)",[pdbcode,chain],insert=True)

        elif task=="SENDKNOT" and request.method=='POST':

            # file arrived as bzip compressed
            data = request.files['file']
            cutoff_set = request.form['cutoff']
            filename = data.filename
            prefix = filename.split(".")[0]
            prefix = prefix.split("_")
            pdb, chain = prefix[1],prefix[2]
            #create results directory
            #filename in format knotmap_2etl_A.txt
            resdir = os.path.join(app.config['KNOTSTATIC_DIRECTORY'],pdb,chain)
            if not os.path.exists(resdir):
                os.makedirs(resdir)
            # save data in temp upload folder
            clientdata.save(request.files['file']) # TODO may be insecure
            clientdata.save(request.files['filepdb'])
            # unzip
            saved_file = clientdata.path(request.files['file'].filename)
            outpath = os.path.join(resdir,request.files['file'].filename[:-4]) # -4 since .bz2 extension
            outpath_map = outpath
            with bz2.BZ2File(saved_file, 'rb') as contentfile:
                content = contentfile.read()
                with open(outpath,'wb') as fw:
                    fw.write(content)
            # remove temp file
            os.remove(saved_file)

            # save native structure
            saved_file = clientdata.path(request.files['filepdb'].filename)
            outpath = os.path.join(resdir,request.files['filepdb'].filename[:-4]+".gz") # -4 since .bz2 extension
            with bz2.BZ2File(saved_file, 'rb') as contentfile:
                content = contentfile.read()
                with gzip.open(outpath,'wb') as fw:
                    fw.write(content)
            # remove temp file
            os.remove(saved_file)

            # add info to DB
            putChainIntoDatabase(outpath_map,resdir,cutoff_set)
    else:
        send_mail(subject="Access violation",body="(Attacker) host IP: "+request.remote_addr)

    return Response("HEIL ERIS!",mimetype='text/plain')

#@app.route('/_getinput/<key>/input.pdb.bz2')
#def get_input_chain(key):
#    filename = os.path.join(app.config['USERJOB_DIRECTORY'],key,"input.pdb.bz2")
#    with  open(filename,"rb") as content:
#        data = content.read()
#        return Response(data,mimetype='application/x-bzip2') 
