#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright Michal Jamroz, 2014, jamroz@chem.uw.edu.pl

from multikulti import app
from config import config, query_db#, send_mail
from flask import request, Response, url_for
import json
from os import path, makedirs
from shutil import rmtree
def send_mail(to='', subject="Test", body="Body"):
    pass


@app.route('/_queue')
def index_queue():
    q = query_db("SELECT jid FROM user_queue WHERE status='pre_queue'")
    d = "\n".join([str(i['jid']) for i in q])
    return Response(d, mimetype='text/plain')


@app.route('/_deleteOldJobs')
def delete_old():
    days = str(app.config['DELETE_USER_JOBS_AFTER'])
    to_delete = []
    for keyid in query_db("SELECT jid FROM user_queue WHERE \
            status_init<= now() - interval %s day", [days]):
        if keyid['jid'] not in app.config['EXAMPLE_JOB']:
            to_delete.append(keyid['jid'])
            pat_k = path.join(app.config['USERJOB_DIRECTORY'], keyid[0])
            rmtree(pat_k)
    for k in to_delete:
        query_db("DELETE FROM models_skip WHERE jid=%s", [k])
        query_db("DELETE FROM constraints WHERE jid=%s", [k])
        query_db("DELETE FROM user_queue WHERE jid=%s", [k], insert=True)

    return Response("HEIL ERIS!", mimetype='text/plain')


@app.route('/_server_talking/<secret_key>/<jid>/<task>/',methods=['POST', 'GET'])
def parse_server_talking(task, secret_key, jid):
    k = config['REMOTE_SERVER_SECRET_KEY']
    if k == secret_key and request.remote_addr in config['REMOTE_SERVER_IP']:
        # added "firewall" (he he) for selected IP only
        # status commander
        if task == 'S_Q':  # job in real queue
            query_db("UPDATE user_queue  set status='queue', \
                     status_init=now() WHERE jid=%s",
                     [jid], insert=True)

        elif task == 'S_E':
            # job error
            query_db("UPDATE user_queue  set status='error',\
                    status_init=now() WHERE jid=%s", [jid],
                     insert=True)
            tomail = query_db("SELECT email FROM user_queue WHERE jid=%s",
                              [jid], one=True)
            send_mail(subject="error "+jid)
            if 'email' in tomail and len(tomail['email']) > 1:
                send_mail(to=tomail['email'], subject="error with job",
                          body='Your job ('+jid+') got error status. Robot informed admin.')

        elif task == 'S_R':
            # job running
            query_db("UPDATE user_queue  set status='running', \
                    status_init=now() WHERE jid=%s",
                     [jid], insert=True)
            tomail = query_db("SELECT email FROM user_queue WHERE jid=%s",
                              [jid], one=True)
            if 'email' in tomail and len(tomail['email']) > 1:
                send_mail(to=tomail, subject="Job is running: "+jid,
                          body="Wait for second mail about job done (or job error).")

        elif task == 'S_D':
            # job done
            query_db("UPDATE user_queue  set status='done', \
                    status_init=now() WHERE jid=%s",
                     [jid], insert=True)

            q = query_db("SELECT email,project_name FROM user_queue \
                    WHERE jid=%s", [jid], one=True)
            if 'email' in q and len(q['email']) > 1:
                send_mail(to=q['email'], subject="Job "+q['project_name']+" completed",
                          body="Get results: "+url_for('job_status', jid=jid, _external=True) +
                          " . Thanks for using our server")

        elif task == "LOAD" and request.method == 'POST':
            load = int(request.form['load'])
            hostname = request.form['hostname']
            query_db("UPDATE  server_load SET `load`=%s, `name`=%s,\
                     `status_date`=now() WHERE id=0",
                     [load, hostname], insert=True)

        elif task == "SENDSS" and request.method == 'POST':
            ss = request.form['ss']
            query_db("UPDATE  user_queue set ligand_ss=%s,ss_psipred=1 \
                     WHERE jid=%s", [ss, jid], insert=True)

        elif task == "LIGCHAIN" and request.method == 'POST':
            ss = request.form['chain']
            query_db("UPDATE  user_queue set ligand_chain=%s \
                     WHERE jid=%s", [ss, jid], insert=True)

        elif task == "LIGANDSEQ":
            t = query_db("SELECT ligand_sequence,ligand_ss FROM user_queue \
                         WHERE jid=%s", [jid], one=True)
            out = {'sequence': 'JESTEM', 'secstr': 'HAkER3M'}
            if t:
                out = {'sequence': t['ligand_sequence'],
                       'secstr': t['ligand_ss']}
            return Response(json.dumps(out), mimetype='application/json')
        elif task == "SCALFACTOR":
            t = query_db("SELECT constraints_scaling_factor FROM user_queue \
                         WHERE jid=%s", [jid], one=True)
            return Response(json.dumps({'constraints_scaling_factor': t['constraints_scaling_factor']}),
                            mimetype='application/json')
        elif task == "LENGTH":
            t = query_db("SELECT simulation_length FROM user_queue \
                         WHERE jid=%s", [jid], one=True)
            return Response(json.dumps({'sim_length': t['simulation_length']}),
                            mimetype='application/json')
        elif task == "JOBNAME":
            t = query_db("SELECT project_name FROM user_queue WHERE jid=%s",
                         [jid], one=True)
            return Response(json.dumps({'jobname': t['project_name']}),
                            mimetype='application/json')
        elif task == "RESTRAINTS":
            t = query_db("SELECT `constraint_definition`,`force` FROM constraints \
                         WHERE jid=%s", [jid])
            out = [{'def': row['constraint_definition'], 'force': row['force']} for row in t]
            return Response(json.dumps(out), mimetype='application/json')
        elif task == "EXCLUDED":
            t = query_db("SELECT excluded_region FROM excluded \
                         WHERE jid=%s", [jid])
            out = [{'excluded': row['excluded_region']} for row in t]
            return Response(json.dumps(out), mimetype='application/json')
        elif task == 'SKIPMODELS':
            t = query_db("SELECT model_id, removed_model, prev_jid \
                         FROM models_skip WHERE jid=%s", [jid])
            # mozliwe ze ta konwersja nie jest konieczna TODO
            out = []
            for row in t:
                out.append({'model_id': row['model_id'], 'prev_jid': row['prev_jid'],
                            'model_body': row['removed_model']})
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
