#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright Michal Jamroz, 2014, jamroz@chem.uw.edu.pl

from multikulti import app
from flask import render_template, g, request, send_from_directory, Response, url_for
from config import config
import os


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""

    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


@app.errorhandler(404)
def page_not_found(error):
    app.logger.warning('Page not found (IP: '+request.remote_addr+') '+request.url)
    return (render_template('page_not_found.html', code="404"), 404)


@app.errorhandler(500)
def page_error(error):
    app.logger.warning('Page 500 (IP: '+request.remote_addr+') '+request.url)
    return (render_template('page_not_found.html', code="500"), 500)


@app.route('/compute_static/<jobid>/input.pdb.gz')
def compute_static(jobid):
    return send_from_directory(app.config['USERJOB_DIRECTORY']+"/"+jobid,
                               "input.pdb.gz")
    # TODO co jesli filename bedzie do nadrzednych


@app.route('/compute_static/<jobid>/input.pdb')
def compute_static_pdb(jobid):
    return send_from_directory(app.config['USERJOB_DIRECTORY']+"/"+jobid,
                               "input.pdb")
    # TODO co jesli filename bedzie do nadrzednych


@app.route('/robots.txt')
def robots():
    return Response("User-agent: *\nDisallow: /job/", mimetype='text/plain')


@app.route('/citation')
def index_cite():
    return render_template('cite.html')


@app.route('/contact')
def index_contact():
    return render_template('contact.html')


@app.route('/learn_more')
def learn_more():
    return render_template('_learn_more.html')


@app.route('/tutorial')
def tutorial():
    return render_template('_tutorial.html')


@app.route('/benchmark')
def benchmark():
    jid = {}
    with open(os.path.join(config['STATIC'],"listaJobow.txt"), "r") as jids:
        for line in jids:
            d = line.split()
            jid[d[0]+d[1]] = d[2:5] + [''] + d[5:]
            #print jid[d[0]+d[1]]


    rows = ""
    with open(os.path.join(config['STATIC'],"tabelka.txt"), "r") as tab_txt:
        data = tab_txt.readlines()
        for line in data:
            rows += "<tr>" 
            d = line.split()
            bound = d[0]
            unbound = d[1]
            i = 0
            j = 0
            for e in d:
                if e == "|":
                    k = bound+unbound
                    if k in jid:
                        jd = jid[k]
                        if len(jd)>j and j!=3:
                            rows += "<td class=dt-center><a href='%s' target=_blank><i class='fa fa-flask'></i></a></td>" % (url_for('job_status',jid=jd[j]))
                        elif j>3 and j<7:
                            rows += "<td class=dt-center><i class='fa fa-close text-danger'></i></td>"
                    j+=1

                if i < 2 and e !="|":
                    e = e.replace("2qbh","1qbh")
                    if e != "-":
                        rows += "<td class=dt-justify><nobr><a href='http://www.pdb.org/pdb/explore/explore.do?structureId=%s' target='_blank'><i class='fa fa-external-link'></i> %s</a></nobr></td>" % (e,e.upper())
                    else:
                        rows += "<td class=dt-center><i class='fa fa-close text-danger'></i></td>"
                elif e != "|":
                    if e == '-':
                        rows += "<td class=dt-center><i class='fa fa-close text-danger'></i></td>"
                    else:
                        rows += "<td class=dt-right>%s</td>" % e

                i += 1
            rows += "</tr>\n"
    return render_template('benchmark.html', table=rows)


@app.route('/job/<jobid>/<filetype>/<filename>')
def sendfile(jobid, filetype, filename):
    filename = os.path.split(filename)[-1]
    jobid = os.path.split(jobid)[-1]  # zabezp przed ../ ?
    udir_path = os.path.join(app.config['USERJOB_DIRECTORY'], jobid)

    if filetype == 'clusters':
        return send_from_directory(os.path.join(udir_path, 'clusters'),
                                   filename, mimetype='application/x-gzip')
    elif filetype == 'models':
        return send_from_directory(os.path.join(udir_path, 'models'),
                                   filename, mimetype='application/x-gzip')
    elif filetype == 'replicas':
        return send_from_directory(os.path.join(udir_path, 'replicas'),
                                   filename, mimetype='application/x-gzip')
    else:
        return (render_template('page_not_found.html', code="404"), 404)
