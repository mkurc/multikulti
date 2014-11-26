#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright Michal Jamroz, 2014, jamroz@chem.uw.edu.pl

from multikulti import app
from flask import render_template, g, url_for, request, jsonify, flash, \
    session, Response, redirect, send_from_directory
import os
from shutil import make_archive

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""

    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

    if hasattr(g, 'sqlite_user_db'):
        g.sqlite_user_db.close()


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
    return render_template('robots.txt')


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static', 'img'),
                               'favicon.png', mimetype='image/png')


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


@app.route('/job/<jobid>/simulation_results.tar')
def tar(jobid):
    jobid = jobid.replace("/", "")  # niby zabezpieczenie przed ../ ;-)
    udir_path = os.path.join(app.config['USERJOB_DIRECTORY'], jobid,
                             "simulation_results.tar")
    udir = app.config['USERJOB_DIRECTORY']
    if not os.path.exists(udir_path):
        cwd = os.getcwd()
        os.chdir(udir)
        make_archive(jobid+"/simulation_results", "tar", root_dir=".",
                     base_dir=jobid)
        os.chdir(cwd)
    return send_from_directory(os.path.join(app.config['USERJOB_DIRECTORY'],
                               jobid), "simulation_results.tar",
                               mimetype='application/x-tar')


@app.before_request
def before():
    if request.view_args and 'lang_code' in request.view_args:
        g.current_lang = request.view_args['lang_code']
        request.view_args.pop('lang_code')
