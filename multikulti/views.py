#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Michal Jamroz 2014/09

import os
import urllib2
import zipfile
import json
import re
from glob import glob
from StringIO import StringIO
import gzip
from shutil import make_archive, rmtree

from multikulti import app
from config import config, query_db, unique_id, gunzip, alphanum_key, send_mail

from flask import render_template, url_for, request, flash, Response, \
    redirect, send_from_directory, jsonify
from flask.ext.uploads import UploadSet

from flask_wtf import Form
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, BooleanField, TextAreaField, HiddenField,\
    IntegerField
from wtforms.validators import DataRequired, Length, Email, optional, \
    ValidationError, NumberRange


from multikulti_modules.parsePDB import PdbParser
# from multikulti_modules.restrRanges import restrRanges
###############################################################################

app.config.update(config)
app.secret_key = 'multikultitosmierdzcywilizacjieurpejzkij'
input_pdb = UploadSet('inputpdbs', extensions=app.config['ALLOWED_EXTENSIONS'],
                      default_dest=app.config['UPLOAD_FOLDER'])


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
                   'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'Y']
    d = ''.join(field.data.replace(' ', '').split()).upper()  # TODO poprawic
    for letter in d:
        if letter not in allowed_seq:
            raise ValidationError('Sequence contains non-standard aminoacid \
                                  symbol: %s' % (letter))


def eqlen_validator(form, field):
    if len(field.data) != len(form.ligand_seq.data):
        raise ValidationError('Secondary structure length != ligand sequence \
                              length')


def ss_validator(form, field):
    allowed_seq = ['C', 'H', 'E']
    d = ''.join(field.data.replace(' ', '').split()).upper()
    for letter in d:
        if letter not in allowed_seq:
            raise ValidationError('Secondary structure contains non-standard \
                    symbol: %s. <br><small>Allowed H - helix, \
                    E - extended/beta, C - coil.</small>' % (letter))


def structure_pdb_validator(form, field):
    if len(form.receptor_file.data.filename) < 5 and len(field.data) == 4:
        buraki = urllib2.urlopen('http://www.rcsb.org/pdb/files/'+field.data+'.pdb.gz')
        b2 = buraki.read()
        ft = StringIO(b2)
        with gzip.GzipFile(fileobj=ft, mode="rb") as f:
            p = PdbParser(f)
            missing = p.getMissing()
            seq = p.getSequence()
            allowed_seq = ['A', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'K', 'L',
                           'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V',
                           'W', 'Y']
            for e in seq:
                if e not in allowed_seq:
                    raise ValidationError('Non-standard residue in the receptor \
                            structure')
            if len(p.getBody()) < 16:
                raise ValidationError('File without chain or chain shorter than \
                        4 residues')
            if len(seq) > 500:
                raise ValidationError('CABSdock allows max 500 receptor \
                                       residues. Provided file contains %d' % (len(seq)))
            if missing > 5:
                raise ValidationError('Missing atoms within protein (M+N = %d). \
                        Protein must fullfill M+N<6, where M - number of \
                        chains, N - number of breaks' % (missing))
        buraki.close()


