#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Michal Jamroz 2014/09-2015/03 :-(

import os
import urllib2
import zipfile
import json
import re
from glob import glob
from StringIO import StringIO
import gzip
from shutil import rmtree, copy
from numpy import min, max, mean, ceil

from multikulti import app
from config import config, query_db, unique_id, gunzip, alphanum_key, send_mail, connect_db


from flask import render_template, url_for, request, flash, Response, g, \
    redirect, send_from_directory, jsonify
from flask.ext.uploads import UploadSet

from flask_wtf import Form
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, BooleanField, TextAreaField, HiddenField,\
    IntegerField
from wtforms.validators import DataRequired, Length, Email, optional, \
    ValidationError, NumberRange


from multikulti_modules.parsePDB import PdbParser
###############################################################################

app.config.update(config)
app.secret_key = 'multikultitosmierdzcywilizacjieurpejzkij'
input_pdb = UploadSet('inputpdbs', extensions=app.config['ALLOWED_EXTENSIONS'],
                      default_dest=app.config['UPLOAD_FOLDER'])


@app.before_request
def before_request():
    g.sqlite_db = connect_db()


def url_for_other_page(**kwargs):
    args = request.view_args.copy()
    for (k, v) in kwargs.iteritems():
        args[k] = v
    return url_for(request.endpoint, **args) + '?' + request.query_string

app.jinja_env.globals['url_for_other_page'] = url_for_other_page


def status_color(status, shorter=True):
    sho_tmp = '<span class="label label-%s"><i class="fa fa-%s">\
               </i> %s</span>  <small>%s</small>'
    if status == 'pending':
        return sho_tmp % ("primary", "edit", "job pending", "waiting for \
                adding/accepting constraints")
    elif status == 'pre_queue':
        return sho_tmp % ("warning", "spinner fa-spin", "job pending", "waiting for \
                computational server response")
    elif status == 'queue':
        return sho_tmp % ("info", "sliders", "in queue",  "waiting for \
                free CPU thread")
    elif status == 'running':
        return sho_tmp % ("primary", "bolt", "running", "")
    elif status == 'error':
        return sho_tmp % ("danger", "exclamation-circle", "error", "")
    elif status == 'done':
        return sho_tmp % ("success", "check-circle-o", "done", "")


def sequence_validator(form, field):
    allowed_seq = ['A', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'K', 'L', 'M', 'N',
                   'P', 'Q', 'R', 'S', 'T', 'V', 'W', 'Y']
    for letter in re.sub("\s", "", field.data):
        if letter not in allowed_seq:
            raise ValidationError('Sequence contains non-standard aminoacid \
                                  symbol: %s' % (letter))


def eqlen_validator(form, field):
    if len(field.data) != len(form.ligand_seq.data):
        raise ValidationError('Secondary structure length != ligand sequence \
                              length')


def ss_validator(form, field):
    allowed_seq = ['C', 'H', 'E']
    for letter in re.sub("\s", "", field.data):
        if letter not in allowed_seq:
            raise ValidationError('Secondary structure contains non-standard \
                    symbol: %s. <br><small>Allowed H - helix, \
                    E - extended/beta, C - coil.</small>' % (letter))


