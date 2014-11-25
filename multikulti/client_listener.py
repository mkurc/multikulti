#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright Michal Jamroz, 2014, jamroz@chem.uw.edu.pl

from multikulti import app
from config import config, query_db, send_mail
from flask import request, Response, url_for
import json
from os import path, makedirs
from shutil import rmtree


@app.route('/_queue')
def index_queue():
    q = query_db("SELECT jid FROM user_queue WHERE status='pre_queue'")
    d = ""
    for i in q:
        d += str(i[0]) + "\n"
    return Response(d, mimetype='text/plain')


@app.route('/_deleteOldJobs')
def delete_old():
    days = "-"+str(app.config['DELETE_USER_JOBS_AFTER'])
    to_delete = []
# TODO sprawdzic, czy to dziala
    for keyid in query_db("SELECT jid FROM user_queue WHERE \
            status_init<=date('now',?)", [days]):
        to_delete.append(keyid[0])
        pat_k = path.join(app.config['USERJOB_DIRECTORY'], keyid[0])
        rmtree(pat_k)
    for k in to_delete:
        query_db("DELETE FROM constraints WHERE jid=?", [k], insert=True)
    query_db("DELETE FROM user_queue where jid in (select jid FROM \
            user_queue WHERE status_init<=date('now',?))", [days], insert=True)

    return Response("HEIL ERIS!", mimetype='text/plain')


@app.route('/_server_talking/<secret_key>/<jid>/<task>/',
           methods=['POST', 'GET'])
def parse_server_talking(task, secret_key, jid):
    k = config['REMOTE_SERVER_SECRET_KEY']
    if k == secret_key and request.remote_addr in config['REMOTE_SERVER_IP']:
        # added "firewall" (he he) for selected IP only
        # status commander
        if task == 'S_Q':  # job in real queue
            query_db("UPDATE user_queue  set status='queue', \
                     status_init=strftime('%s', 'now') WHERE jid=?",
                     [jid], insert=True)

        elif task == 'S_E':
            # job error
            query_db("UPDATE user_queue  set status='error',\
                    status_init=strftime('%s', 'now') WHERE jid=?", [jid],
                     insert=True)
            tomail = query_db("SELECT email FROM user_queue WHERE jid=?",
                              [jid], one=True)[0]
            send_mail(subject="error "+jid)
            if len(tomail) > 1:
                send_mail(to=tomail, subject="error with job", body='Your job ('+jid+') got error status. Robot will inform admin.')

        elif task == 'S_R':
            # job running
            query_db("UPDATE user_queue  set status='running', \
                    status_init=strftime('%s', 'now') WHERE jid=?",
                     [jid], insert=True)
            tomail = query_db("SELECT email FROM user_queue WHERE jid=?",
                              [jid], one=True)[0]
            if len(tomail) > 1:
                send_mail(to=tomail, subject="Job is running: "+jid,
                          body="Wait for second mail about job done (or job error).")

        elif task == 'S_D':
            # job done
            query_db("UPDATE user_queue  set status='done', \
                    status_init=strftime('%s', 'now') WHERE jid=?",
                     [jid], insert=True)

            q = query_db("SELECT email,project_name FROM user_queue \
                    WHERE jid=?", [jid], one=True)
            tomail, name = q[0], q[1]
            if len(tomail) > 1:
                send_mail(to=tomail, subject="Job "+name+" completed",
                          body="Get results: "+url_for('job_status', jid=jid) +
                          " . Thanks for using our server")

        elif task == "LOAD" and request.method == 'POST':
            load = request.form['load']
            hostname = request.form['hostname']
            query_db("UPDATE  server_load SET load=?, name=?,\
                     status_date=(strftime('%s','now')) WHERE id=0",
                     [load, hostname], insert=True)

        elif task == "SENDSS" and request.method == 'POST':
            ss = request.form['ss']
            query_db("UPDATE  user_queue set ligand_ss=?,ss_psipred=1 \
                     WHERE jid=?", [ss, jid], insert=True)

        elif task == "LIGANDSEQ":
            t = query_db("SELECT ligand_sequence,ligand_ss FROM user_queue \
                         WHERE jid=?", [jid], one=True)
            out = {'sequence': 'JESTEM', 'secstr': 'HAkER3M'}
            if t:
                out = {'sequence': t['ligand_sequence'],
                       'secstr': t['ligand_ss']}
            return Response(json.dumps(out), mimetype='application/json')

        elif task == "SCALFACTOR":
            t = query_db("SELECT constraints_scaling_factor FROM user_queue \
                         WHERE jid=?", [jid], one=True)
            return Response(json.dumps({'constraints_scaling_factor': t[0]}),
                            mimetype='application/json')
        elif task == "RESTRAINTS":
            t = query_db("SELECT constraint_definition,force FROM constraints \
                         WHERE jid=?", [jid])
            out = []
            for row in t:
                out.append({'def': row[0], 'force': row[1]})
            return Response(json.dumps(out), mimetype='application/json')
        elif task == "SEND" and request.method == 'POST':
            user_dir = path.join(app.config['USERJOB_DIRECTORY'], jid)
            for d in ["models", 'clusters', 'replicas']:
                if not path.exists(path.join(user_dir, d)):
                    makedirs((path.join(user_dir, d)))

            for file in request.files.keys():
                filename = file
                request.files[file].save(path.join(user_dir, filename))

    return Response("HEIL ERIS!", mimetype='text/plain')