def pdb_input_validator(form, field):
    if len(form.pdb_receptor.data) < 4 and len(form.receptor_file.data.filename) < 5:
        raise ValidationError('PDB code or PDB file is required')
    if len(form.pdb_receptor.data) < 4 and form.receptor_file.data: # parse only if pdbcode empty
        p = PdbParser(form.receptor_file.data.stream)
        missing = p.getMissing()
        seq = p.getSequence()
        allowed_seq = ['A', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'K', 'L', 'M',
                       'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'Y']
        for e in seq:
            if e not in allowed_seq:
                raise ValidationError('Non-standard residue in the receptor \
                                       structure')
        if len(p.getBody()) < 16:
            raise ValidationError('File without chain or chain shorter than \
                                   4 residues')
        if len(seq) > 500:
            raise ValidationError('CABSdock allows max 500 receptor residues. \
                                   Provided file contains %d' % (len(seq)))
        if missing > 5:
            raise ValidationError('Missing atoms within receptor (M+N = %d). \
                    Protein must fullfill M+N<6, where M - number of chains, \
                    N - number of breaks' % (missing))


def pdb_input_code_validator(form, field):
    if len(field.data) < 4 and not form.receptor_file.data.filename:
        raise ValidationError('Protein code must be 4-letter (2PCY) or >5 letters (2PCY:A or 2PCY:AB ...). Leave empty only if PDB file is provided')
    if not form.pdb_receptor.data and not form.receptor_file.data:
        raise ValidationError('Protein PDB code or PDB file is required')


class MyForm(Form):
    name = StringField('Project name', validators=[Length(min=4, max=50),
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
    length = IntegerField('Simulation cycles', default=50,
                          validators=[NumberRange(5, 200)])


@app.route('/exclude_regions/<jid>/<final>/', methods=['GET', 'POST'])
def index_excluding(jid, final="True"):
    d = query_db("SELECT ligand_sequence,status \
            FROM user_queue WHERE jid=? AND status='pending'", [jid], one=True)
    ligand_sequence = d[0]
    status = d[1]
    jmol_string = 'Jmol.script(jmolApplet0,"select %s; color "+colors_jmol[%d]+"");'
    jmol_l = []

    constraints = query_db("SELECT excluded_region,excluded_jmol FROM \
            excluded WHERE jid=?", [jid])
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
            FROM user_queue WHERE jid=? AND status='pending'", [jid], one=True)
    ligand_sequence = d[0]
    status = d[1]
    scaling = d[2]
    jmol_string = 'Jmol.script(jmolApplet0,"select %s; color "+colors_jmol[%d]+"");'
    jmol_l = []

    constraints = query_db("SELECT constraint_definition,force,constraint_jmol FROM \
            constraints WHERE jid=?", [jid])
    for i in range(len(constraints)):
        jmol_l.append(jmol_string % (constraints[i]['constraint_jmol'], i))
    di = {'0.0': '<option value="0.0" selected>full</option><option \
          value="0.5">moderate</option>', '0.5': '<option value="0.5" selected>moderate</option>'}


    return render_template('add_constraints.html', jid=jid, status=status,
                           scaling=scaling, constr=constraints, di=di, fin=final,
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
    if form.receptor_file.data.filename:
        # print "plikkkkk" + form.receptor_file.data.filename
        p = PdbParser(form.receptor_file.data.stream)
        receptor_seq = p.getSequence()
        p.savePdbFile(dest_file)
        gunzip(dest_file)

    elif form.pdb_receptor.data:
        # print "receptor "+form.pdb_receptor.data
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
             VALUES(?,?,?,?,?,?,?,?)", [jid, form.email.data, receptor_seq,
                                        ligand_seq, ligand_ss, hide, name,
                                        sim_length], insert=True)

#    # generate constraints
#    unzpinp = os.path.join(app.config['USERJOB_DIRECTORY'], jid, "input.pdb")
#    r = restrRanges(unzpinp)
#    r.parseRanges()
#    for e, e1, e2 in zip(r.getLabelFormat(), r.getLabelFormatChains1(),
#                         r.getJmolFormat()):
#        query_db("INSERT INTO constraints(jid,constraint_definition, \
#                 constraint_definition1,constraint_jmol) VALUES(?,?,?,?)",
#                 [jid, e, e1, e2], insert=True)

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
        query_db("UPDATE user_queue SET status=? WHERE jid=?",
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
    q = query_db("SELECT project_name, jid,status, datetime(status_date, \
            'unixepoch') datet FROM user_queue WHERE hide=0 \
            AND status!='pending' ORDER BY status_date DESC LIMIT ?,?",
                 [before, app.config['PAGINATION']])
    out = parse_out(q)
    return jsonify({'data': out, 'page': page})


@app.route('/queue', methods=['POST', 'GET'], defaults={'page': 1})
@app.route('/queue/page/<int:page>/', methods=['POST', 'GET'])
def queue_page(page=1):
    before = (page - 1) * app.config['PAGINATION']

    if request.method == 'GET':
        search = request.args.get('q', '')
        if search != '':
            flash("Searching results for %s ..." % (search), 'warning')
            q = query_db("SELECT project_name, jid,status, datetime(status_date, 'unixepoch') datet \
                    FROM user_queue WHERE project_name LIKE ? OR jid=? ORDER BY \
                    status_date DESC LIMIT ?,?",
                    ["%"+search+"%", search, before, app.config['PAGINATION']])
            q_all = query_db("SELECT status FROM user_queue WHERE project_name \
                    LIKE ? OR jid=? ORDER BY  status_date DESC", ["%"+search+"%", search])
            # jesli jest szukanie po nazwie projektu to ukrywanie zadan przestaje miec sens TODO
            out = parse_out(q)
            if len(out) == 0:
                flash("Nothing found", "error")
            elif len(out) == 1:
                flash("Project found!", "info")
                jid = out[0]['jid']
                return redirect(url_for('job_status', jid=jid))

            return render_template('queue.html', queue=out, page=page,
                                   total_rows=len(q_all))

    qall = query_db("SELECT status FROM  user_queue WHERE hide=0 AND \
                    status!='pending' ORDER BY status_date DESC", [])
    q = query_db("SELECT project_name, jid,status, datetime(status_date, \
            'unixepoch') datet FROM user_queue WHERE hide=0 \
            AND status!='pending' ORDER BY status_date DESC LIMIT ?,?",
                 [before, app.config['PAGINATION']])
    out = parse_out(q)

    return render_template('queue.html', queue=out, total_rows=len(qall),
                           page=page)


@app.route('/job/<jid>/')
def job_status(jid):
    jid = os.path.split(jid)[-1]
    todel = "+"+str(app.config['DELETE_USER_JOBS_AFTER'])+" days"

    system_info = query_db("SELECT ligand_sequence, receptor_sequence, \
            datetime(status_date,'unixepoch') status_date, \
            date(status_init, 'unixepoch', ?) del, ligand_chain, \
            datetime(status_init,'unixepoch') status_change, project_name, \
            status,constraints_scaling_factor, ligand_ss, ss_psipred FROM \
            user_queue WHERE jid=?", [todel, jid], one=True)
    constraints = query_db("SELECT constraint_definition,force FROM \
            constraints WHERE jid=?", [jid])
    exclu = query_db("SELECT excluded_region FROM excluded WHERE jid=?", [jid])
    status = status_color(system_info['status'])
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



    # TODO usunac pozniej !!!!!
    if os.path.exists(os.path.join(app.config['USERJOB_DIRECTORY'], jid, "klastry.txt")):
        pie = calc_first_cluster_composition(jid)
        clust = True
    else:
        clust = False
        pie = "{}"

    if request.args.get('js', '') == 'js':
        return render_template('job_info.html', status=status, constr=constraints,
                            jid=jid, sys=system_info, results=models, pie=pie,
                            status_type=system_info['status'], ex=exclu, clust=clust,
                            lig_txt=ligand_txt, rec_txt=receptor_txt)

    return render_template('job_info1.html', status=status, constr=constraints,
                           jid=jid, sys=system_info, results=models, pie=pie,
                           status_type=system_info['status'], ex = exclu, clust=clust,
                           lig_txt=ligand_txt, rec_txt=receptor_txt)


@app.route('/_add_excluded', methods=['POST', 'GET'])
def user_add_excluded():
    if request.method == 'POST':
        jid = request.form.get('jid', '')
        if jid == '':
            return Response("OJ OJ, nieladnie", status=404,
                            mimetype='text/plain')

        constraints = request.form.getlist('constr[]')
        constraints_jmol = request.form.getlist('constr_jmol[]')
        query_db("DELETE FROM excluded WHERE jid=?", [jid], insert=True)

        for r in zip(constraints, constraints_jmol):
            query_db("INSERT INTO excluded(jid,excluded_region, excluded_jmol) \
                    VALUES(?,?,?)", [jid, r[0], r[1]], insert=True)
    return Response("HAHAHAahahahakier", status=200, mimetype='text/plain')


@app.route('/_add_const_toDB', methods=['POST', 'GET'])
def user_add_constraints():
    if request.method == 'POST':
        jid = request.form.get('jid', '')
        if jid == '':
            return Response("OJ OJ, nieladnie", status=404,
                            mimetype='text/plain')

        constraints = request.form.getlist('constr[]')
        constraints_jmol = request.form.getlist('constr_jmol[]')
        weights = request.form.getlist('constr_w[]')
        scaling_factor = request.form.get('overall_weight', '1.0')
        query_db("DELETE FROM constraints WHERE jid=?", [jid], insert=True)
        query_db("UPDATE user_queue SET constraints_scaling_factor=? \
                WHERE jid=?", [scaling_factor, jid], insert=True)

        for r in zip(constraints, weights, constraints_jmol):
            query_db("INSERT INTO constraints(jid,constraint_definition,force,\
                     constraint_jmol) VALUES(?,?,?,?)", [jid, r[0], r[1], r[2]],
                     insert=True)

    return Response("HAHAHAahahahakier", status=200, mimetype='text/plain')


@app.route('/', methods=['GET', 'POST'])
def index_page():
    # get remote server load. If delay 50 minut - OFLAJN
    q = query_db("SELECT load FROM server_load where id=0 AND \
                 datetime(status_date, 'unixepoch', '+50 minutes')> \
                 datetime('now')", one=True)
    if not q:
        comp_status = '<span class="label label-danger">offline</span>'
        # TODO send_mail(subject="cabsdock comp server offline?")
    elif int(q[0]) > 85:
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
                query_db("UPDATE user_queue SET status=? WHERE jid=?",
                         ['pre_queue', jid], insert=True)
                return redirect(url_for('job_status', jid=jid))
        else:
            flash('Something goes wrong. Check errors within data \
                  input panel', 'error')
    return render_template('index.html', form=form, status=comp_status)


def simulation_parameters(jid):
    with open(os.path.join(app.config['USERJOB_DIRECTORY'], jid,
                           "README.txt"), "w") as fw:
        q = query_db("SELECT ligand_sequence, ligand_ss, receptor_sequence, \
                      project_name, datetime(status_date,'unixepoch') \
                      submitted, datetime(status_init, 'unixepoch') finished, \
                      constraints_scaling_factor FROM user_queue where jid=?",
                     [jid], one=True)
        fw.write("CABSdock simulation results. Kolinski's lab homepage: http://biocomp.chem.uw.edu.pl\n")
        fw.write("======================================================================================\n")
        fw.write("%28s : %s\n" % ("job_identifier", jid))
        for k in q.keys():
            fw.write("%28s : %s\n" % (k, q[k]))
        q = query_db("SELECT constraint_definition, force FROM constraints \
                      WHERE jid=?", [jid])
        fw.write("\nFLEXIBLE:\n")
        for row in q:
            fw.write("%40s force: %5.2f\n" % (row[0], float(row[1])))
        q = query_db("SELECT excluded_region FROM excluded \
                      WHERE jid=?", [jid])
        fw.write("\nEXCLUDED:\n")
        for row in q:
            fw.write("%40s \n" % (row[0]))


@app.route('/job/<jobid>/<models>/<model_name>/model.pdb')
def send_unzipped(jobid, model_name, models):

    jobid = jobid.replace("/", "")  # niby zabezpieczenie przed ../ ;-)
    models = models.split("/")[0]

    path_dir = os.path.join(app.config['USERJOB_DIRECTORY'], jobid, models,
                            model_name)
    data = gzip.open(path_dir)
    file_content = data.read()
    data.close()
    return Response(file_content, status=200, mimetype='chemical/x-pdb')


@app.route('/job/<jobid>/models/<model_idx>/<rep_idx>/model.pdb')
def send_unzipped_cluster(jobid, model_idx, rep_idx):
    jobid = jobid.replace("/", "")  # niby zabezpieczenie przed ../ ;-)
    path_dir = os.path.join(app.config['USERJOB_DIRECTORY'], jobid, "replicas",
                            "replica_"+str(rep_idx)+".pdb.gz")
    with gzip.open(path_dir) as fo:
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
                break
        return Response("".join(data[line_start:line_stop]), status=200,
                        mimetype='chemical/x-pdb')


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
             for f in filenames if f != "klastry.txt" and dp != "CABSdock_"+jid and f != "input.pdb"]
    for file in files:
        file2 = "/".join(file.split("/")[1:])
        file2 = os.path.basename(file)

        with gzip.GzipFile(file) as gz:
            with open(os.path.join("CABSdock_"+jid,
                      os.path.splitext(file2)[0]), "w") as un:
                un.write(gz.read())

    zf = zipfile.ZipFile("CABSdock_"+jid+".zip", "w", zipfile.ZIP_DEFLATED)
    files = [os.path.join(dp, f) for dp, dn, filenames in os.walk(dir_o)
             for f in filenames]
    for file in files:
        zf.write(file)
    zf.close()
    rmtree(dir_o)
    os.chdir(tu)


def calc_first_cluster_composition(jid):
    path = os.path.join(app.config['USERJOB_DIRECTORY'], jid, "klastry.txt")
    with open(path, "r") as rl:
        for line in rl.readlines():
            d = line.split(" ")
            cluster = d[0][:-1]
            te = []
            for e in d[1:]:
                tt = e.split("_")
                te.append([int(tt[0]), int(tt[1])])
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
        for line in rl.readlines():
            d = line.split(" ")
            cluster = d[0][:-1]
            te = []
            for e in d[1:]:
                tt = e.split("_")
                te.append([int(tt[0]), int(tt[1])])
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


@app.route('/plot')
def plotclust():
    return render_template('cluster_sep.html')


@app.route('/job/CABSdock_<jobid>.zip')
def sendzippackage(jobid):
    make_zip(jobid)
    return send_from_directory(os.path.join(app.config['USERJOB_DIRECTORY'],
                               jobid), "CABSdock_"+jobid+".zip",
                               mimetype='application/x-zip')
