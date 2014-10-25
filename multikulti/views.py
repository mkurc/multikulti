#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Michal Jamroz 2014/09

import os
import urllib2
from datetime import datetime
from StringIO import StringIO
import gzip

from multikulti import app
from config import config, query_db, unique_id, gzipped

from flask import render_template, g, url_for, request, flash, \
    Response, redirect, send_from_directory
#from flask.ext.login import login_required,current_user

from flask.ext.uploads import UploadSet

from flask_wtf import Form
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, BooleanField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Length, Email, optional, ValidationError


from multikulti_modules.fetchPDBinfo import getCoordinates, fetchPDBinfo
from multikulti_modules.parsePDB import  PdbParser
from multikulti_modules.restrRanges import restrRanges
################################################################################

app.config.update(config)
app.secret_key = 'multikultitosmierdzcywilizacjieurpejzkij'
input_pdb = UploadSet('inputpdbs', extensions = app.config['ALLOWED_EXTENSIONS'],\
        default_dest = app.config['UPLOAD_FOLDER']) 
def url_for_other_page(**kwargs):
    args = request.view_args.copy()
    for (k, v) in kwargs.iteritems():
        args[k] = v
    return url_for(request.endpoint, **args) + '?' + request.query_string

app.jinja_env.globals['url_for_other_page'] = url_for_other_page



def status_color(status,shorter=True):
    if not shorter:
        if status=='pending':
            return '<span class="label label-primary"><i class="fa fa-edit"></i> job pending <small>waiting for adding/accepting constraints</small></span>'
        elif status=='pre_queue':
            return '<span class="label label-warning"><i class="fa fa-spin fa-spinner"></i> job pending <small>waiting for computational server response</small></span>'
        elif status=='queue':
            return '<span class="label label-info"><i class="fa fa-sliders"></i> in queue</span>'
        elif status=='running':
            return '<span class="label label-info"><i class="fa fa-cog fa-spin"></i> running</span>'
        elif status=='error':
            return '<span class="label label-danger"><i class="fa fa-exclamation-triangle"></i> error!</span>'
    else:
        if status=='pending':
            return '<span class="label label-primary"><i class="fa fa-edit"></i> job pending</span> <small>waiting for adding/accepting constraints</small>'
        elif status=='pre_queue':
            return '<span class="label label-warning"><i class="fa fa-spin fa-spinner"></i> job pending</span> <small>waiting for computational server response</small>'
        elif status=='queue':
            return '<span class="label label-info"><i class="fa fa-sliders"></i> in queue</span>'
        elif status=='running':
            return '<span class="label label-info"><i class="fa fa-cog fa-spin"></i> running</span>'
        elif status=='error':
            return '<span class="label label-danger"><i class="fa fa-exclamation-triangle"></i> error!</span>'



