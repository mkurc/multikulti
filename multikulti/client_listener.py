#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright Michal Jamroz, 2014, jamroz@chem.uw.edu.pl

from multikulti import app
from config import config, query_db
from flask import g, url_for, request, jsonify, Response, redirect, send_from_directory

import json

@app.route('/_queue')
def index_queue():
    q = query_db("SELECT jid FROM user_queue WHERE status='pre_queue'")
    d = ""
    for i in q:
        d += str(i[0]) + "\n"
    return Response(d,mimetype='text/plain')
@app.route('/_deleteOldJobs')
def delete_old():
    days="-"+str(app.config['DELETE_USER_JOBS_AFTER'])
    to_delete = []
# TODO sprawdzic, czy to dziala
    for keyid in query_db("SELECT jid FROM user_queue WHERE \
            status_init<=date('now',?)",[days]):
        to_delete.append(keyid[0])
        pat_k = path.join(app.config['USERJOB_DIRECTORY'],keyid[0])
        rmtree(pat_k)
    for k in to_delete:
        query_db("DELETE FROM constraints WHERE jid=?",[k],insert=True)
    query_db("DELETE FROM user_queue where jid in (select jid FROM \
            user_queue WHERE status_init<=date('now',?))",[days],insert=True)

    return Response("HEIL ERIS!",mimetype='text/plain')

@app.route('/_server_talking/<secret_key>/<jid>/<task>/',methods=['POST','GET'])
def parse_server_talking(task,secret_key,jid):
    k = config['REMOTE_SERVER_SECRET_KEY'] 
    if k==secret_key and request.remote_addr in config['REMOTE_SERVER_IP']: # added "firewall" (he he) for selected IP only
        # status commander
        if task=='S_Q': # job in real queue
            query_db("UPDATE user_queue  set status='queue', status_init=strftime('%s', 'now') WHERE jid=?",[jid], insert=True) 

        elif task=='S_E': # job error
            query_db("UPDATE user_queue  set status='error',status_init=strftime('%s', 'now') WHERE jid=?",[jid], insert=True) 
            # TODO send mail to admin

        elif task=='S_R': # job running
            query_db("UPDATE user_queue  set status='running', status_init=strftime('%s', 'now') WHERE jid=?",[jid], insert=True) 

        elif task=='S_D': # job done
            query_db("UPDATE user_queue  set status='done', status_init=strftime('%s', 'now') WHERE jid=?",[jid], insert=True) 

        elif task=="LOAD" and request.method=='POST': 
            load = request.form['load']
            hostname = request.form['hostname']
            query_db("UPDATE  server_load SET load=?, name=?,status_date=(strftime('%s','now')) WHERE id=0",[load,hostname], insert=True)

        elif task=="LIGANDSEQ":
            t = query_db("SELECT ligand_sequence,ligand_ss FROM user_queue WHERE jid=?",[jid], one=True)
            out =  {'sequence': 'JESTEM', 'secstr': 'HAkER3M'}
            if t:
                out = {'sequence': t['ligand_sequence'], 'secstr': t['ligand_ss']}
            return Response(json.dumps(out),mimetype='application/json')

        elif task=="SCALFACTOR":
            t = query_db("SELECT constraints_scaling_factor FROM user_queue WHERE jid=?",[jid], one=True)
            return Response(json.dumps({'constraints_scaling_factor': t[0]}), mimetype='application/json')

    return Response("HEIL ERIS!",mimetype='text/plain')