def structure_pdb_validator(form, field):
    if len(form.receptor_file.data.filename) < 5 and len(field.data) >= 4:
        d = field.data.split(":")
        pdbcode = d[0]
        if len(d) > 1:
            chain = d[1]
        else:
            chain = ''
        pdb_code = d[0]

        buraki = urllib2.urlopen('http://www.rcsb.org/pdb/files/'+pdb_code+'.pdb.gz')
        b2 = buraki.read()
        ft = StringIO(b2)


        with gzip.GzipFile(fileobj=ft, mode="rb") as f:
            p = PdbParser(f, chain=chain)
            missing = p.getMissing()
            seq = p.getSequence()
            allowed_seq = ['A', 'C', 'D', ' ', 'E', 'F', 'G', 'H', 'I', 'K', 'L',
                           'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'V', 'W', 'Y']
            for e in seq:
                if e not in allowed_seq:
                    raise ValidationError('Non-standard residue in the receptor \
                            structure')
            if len(p.getBody()) < 16 or len(seq) == 0:
                raise ValidationError('File without chain or chain shorter than \
                        4 residues')
            if len(seq) > 500:
                raise ValidationError('CABS-dock allows max 500 receptor \
                                       residues. Provided file contains \
                                       %d' % (len(seq)))
            if missing > 5:
                raise ValidationError('Missing atoms within protein (M+N = %d). \
                        Protein must fullfill M+N<6, where M - number of \
                        chains, N - number of breaks' % (missing))
        buraki.close()


def pdb_input_validator(form, field):
    if len(form.pdb_receptor.data) < 4 \
            and len(form.receptor_file.data.filename) < 5:
        raise ValidationError('PDB code or PDB file is required')
    if len(form.pdb_receptor.data) < 4 \
            and form.receptor_file.data:  # parse only if pdbcode empty
        p = PdbParser(form.receptor_file.data.stream)
        missing = p.getMissing()
        seq = p.getSequence()
        allowed_seq = ['A', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'K', 'L', 'M',
                       'N', 'P', 'Q', 'R', 'S', 'T', 'V', 'W', 'Y']
        for e in seq:
            if e not in allowed_seq:
                raise ValidationError('Non-standard residue in the receptor \
                                       structure')
        if len(p.getBody()) < 16 or len(seq) == 0:
            raise ValidationError('File without chain or chain shorter than \
                                   4 residues')
        if len(seq) > 500:
            raise ValidationError('CABS-dock allows max 500 receptor residues. \
                                   Provided file contains %d' % (len(seq)))
        if missing > 5:
            raise ValidationError('Missing atoms within receptor (M+N = %d). \
                    Protein must fullfill M+N<6, where M - number of chains, \
                    N - number of breaks' % (missing))


def pdb_input_code_validator(form, field):
    if len(field.data) < 4 and not form.receptor_file.data.filename:
        raise ValidationError('Protein code must be 4-letter (2PCY) or >5 \
                letters (2PCY:A or 2PCY:AB ...). Leave empty only if PDB \
                file is provided')
    if not form.pdb_receptor.data and not form.receptor_file.data:
        raise ValidationError('Protein PDB code or PDB file is required')


class MyForm(Form):
    name = StringField('Project name', validators=[Length(min=4, max=150),
                                                   optional()])
    pdb_receptor = StringField('PDB code', validators=[pdb_input_code_validator, structure_pdb_validator])
    receptor_file = FileField('PDB file', validators=[FileAllowed(input_pdb.extensions, 'PDB file format only!'), pdb_input_validator])
    ligand_seq = TextAreaField('Peptide sequence', validators=[Length(min=4, max=30), DataRequired(), sequence_validator])
    ligand_ss = TextAreaField('Peptide secondary structure', validators=[Length(min=4, max=30), optional(), ss_validator, eqlen_validator])
    email = StringField('E-mail address', validators=[optional(), Email()])
    show = BooleanField('Do not show my job on the results page',
                        default=False)
    add_constraints = BooleanField('Mark flexible regions', default=False)
    excluding = BooleanField('Mark unlikely to bind regions', default=False)
    jid = HiddenField(default=unique_id())
    resubmit = HiddenField(default=False)
    length = IntegerField('Simulation cycles', default=50,
                          validators=[NumberRange(5, 200)])


@app.route('/exclude_regions/<jid>/<final>/', methods=['GET', 'POST'])
def index_excluding(jid, final="True"):
    d = query_db("SELECT ligand_sequence,status FROM user_queue WHERE \
                 jid=%s AND status='pending'", [jid], one=True)
    ligand_sequence = d['ligand_sequence']
    status = d['status']
    jmol_string = 'Jmol.script(jmolApplet0,"select %s; color "+colors_jmol[%d]+"");'
    jmol_l = []

    constraints = query_db("SELECT excluded_region,excluded_jmol FROM \
            excluded WHERE jid=%s", [jid])
    for i in range(len(constraints)):
        jmol_l.append(jmol_string % (constraints[i]['excluded_jmol'], i))
    di = {'0.0': '<option value="0.0" selected>full</option><option \
          value="0.5">moderate</option>', '0.5': '<option value="0.5" selected>moderate</option>'}
    return render_template('exclude_regions.html', jid=jid, status=status,
                           constr=constraints, di=di, fin=final,
                           ligand_seq=ligand_sequence, jmol_color=jmol_l)


@app.route('/add_constraints/<jid>/<final>/', methods=['GET', 'POST'])
def index_constraints(jid, final="True"):
    d = query_db("SELECT ligand_sequence,status, constraints_scaling_factor \
            FROM user_queue WHERE jid=%s AND \
            status='pending'", [jid], one=True)
    ligand_sequence = d['ligand_sequence']
    status = d['status']
    scaling = d['constraints_scaling_factor']
    jmol_string = 'Jmol.script(jmolApplet0,"select %s; color "+colors_jmol[%d]+"");'
    jmol_l = []

    constraints = query_db("SELECT `constraint_definition`,`force`,\
                            `constraint_jmol` FROM constraints \
                            WHERE jid=%s", [jid])
    for i in range(len(constraints)):
        jmol_l.append(jmol_string % (constraints[i]['constraint_jmol'], i))
    di = {'0.0': '<option value="0.0" selected>full</option><option \
          value="0.5">moderate</option>', '0.5': '<option value="0.5" selected>moderate</option>'}

    return render_template('add_constraints.html', jid=jid, status=status, di=di,
                           scaling=scaling, constr=constraints, fin=final,
                           ligand_seq=ligand_sequence, jmol_color=jmol_l)


def add_init_data_to_db(form, final=False):
    jid = unique_id()

    if form.show.data:
        hide = 1
    else:
        hide = 0
    ligand_seq = ''.join(form.ligand_seq.data.upper().replace(' ', '').split())
    ligand_ss = ''.join(form.ligand_ss.data.upper().replace(' ', '').split())
    sim_length = int(form.length.data)

    # save receptor structure
    dest_directory = os.path.join(app.config['USERJOB_DIRECTORY'], jid)
    dest_file = os.path.join(dest_directory, "input.pdb.gz")
    os.mkdir(dest_directory)
    if form.resubmit.data == "True":  # if there is resubmit, skip parsing pdb
        old_jid = form.jid.data
        receptor_seq = form.receptor_seq.data
        old_receptor = os.path.join(app.config['USERJOB_DIRECTORY'],
                                    old_jid, "input.pdb")
        copy(old_receptor, os.path.join(dest_directory, "input.pdb"))
        with gzip.open(dest_file, "wb") as fw:
            with open(old_receptor, "r") as fr:
                fw.write(fr.read())

    else:
        if form.receptor_file.data.filename:
            p = PdbParser(form.receptor_file.data.stream)
            receptor_seq = p.getSequence()
            p.savePdbFile(dest_file)
            gunzip(dest_file)

        elif form.pdb_receptor.data:
            d = form.pdb_receptor.data.split(":")
            pdbcode = d[0]
            if len(d) > 1:
                chain = d[1]
            else:
                chain = ''
            buraki = urllib2.urlopen('http://www.rcsb.org/pdb/files/'+pdbcode+'.pdb.gz')
            b2 = buraki.read()
            ft = StringIO(b2)
            with gzip.GzipFile(fileobj=ft, mode="rb") as f:
                p = PdbParser(f, chain=chain)
                receptor_seq = p.getSequence()
                p.savePdbFile(dest_file)
                gunzip(dest_file)

            buraki.close()
    name = form.name.data
    if len(name) < 2:
        name = jid
    query_db("INSERT INTO user_queue(jid, email, receptor_sequence, \
             ligand_sequence, ligand_ss, hide, project_name,simulation_length) \
             VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", [jid, form.email.data, receptor_seq,
                                        ligand_seq, ligand_ss, hide, name,
                                        sim_length], insert=True)
    if form.resubmit.data == "True":  # if there is resubmit, skip parsing pdb
        old_jid = form.jid.data
        query_db("insert into constraints(`jid`,`constraint_definition`,\
                  `constraint_definition1`, `constraint_jmol`, `force`) \
                  SELECT %s,`constraint_definition`,`constraint_definition1`, \
                  `constraint_jmol`, `force` FROM constraints \
                  WHERE jid=%s", [jid, old_jid], insert=True)
        query_db("insert into excluded(jid,excluded_region,excluded_region1,\
                  excluded_jmol) SELECT %s,excluded_region,excluded_region1,\
                  excluded_jmol FROM excluded WHERE jid=%s", [jid, old_jid], insert=True)
    return (jid, receptor_seq, ligand_seq, form.name.data, form.email.data)


@app.route('/final_submit', methods=['POST', 'GET'])
def final_submit():
    if request.method == 'POST':
        jid = request.form.get('jid', '')
        if jid == '':
            return Response("OJ OJ, nieladnie", status=404,
                            mimetype='text/plain')

        flash('Job submitted. Bookmark this page to check results (usually within \
                24h) if you didn\'t povided e-mail address', 'info')
        query_db("UPDATE user_queue SET status=%s WHERE jid=%s",
                 ['pre_queue', jid], insert=True)
        return redirect(url_for('job_status', jid=jid))
    return Response("HAHAHAahahahakier", status=200, mimetype='text/plain')


def parse_out(q):
    out = []
    for row in q:
        if row['datet']:
            dtt = row['datet']
        else:
            dtt = "-"
        l = {'project_name': row['project_name'],
             'jid': row['jid'],
             'date': dtt,
             'status': status_color(row['status'])}

        out.append(l)
    return out


@app.route('/_queue_json', methods=['POST', 'GET'], defaults={'page': 1})
@app.route('/_queue_json/page/<int:page>/', methods=['POST', 'GET'])
def queue_page_json(page=1):
    before = (page - 1) * app.config['PAGINATION']
    # TODO przy searchu to nie bedzie dzialac, z lenistwa
    q = query_db("SELECT project_name, jid,status, \
            date_format(status_date, \"%%Y-%%m-%%d %%H:%%i:%%s\") \
            datet FROM user_queue WHERE hide=0 AND status!='pending' ORDER BY \
            status_date DESC LIMIT %s,%s", [before, app.config['PAGINATION']])
    out = parse_out(q)
    return jsonify({'data': out, 'page': page})


@app.route('/queue_txt')
def queue_txt():
    q = query_db("SELECT jid,project_name FROM user_queue where status='done' \
            ORDER BY id DESC", [])
    a = [i['jid']+"\t"+i['project_name'] for i in q]
    return Response("\n".join(a), mimetype='text/plain')


@app.route('/queue', methods=['POST', 'GET'], defaults={'page': 1})
@app.route('/queue/page/<int:page>/', methods=['POST', 'GET'])
def queue_page(page=1):
    before = (page - 1) * app.config['PAGINATION']

    if request.method == 'GET':
        search = request.args.get('q', '')
        if search != '':
            flash("Searching results for %s ..." % (search), 'warning')
            q = query_db("SELECT project_name, jid,status, status_date datet \
                          FROM user_queue WHERE (project_name LIKE %s OR jid \
                          LIKE %s or email=%s) and hide=0 UNION SELECT \
                          project_name, jid,status, status_date datet FROM \
                          user_queue WHERE (project_name=%s OR jid=%s or \
                          email=%s) and hide=1 ORDER BY datet DESC LIMIT \
                          1000", 2*["%"+search+"%"]+4*[search])

            q_all = query_db("SELECT count(*) l FROM (SELECT id FROM user_queue \
                              WHERE (project_name LIKE %s OR jid LIKE %s or \
                              email=%s) and hide=0 UNION SELECT id FROM \
                              user_queue WHERE (project_name=%s OR jid=%s or \
                              email=%s) and hide=1) z",
                              2*["%"+search+"%"]+4*[search], one=True)
            flash("Found %d results, displaying up to 1000" % (q_all['l']), 'warning')
            
            out = parse_out(q)
            if len(out) == 0:
                flash("Nothing found", "error")
            elif len(out) == 1:
                flash("Project found!", "info")
                jid = out[0]['jid']
                return redirect(url_for('job_status', jid=jid))

            return render_template('queue.html', queue=out, page=page,
                                   total_rows=len(q_all),search=True)

    qall = query_db("SELECT count(*) l FROM  user_queue WHERE hide=0 AND \
                    status!='pending'", [])
    q = query_db("SELECT project_name, jid,status, status_date datet FROM \
                 user_queue WHERE hide=0 AND status!='pending' ORDER BY \
                 status_date DESC LIMIT %s,%s", [before, app.config['PAGINATION']])

    return render_template('queue.html', queue=parse_out(q),
                           total_rows=qall[0], page=page, search=False)


class FormResubmit(MyForm):
    receptor_file = None
    pdb_receptor = None
    receptor_seq = HiddenField(default="")
    resubmit = HiddenField(default=True)


@app.route('/resubmit/<jid>/', methods=['GET', 'POST'])
def resubmit(jid):
    form = FormResubmit()
    jid = os.path.split(jid)[-1]
    system_info = query_db("SELECT ligand_sequence, simulation_length, receptor_sequence, \
            ligand_chain, project_name, ligand_ss, ss_psipred FROM user_queue \
            WHERE jid=%s", [jid], one=True)
    constraints = query_db("SELECT `constraint_definition`,`force` FROM \
            constraints WHERE jid=%s", [jid])
    exclu = query_db("SELECT excluded_region FROM excluded WHERE jid=%s", [jid])

    if not form.name.data:
        form.name.data = system_info['project_name']
    if not form.ligand_ss.data:
        form.ligand_ss.data = system_info['ligand_ss']
    if not form.ligand_seq.data:
        form.ligand_seq.data = system_info['ligand_sequence']
    if not form.length.data:
        form.length.data = system_info['simulation_length']
    form.jid.data = jid
    form.receptor_seq.data = system_info['receptor_sequence']

    if request.method == 'POST':
        if form.validate():
            newjid, rec, lig, nam, email = add_init_data_to_db(form)
            query_db("INSERT INTO models_skip(jid, prev_jid, model_id, \
                    removed_model) SELECT %s,prev_jid,model_id,removed_model FROM \
                    models_skip WHERE jid=%s", [newjid, jid], insert=True)

            for to_exclude in request.form.getlist('excluded'):
                udir_path = os.path.join(app.config['USERJOB_DIRECTORY'],
                                         jid, "clusters", to_exclude.replace("model", "cluster"))
                with gzip.open(udir_path, "rb") as fr:
                    query_db("INSERT INTO models_skip(`jid`, `prev_jid`, `model_id`, \
                              `removed_model`) VALUES(%s,%s,%s,%s)",
                              [newjid, jid, to_exclude, fr.read()], insert=True)

            if form.add_constraints.data or form.excluding.data:
                if form.add_constraints.data and form.excluding.data:
                    return redirect(url_for('index_constraints', jid=newjid,
                                            final="False"))
                elif form.excluding.data:
                    return redirect(url_for('index_excluding', jid=newjid,
                                            final="True"))
                else:
                    return redirect(url_for('index_constraints', jid=newjid,
                                            final="True"))
            else:
                flash('Job submitted. Bookmark this page to check results \
                      (usually within 24h) if you didn\'t povided e-mail \
                      address', 'info')
                query_db("UPDATE user_queue SET status=%s WHERE jid=%s",
                         ['pre_queue', newjid], insert=True)
                return redirect(url_for('job_status', jid=newjid))
        else:
            flash('Something goes wrong. Check errors within data \
                  input panel', 'error')

    models = {'models': []}
    udir_path = os.path.join(app.config['USERJOB_DIRECTORY'], jid)
    tm = [fil.split("/")[-1] for fil in glob(udir_path+"/models/*.gz")]
    models['models'] = sorted(tm, key=alphanum_key)
    # get indexes for RECEPTOR/LIGAND
    path_dir = os.path.join(app.config['USERJOB_DIRECTORY'], jid,
                            "models", models['models'][0])
    ligand_txt = ""
    receptor_txt = ""
    data = gzip.open(path_dir)
    file_content = data.readlines()
    atm = re.compile(r"^ATOM.{17}(?P<chain>.{1}).*$")
    data.close()
    chains_set = []
    for line in file_content:
        d = atm.match(line)
        if d:
            ch = d.groups()[0]
            if ch not in chains_set:
                chains_set.append(ch)
    # format as javascript data
    ligand_txt = "{'chain': '"+system_info['ligand_chain']+"'}"
    if system_info['ligand_chain'] in chains_set:
        chains_set.remove(system_info['ligand_chain'])
    for e in range(len(chains_set)):
        receptor_txt += "'"+chains_set[e]+"',"
    receptor_txt = "[" + receptor_txt[:-1] + "]"

    return render_template('resubmit.html', jid=jid, form=form,
                           results=models, rec_txt=receptor_txt,
                           lig_txt=ligand_txt, sys=system_info)


@app.route('/job/<jid>/')
def job_status(jid):
    if jid == 'REPLACE':  # to skip 500 if robots use javascript links
        return Response("null model", status=200, mimetype='text/plain')

    jid = os.path.split(jid)[-1]
    todel = str(app.config['DELETE_USER_JOBS_AFTER'])
    # check if job is from benchmark
    bench = query_db("select id from user_queue where status_date > \
            (select status_date from user_queue where jid=%s) \
            and jid=%s", [app.config['EXAMPLE_JOB'], jid], one=True)
    if bench is not None:
        botlab = True
    else:
        botlab = False

    system_info = query_db("SELECT ligand_sequence, receptor_sequence, \
            status_date, date_add(status_date, interval  %s day) del, \
            ligand_chain, status_init status_change, project_name, status, \
            constraints_scaling_factor, ligand_ss, ss_psipred, simulation_length macrocycles FROM user_queue \
            WHERE jid=%s", [todel, jid], one=True)

    if not system_info:
        return (render_template('page_not_found.html', code="404"), 404)

    constraints = query_db("SELECT `constraint_definition`,`force` FROM \
            constraints WHERE jid=%s", [jid])
    exclu = query_db("SELECT excluded_region FROM excluded WHERE jid=%s", [jid])
    if 'status' in system_info:  # google bot
        status = status_color(system_info['status'])
    else:
        status = 'undefined'
    # wylistuj wyniki jesli done
    models = {'models': [], 'clusters': [], 'replicas': []}
    udir_path = os.path.join(app.config['USERJOB_DIRECTORY'], jid)

    ligand_txt = ""
    receptor_txt = ""
    if system_info['status'] == 'done':
        for d in ['models', 'replicas', 'clusters']:
            tm = [fil.split("/")[-1] for fil in glob(udir_path+"/"+d+"/*.gz")]
            models[d] = sorted(tm, key=alphanum_key)

        # get indexes for RECEPTOR/LIGAND
        path_dir = os.path.join(app.config['USERJOB_DIRECTORY'], jid,
                                "models", models['models'][0])
        data = gzip.open(path_dir)
        file_content = data.readlines()
        atm = re.compile(r"^ATOM.{17}(?P<chain>.{1}).*$")
        data.close()
        chains_set = []
        for line in file_content:
            d = atm.match(line)
            if d:
                ch = d.groups()[0]
                if ch not in chains_set:
                    chains_set.append(ch)
        # format as javascript data
        ligand_txt = "{'chain': '"+system_info['ligand_chain']+"'}"
        if system_info['ligand_chain'] in chains_set:
            chains_set.remove(system_info['ligand_chain'])
        for e in range(len(chains_set)):
            receptor_txt += "'"+chains_set[e]+"',"
        receptor_txt = "[" + receptor_txt[:-1] + "]"

    if system_info['status'] == 'done':
        pie = calc_first_cluster_composition(jid)
        clust_details = cluster_stats(jid)
    else:
        pie = []
        clust_details = []
    if system_info['status'] == 'error':
        flash('Something went wrong. In most cases your PDB file is not properly formatted (according to the <a href="http://www.wwpdb.org/documentation/file-format">PDB file format</a>): <ul><li>continuous residue numbering (breaks are allowed, but chain must be numbered from N to M, where N&lt;M)</li><li>proper atom names within residues (for example if PDB file contains MET residue - atoms must be as in the methionine)</li><li>residue numbering must be unique - you cannot upload structure with the same residue index within the same chain</li><li>each chain must be defined with unique chain index. Empty string (" ") in chain index column is chain index, too. If you uploaded multichain structure without chain index column - you\'ll get an error</li><li>If PDB file looks good, do not hesistate to contact us (email in <a href="'+url_for('index_contact')+'">Contact tab</a>), we will check logs of your job.</li></ul>', 'error')

    if request.args.get('js', '') == 'js':
        return render_template('job_info.html', status=status, constr=constraints,
                            jid=jid, sys=system_info, results=models, pie=pie,
                            status_type=system_info['status'], ex=exclu,
                            lig_txt=ligand_txt, rec_txt=receptor_txt,
                            clu_det=clust_details, botlab=botlab)

    return render_template('job_info1.html', status=status, constr=constraints,
                           jid=jid, sys=system_info, results=models, pie=pie,
                           status_type=system_info['status'], ex=exclu,
                           lig_txt=ligand_txt, botlab=botlab,
                           clu_det=clust_details, rec_txt=receptor_txt)


@app.route('/examples')
def examples():
    c1 = cluster_stats("7f0bda72050182")
    c2 = cluster_stats("ccec04fc40c4c2e")
    return render_template('_examples.html', clu_det1=c1, clu_det2=c2)


@app.route('/_add_excluded', methods=['POST', 'GET'])
def user_add_excluded():
    if request.method == 'POST':
        jid = request.form.get('jid', '')
        if jid != '':
            constraints = request.form.getlist('constr[]')
            constraints_jmol = request.form.getlist('constr_jmol[]')
            query_db("DELETE FROM excluded WHERE jid=%s", [jid], insert=True)

            for r in zip(constraints, constraints_jmol):
                query_db("INSERT INTO excluded(jid,excluded_region, excluded_jmol) \
                        VALUES(%s,%s,%s)", [jid, r[0], r[1]], insert=True)
            return Response('OK', status=200)


@app.route('/_add_const_toDB', methods=['POST', 'GET'])
def user_add_constraints():
    if request.method == 'POST':
        jid = request.form.get('jid', '')
        if jid != '':
            constraints = request.form.getlist('constr[]')
            constraints_jmol = request.form.getlist('constr_jmol[]')
            weights = request.form.getlist('constr_w[]')
            scaling_factor = request.form.get('overall_weight', '1.0')
            query_db("DELETE FROM constraints WHERE jid=%s", [jid], insert=True)
            query_db("UPDATE user_queue SET constraints_scaling_factor=%s \
                    WHERE jid=%s", [scaling_factor, jid], insert=True)

            for r in zip(constraints, weights, constraints_jmol):
                query_db("INSERT INTO constraints(`jid`,`constraint_definition`,`force`,\
                        `constraint_jmol`) VALUES(%s,%s,%s,%s)", [jid]+list(r[:3]),
                        insert=True)
            return Response('OK', status=200)


@app.route('/', methods=['GET', 'POST'])
def index_page():
    # get remote server load. If delay 50 minut - OFLAJN
    q = query_db("SELECT `load` FROM server_load where id=0 AND \
                 status_date + interval 50 minute > now()", one=True)
    if not q or 'load' not in q:
        comp_status = '<span class="label label-danger">offline</span>'
        #send_mail(subject="cabsdock comp server offline?")
    elif q and int(q['load']) > 85:
        comp_status = '<span class="label label-warning">high load</span>'
    else:
        comp_status = '<span class="label label-success">online</span>'

    # forms
    form = MyForm()
    if request.method == 'POST':
        if form.validate():
            jid, rec, lig, nam, email = add_init_data_to_db(form)
            if form.add_constraints.data or form.excluding.data:
                if form.add_constraints.data and form.excluding.data:
                    return redirect(url_for('index_constraints', jid=jid, final="False"))
                elif form.excluding.data:
                    return redirect(url_for('index_excluding', jid=jid, final="True"))
                else:
                    return redirect(url_for('index_constraints', jid=jid, final="True"))
            else:
                flash('Job submitted. Bookmark this page to check results \
                      (usually within 24h) if you didn\'t povided e-mail \
                      address', 'info')
                query_db("UPDATE user_queue SET status=%s WHERE jid=%s",
                         ['pre_queue', jid], insert=True)
                return redirect(url_for('job_status', jid=jid))
        else:
            flash('Something goes wrong. Check errors within data \
                  input panel', 'error')
    return render_template('index.html', form=form, status=comp_status)


def simulation_parameters(jid):
    with gzip.open(os.path.join(app.config['USERJOB_DIRECTORY'], jid,
                                "README.txt"), "w") as fw:
        q = query_db("SELECT ligand_sequence, ligand_ss, receptor_sequence, \
                      project_name, status_date submitted, status_init \
                      finished, simulation_length macrocycles FROM user_queue \
                      where jid=%s", [jid], one=True)
        fw.write("CABS-dock simulation results. Kolinski's lab homepage: http://biocomp.chem.uw.edu.pl\n")
        fw.write("======================-oo8OO8oo-====================================================\n")
        fw.write("%28s : %s\n" % ("job_identifier", jid))
        for k in q.keys():
            fw.write("%28s : %s\n" % (k, q[k]))
        fw.write("\nflexible regions:\n")
        for row in query_db("SELECT `constraint_definition`, `force` FROM \
                            constraints WHERE jid=%s", [jid]):
            fw.write("%40s force: %5.2f\n" % (row['constraint_definition'], float(row['force'])))
        fw.write("\nexcluded regions:\n")
        for row in query_db("SELECT excluded_region FROM excluded WHERE jid=%s", [jid]):
            fw.write("%40s \n" % (row['excluded_region']))
        legend = '''
LEGEND:
input.pdb        - input structure of the receptor
trajectory_*.pdb - trajectories in CA-only representation
cluster_*.pdb    - models grouped into clusters in CA-only representation
model_*.pdb      - final models in all-atom representation
top1000.pdb      - top 1000 models
energy.txt       - log file from the simulation with energy and its distribution;
                   following columns contain:
                   replica frame temperature Energy(receptor) Energy(ligand)
                   Energy(interaction) Energy(total)
        '''
        fw.write(legend)


@app.route('/job/<jobid>/<models>/<model_name>/model.pdb')
def send_unzipped(jobid, model_name, models):

    jobid = jobid.replace("/", "")  # niby zabezpieczenie przed ../ ;-)
    models = models.split("/")[0]

    path_dir = os.path.join(app.config['USERJOB_DIRECTORY'], jobid, models,
                            model_name)
    with gzip.open(path_dir) as data:
        r = Response(data.read(), status=200, mimetype='chemical/x-pdb')
        out_name = jobid+"_"+model_name.split(".")[0]+".pdb"
        r.headers.add('Content-Disposition', 'attachment', filename=out_name)
        return r


def get_model(fo, model_idx):
    te = re.compile(r'MODEL.{6}'+str(model_idx)+'.*?ENDMDL',flags=re.DOTALL)
    out = te.search(fo.read()).group(0)
    return Response(out, status=200, mimetype='chemical/x-pdb')


def get_model_old(fo, model_idx):
    te = re.compile(r"^MODEL\s+"+str(model_idx)+"$")
    te2 = re.compile(r"^ENDMDL")
    line_start = -1
    line_stop = -1
    data = fo.readlines()
    for i in xrange(len(data)):
        if te.search(data[i]):
            line_start = i
            break
    for i in xrange(i, len(data)):
        if te2.search(data[i]):
            line_stop = i
            return Response("".join(data[line_start:line_stop]), status=200,
                            mimetype='chemical/x-pdb')


@app.route('/job/<jobid>/clusters/<model_idx>/<cluster_idx>/model.pdb')
def send_cluster_model(jobid, model_idx, cluster_idx):
    jobid = jobid.replace("/", "")  # niby zabezpieczenie przed ../ ;-)
    path_dir = os.path.join(app.config['USERJOB_DIRECTORY'], jobid, "clusters",
                            cluster_idx)
    with gzip.open(path_dir) as fo:
        return get_model(fo, model_idx)


@app.route('/job/<jobid>/models/<model_idx>/<rep_idx>/model.pdb')
def send_unzipped_cluster(jobid, model_idx, rep_idx):
    if rep_idx == 'REPIDX' or model_idx == 'IDX':  # google bot
        return Response("null model", status=200, mimetype='text/plain')

    jobid = jobid.replace("/", "")  # niby zabezpieczenie przed ../ ;-)
    path_dir = os.path.join(app.config['USERJOB_DIRECTORY'], jobid, "replicas",
                            "replica_"+str(rep_idx)+".pdb.gz")
    with gzip.open(path_dir) as fo:
        r = get_model(fo, model_idx)
        out_name = jobid+"_mod_"+str(model_idx)+"_tra_"+str(rep_idx)+".pdb"
        r.headers.add('Content-Disposition', u'attachment; filename="%s"' % (out_name) )
        return r


def make_zip(jid):
    if os.path.exists(os.path.join(app.config['USERJOB_DIRECTORY'],
                                   jid, "CABSdock_"+jid+".zip")):
        return

    jid = jid.split("/")[0]
    tu = os.getcwd()
    os.chdir(os.path.join(app.config['USERJOB_DIRECTORY'], jid))
    simulation_parameters(jid)

    dir_o = "CABSdock_"+jid

    for d in ["models", "clusters", "replicas"]:
        if not os.path.exists(os.path.join(dir_o, d)):
                os.makedirs(os.path.join(dir_o, d))
    files = [os.path.join(dp, f) for dp, dn, filenames in os.walk(".")
             for f in filenames if f != "klastry.txt" and
             dp != "CABSdock_"+jid and f != "input.pdb" and f != 'energy.txt']
    for file in files:
        file2 = os.path.basename(file)

        with gzip.GzipFile(file) as gz:
            fnams = os.path.splitext(file2)[0]
            if 'replica' in fnams:
                fnams = fnams.replace("replica", "trajectory")
            with open(os.path.join("CABSdock_"+jid, fnams), "w") as un:
                un.write(gz.read())
    for k in ['energy.txt']:
        inp = os.path.join(app.config['USERJOB_DIRECTORY'], jid,  k)
        out = os.path.join(app.config['USERJOB_DIRECTORY'], jid, dir_o, k)
        if os.path.isfile(inp):
            copy(inp, out)

    zf = zipfile.ZipFile("CABSdock_"+jid+".zip", "w", zipfile.ZIP_DEFLATED)
    files = [os.path.join(dp, f) for dp, dn, filenames in os.walk(dir_o)
             for f in filenames]
    for file in files:
        zf.write(file)
    zf.close()
    rmtree(dir_o)
    os.chdir(tu)


def cluster_stats(jid):
    cluster_details = []
    path = os.path.join(app.config['USERJOB_DIRECTORY'], jid, "klastry.txt")
    with open(path, "r") as rl:
        for line in rl:
            d = line.split()
            # gestosc maxrms srednirms medoid licznosc
            # 4.918   4.067   4.918   4.067    20         cluster_2.pdb:
            row = {'cluster': d[5][:-1], 'density': d[0], 'rmsd': d[2],
                   'counts': d[4], 'medoid': d[3][1:], 'maxrmsd': d[1]}
            cluster_details.append(row)
    return cluster_details


def calc_first_cluster_composition(jid):
    path = os.path.join(app.config['USERJOB_DIRECTORY'], jid, "klastry.txt")
    with open(path, "r") as rl:
        for line in rl:  # viczan .readlines():
            d = line.split()
            cluster = d[5][:-1]
            te = []
            for e in d[6:]:
                tt = e.split("_")
                te.append([int(tt[1]), int(tt[0])])
            if cluster == "cluster_1.pdb":
                # calc pie chart
                clusts = {}
                for e in te:
                    if e[1] in clusts:
                        clusts[e[1]] += 1
                    else:
                        clusts[e[1]] = 1
                break

        return json.dumps(clusts)


@app.route('/_clust_sep/<jid>')
def clustsep(jid):
    path = os.path.join(app.config['USERJOB_DIRECTORY'], jid, "klastry.txt")
    with open(path, "r") as rl:
        data = []
        data_tmp = {}
        pie_data = []
        for line in rl:
            d = line.split()
            cluster = d[5][:-1]
            te = []
            for e in d[6:]:
                tt = e.split("_")
                te.append([int(tt[1]), int(tt[0])])
            if cluster == "cluster_1.pdb":
                # calc pie chart
                clusts = {}
                for e in te:
                    if e[1] in clusts:
                        clusts[e[1]] += 1
                    else:
                        clusts[e[1]] = 1
                for k in clusts:
                    pie_data.append({'name': 'Trajectory '+str(k),
                                    'y': clusts[k]})

                data_tmp[cluster] = {'visible': True, 'name': cluster,
                                     'data': te}
            else:
                data_tmp[cluster] = {'visible': False, 'name': cluster,
                                     'data': te}
        # sort clusters by number
        for i in sorted(data_tmp, key=alphanum_key):
            data.append(data_tmp[i])
        data.append({"type": 'pie', "name": 'Number of elements in selected cluster(s)',
                     "data": pie_data, "center": [-160, 180], "size": 50,
                     "showInLegend": False, "shadow": False,
                     "ignoreHiddenPoint": True, "dataLabels": {"enabled": True}})

    return Response(json.dumps(data), mimetype='application/json')


@app.route('/job/CABSdock_<jobid>.zip')
def sendzippackage(jobid):
    make_zip(jobid)
    return send_from_directory(os.path.join(app.config['USERJOB_DIRECTORY'],
                               jobid), "CABSdock_"+jobid+".zip",
                               mimetype='application/x-zip')


@app.route('/_comp_time')
def comp_time():
    q = query_db("select (timestampdiff(minute,status_date, \
                  status_init)/60) h, (simulation_length*(length(\
                  ligand_sequence)+length(receptor_sequence))/50) l from \
                  user_queue where status='done' and status_date>(select \
                  status_date from user_queue where jid=%s)",
                 [app.config['EXAMPLE_JOB']])
    histogram = {}
    for row in q:
        tim_l = int(row['h'])
        seq_l = 50*round(int(row['l'])/50)

        if seq_l in histogram:
            histogram[seq_l].append(tim_l)
        else:
            histogram[seq_l] = [tim_l]
    avgs = []
    rangs = []
    elements = histogram.keys()
    elements.sort()

    for e in elements:
        mine = int(ceil(min(histogram[e])))
        maxe = int(ceil(max(histogram[e])))
        avge = int(ceil(mean(histogram[e])))
        rangs.append([int(e), mine, maxe])
        avgs.append([int(e), avge])
    return json.dumps({'avg': avgs, 'ranges': rangs})