def sequence_validator(form, field):
    allowed_seq = ['A', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'K', 'L', 'M', 'N',\
            'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'Y']
    d = ''.join(field.data.replace(' ','').split()).upper() # TODO poprawic
    for letter in d:
        if letter not in allowed_seq:
            raise ValidationError('Sequence contains non-standard aminoacid symbol: %s' % (letter) )
def eqlen_validator(form, field):
    if len(field.data) != len(form.ligand_seq.data):
        raise ValidateError('Secondary structure length != ligand sequence length')
def ss_validator(form, field):
    allowed_seq = ['C', 'H', 'E']
    d = ''.join(field.data.replace(' ','').split()).upper()
    for letter in d:
        if letter not in allowed_seq:
            raise ValidationError('Secondary structure contains non-standard \
                    symbol: %s. <br><small>Allowed H - helix, E - extended/beta,\
                    C - coil.</small>' % (letter) )
def structure_pdb_validator(form, field):
    if len(form.receptor_file.data.filename)<5 and len(field.data)==5:
        buraki =  urllib2.urlopen('http://www.rcsb.org/pdb/files/'+field.data+'.pdb.gz')
        b2 = buraki.read()
        ft = StringIO(b2)
        with gzip.GzipFile(fileobj=ft,mode="rb") as f:
            p = PdbParser(f)
            missing = p.getMissing()
            seq =  p.getSequence()
            allowed_seq = ['A', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'K', 'L', 'M', 'N',\
                    'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'Y']
            for e in seq:
                if e not in allowed_seq:
                    raise ValidationError('Non-standard residue in the receptor \
                            structure')
            if len(p.getBody()) < 16:
                raise ValidationError('File without chain or chain shorter than \
                        4 residues')
            if len(missing)>0:
                raise ValidationError('Missing atoms around residue(s): %s. Server \
                        accepts only continuous chains.' % missing)
        buraki.close()

def pdb_input_validator(form, field):
    if len(form.pdb_receptor.data)!=4 and len(form.receptor_file.data.filename)<5:
        raise ValidationError('PDB code or PDB file is required')
    if len(form.pdb_receptor.data) !=4 and form.receptor_file.data: # parse only if pdbcode empty
        p = PdbParser(form.receptor_file.data.stream)
        missing = p.getMissing()
        seq =  p.getSequence()
        allowed_seq = ['A', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'K', 'L', 'M', 'N',\
                'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'Y']
        for e in seq:
            if e not in allowed_seq:
                raise ValidationError('Non-standard residue in the receptor structure')
        if len(p.getBody()) < 16:
            raise ValidationError('File without chain or chain shorter than 4 residues')
        if len(missing)>0:
            raise ValidationError('Missing atoms around residue(s): %s. Server \
                    accepts only continuous chains.' % missing)

def pdb_input_code_validator(form, field):
    if len(field.data)!=4 and not form.receptor_file.data.filename:
        raise ValidationError('Receptor code must be 4-letter (2PCY). Leave \
                empty only if PDB file is provided')
    if not form.pdb_receptor.data and not form.receptor_file.data:
        raise ValidationError('Receptor PDB code or PDB file is required')

class MyForm(Form):
    name = StringField('Project name', validators=[Length(min=4,max=50),optional()])
    pdb_receptor = StringField('Remote PDB file', \
            validators=[pdb_input_code_validator, structure_pdb_validator])
    receptor_file = FileField('Local PDB file', \
            validators=[FileAllowed(input_pdb.extensions, 'PDB file format only!'), \
            pdb_input_validator])
    ligand_seq = TextAreaField('Ligand sequence', \
            validators=[Length(min=3,max=60),DataRequired(),sequence_validator])
    ligand_ss = TextAreaField('Ligand secondary structure', \
            validators=[Length(min=3,max=60),optional(),ss_validator,eqlen_validator])
    email = StringField('E-mail address', 
            validators = [optional(), Email()])
    show = BooleanField('Do not show my job on the results page', default=False)
    jid = HiddenField(default=unique_id())

@app.route('/add_constraints/<jid>/', methods=['GET','POST'])
def index_constraints(jid):
    d = query_db("SELECT ligand_sequence,status, constraints_scaling_factor \
            FROM user_queue WHERE jid=?", [jid],one=True)
    ligand_sequence = d[0]
    status = d[1]
    scaling = d[2]

    constraints = query_db("SELECT constraint_definition,force FROM \
            constraints WHERE jid=?", [jid])
    print constraints
    di ={'1.0': '<option value="1.0" selected>default</option><option \
            value="0.25">light</option><option value="5.0">strong</option>',
            '0.25': '<option value="0.25" selected>light</option><option \
                    value="1.0">default</option><option value="5.0">strong</option>',
            '5.0': '<option value="5.0" selected>strong</option><option \
                    value="1.0">default</option><option value="0.25">light</option>'}

    return render_template('add_constraints.html',jid=jid, status=status, 
            scaling=scaling, constr = constraints, ligand_seq=ligand_sequence,di=di)
  
def add_init_data_to_db(form):
    jid = unique_id()

    if form.show.data:
        hide = 1
    else:
        hide = 0
    ligand_seq = ''.join(form.ligand_seq.data.upper().replace(' ','').split())
    ligand_ss = ''.join(form.ligand_ss.data.upper().replace(' ','').split())

    # save receptor structure
    dest_directory = os.path.join(app.config['USERJOB_DIRECTORY'],jid)
    dest_file = os.path.join(dest_directory, "input.pdb.gz")
    os.mkdir(dest_directory)
    if form.receptor_file.data.filename:
        p = PdbParser(form.receptor_file.data.stream)
        receptor_seq =  p.getSequence()
        p.savePdbFile(dest_file)
        gunzip(dest_file)
        

    elif form.pdb_receptor.data:
        buraki =  urllib2.urlopen('http://www.rcsb.org/pdb/files/'+form.pdb_receptor.data+'.pdb.gz')
        b2 = buraki.read()
        ft = StringIO(b2)
        with gzip.GzipFile(fileobj=ft,mode="rb") as f:
            p = PdbParser(f)
            receptor_seq =  p.getSequence()
            p.savePdbFile(dest_file)
            gunzip(dest_file)

        buraki.close()
    name = form.name.data
    if len(name)<2:
        name = jid
    query_db("INSERT INTO user_queue(jid, email, receptor_sequence, \
            ligand_sequence, ligand_ss, hide, project_name) VALUES(?,?,?,?,?,?,?)",
            [jid, form.email.data, receptor_seq, ligand_seq, ligand_ss, hide, 
                name], insert=True)

    #generate constraints
    unzpinp = os.path.join(app.config['USERJOB_DIRECTORY']+"/"+jid, "input.pdb")
    r = restrRanges(unzpinp)
    r.parseRanges()
    for e in r.getLabelFormat():
        query_db("INSERT INTO constraints(jid,constraint_definition) VALUES(?,?)", 
                [jid,e],insert = True)
    # TODO kolorowanie wiezow

    return (jid, receptor_seq, ligand_seq, form.name.data,form.email.data)

@app.route('/final_submit', methods=['POST', 'GET'])
def final_submit():
    if request.method == 'POST':
        jid = request.form.get('jid','')
        if jid=='':
            return Response("OJ OJ, nieladnie", status=404,mimetype='text/plain')

        flash('Job submitted. Bookmark this page to check results (usually within \
                24h) if you didn\'t povided e-mail address', 'info')
        query_db("UPDATE user_queue SET status=? WHERE jid=?",['pre_queue',jid], insert=True)
        return redirect(url_for('job_status', jid=jid))
    return Response("HAHAHAahahahakier",status=200,mimetype='text/plain') # tu chyba nikt

def parse_out(q):
    out = []
    for row in q:
        if row['datet']:
            dtt = datetime.fromtimestamp(float(row['datet'])).strftime('%Y-%m-%d %H:%M')
        else:
            dtt = "-"
        l = {'project_name': row['project_name'], 
                'jid': row['jid'], 
                'date': dtt, 
                'status': status_color(row['status'])}

        out.append(l)
    return out

@app.route('/queue', methods=['POST','GET'], defaults={'page':1})
@app.route('/queue/page/<int:page>/', methods=['POST', 'GET'])
def queue_page(page=1):
    before = (page - 1) * app.config['PAGINATION']
    displ_from = 1 + (page - 1) * config['PAGINATION']

    if request.method == 'GET':
        search = request.args.get('q','')
        if search != '':
            flash("Searching results for %s ..." %(search), 'warning')
            q = query_db("SELECT project_name, jid,status, status_date datet \
                    FROM user_queue WHERE project_name LIKE ? OR jid=? ORDER BY \
                    status_date DESC LIMIT ?,?", 
                    ["%"+search+"%", search, before, app.config['PAGINATION']])
            q_all = query_db("SELECT status FROM user_queue WHERE project_name \
                    LIKE ? OR jid=? ORDER BY  status_date DESC", 
                    ["%"+search+"%", search])
            # jesli jest szukanie po nazwie projektu to ukrywanie zadan przestaje miec sens TODO
            out = parse_out(q)
            if len(out)==0:
                flash("Nothing found", "error")
            elif len(out)==1:
                flash("Project found!", "info")
                jid = out[0]['jid']
                return redirect(url_for('job_status', jid=jid))

            return render_template('queue.html', queue = out, page=page, total_rows=len(q_all))


    qall = query_db("SELECT status FROM \
            user_queue WHERE hide=0 AND status!='pending' \
            ORDER BY status_date DESC",[])
    q = query_db("SELECT project_name, jid,status, status_date datet FROM \
            user_queue WHERE hide=0 AND status!='pending' \
            ORDER BY status_date DESC LIMIT ?,?",[before, app.config['PAGINATION']])
    out = parse_out(q)
    # pagination
    count_data = len(qall)
    if page*config['PAGINATION'] < count_data:
        displ_to = page * config['PAGINATION']
    else:
        displ_to = count_data
    

    return render_template('queue.html', queue = out, total_rows = len(qall), page=page)

@app.route('/job/<jid>/')
def job_status(jid):
    system_info = query_db("SELECT ligand_sequence, receptor_sequence, \
            datetime(status_date,'unixepoch') status_date, project_name, \
            status,constraints_scaling_factor FROM  user_queue WHERE jid=?", 
            [jid],one=True)
    constraints = query_db("SELECT constraint_definition,force FROM constraints\
            WHERE jid=?",[jid])
    status = status_color(system_info['status'])
    # dodac kolorowe badgesy do statusu

    return render_template('job_info.html', status = status, constr=constraints, 
            jid=jid, sys=system_info)

@app.route('/_add_const_toDB', methods=['POST', 'GET'])
def user_add_constraints():
    if request.method == 'POST':
        jid = request.form.get('jid','')
        if jid=='':
            return Response("OJ OJ, nieladnie", status=404,mimetype='text/plain')

        constraints = request.form.getlist('constr[]')
        weights = request.form.getlist('constr_w[]')
        scaling_factor =   request.form.get('overall_weight','1.0')
        query_db("DELETE FROM constraints WHERE jid=?", [jid], insert=True)
        query_db("UPDATE user_queue SET constraints_scaling_factor=? WHERE jid=?",
                [scaling_factor, jid], insert=True)

        for r in zip(constraints,weights):
            query_db("INSERT INTO constraints(jid,constraint_definition,force) \
                    VALUES(?,?,?)", [jid,r[0],r[1]], insert = True) 

    return Response("HAHAHAahahahakier",status=200,mimetype='text/plain')

@app.route('/',methods=['GET','POST'])
def index_page():
    form = MyForm()
    if request.method == 'POST':
        if form.validate():
            try:
                jid, rec, lig, nam,email = add_init_data_to_db(form)
                if len(form.name.data)<2:
                    nam = jid
#                flash('<strong>Input data</strong><table class="table table-bordered"><tr><td>\
#                        <strong>Ligand sequence</strong></td> \
#                        <td><strong>Receptor sequence</strong></td> \
#                        <td><strong>Project name</strong></td> </tr><tr> \
#                        <td><span class="sequence">%s</span></td> \
#                        <td><span class="sequence">%s</span></td> \
#                        <td>%s</td> </tr></table>' %(lig,rec,nam),'info')
                return redirect(url_for('index_constraints', jid=jid))
            except:
                flash("Network problem, try again later, contact admin: jamroz(AT)chem.uw.edu.pl ", "error")
                return render_template('index.html', form=form)

        else:
            flash('Something goes wrong. Check errors within data input panel','error')
    return render_template('index.html', form=form)

