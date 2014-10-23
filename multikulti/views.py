#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Michal Jamroz 2014/09

import uuid
import os
import urllib2
from StringIO import StringIO
import gzip

from multikulti import app
from config import config,query_db,unique_id

from flask import render_template, g, url_for, request, jsonify, flash, \
    session, Response, redirect, send_from_directory, send_file
from flask.ext.login import login_required,current_user
from urllib import quote

from flask.ext.uploads import UploadSet, IMAGES

from flask_wtf import Form
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, BooleanField, TextAreaField, HiddenField
from wtforms.validators import DataRequired,Length,Email, optional, ValidationError



from multikulti_modules.fetchPDBinfo import getCoordinates, fetchPDBinfo
from multikulti_modules.parsePDB import  PdbParser
################################################################################

app.config.update(config)
app.secret_key = 'multikultitosmierdzcywilizacjieurpejzkij'
input_pdb = UploadSet('inputpdbs', extensions = app.config['ALLOWED_EXTENSIONS'],\
        default_dest = app.config['UPLOAD_FOLDER']) 
@app.route('/compute_static/<jobid>/input.pdb.gz')
def compute_static(jobid):
    return send_from_directory(app.config['USERJOB_DIRECTORY']+"/"+jobid, "input.pdb.gz") # TODO co jesli filename bedzie do nadrzednych      



def unique_id():
    return hex(uuid.uuid4().time)[2:-1]



def sequence_validator(form, field):
    allowed_seq = ['A', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'K', 'L', 'M', 'N',\
            'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'Y']
    d = ''.join(field.data.replace(' ','').split()).upper() # TODO poprawic
    for letter in d:
        if letter not in allowed_seq:
            raise ValidationError('Sequence contains non-standard aminoacid symbol: %s' % (letter) )

def ss_validator(form, field):
    allowed_seq = ['C', 'H', 'E']
    d = ''.join(field.data.replace(' ','').split()).upper()
    for letter in d:
        if letter not in allowed_seq:
            raise ValidationError('Secondary structure contains non-standard \
                    symbol: %s. <br><small>Allowed H - helix, E - extended/beta, C - coil.</small>' % (letter) )
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
                    raise ValidationError('Non-standard residue in the receptor structure')
            if len(p.getBody()) < 16:
                raise ValidationError('File without chain or chain shorter than 4 residues')
            if len(missing)>0:
                raise ValidationError('Missing atoms around residue(s): %s. Server accepts only continuous chains.' % missing)
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
            raise ValidationError('Missing atoms around residue(s): %s. Server accepts only continuous chains.' % missing)

def pdb_input_code_validator(form, field):
    if len(field.data)!=4 and not form.receptor_file.data.filename:
        raise ValidationError('Receptor code must be 4-letter (2PCY). Leave empty only if PDB file is provided')
    if not form.pdb_receptor.data and not form.receptor_file.data:
        raise ValidationError('Receptor PDB code or PDB file is required')

class MyForm(Form):
    name = StringField('Project name', validators=[Length(min=4,max=50),optional()])
    pdb_receptor = StringField('Remote PDB file', \
            validators=[pdb_input_code_validator, structure_pdb_validator])
    receptor_file = FileField('Local PDB file', \
            validators=[FileAllowed(input_pdb.extensions, 'PDB file format only!'), pdb_input_validator])
    ligand_seq = TextAreaField('Ligand sequence', \
            validators=[Length(min=3,max=60),DataRequired(),sequence_validator])
    ligand_ss = TextAreaField('Ligand secondary structure', \
            validators=[Length(min=3,max=60),optional(),ss_validator])
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
    di ={'1.0': '<option value="1.0">default</option><option value="0.25">light</option><option value="5.0">strong</option>',
            '0.25': '<option value="0.25">light</option><option value="1.0">default</option><option value="5.0">strong</option>',
            '5.0': '<option value="5.0">strong</option><option value="1.0">default</option><option value="0.25">light</option>'}

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

    elif form.pdb_receptor.data:
        buraki =  urllib2.urlopen('http://www.rcsb.org/pdb/files/'+form.pdb_receptor.data+'.pdb.gz')
        b2 = buraki.read()
        ft = StringIO(b2)
        with gzip.GzipFile(fileobj=ft,mode="rb") as f:
            p = PdbParser(f)
            receptor_seq =  p.getSequence()
            p.savePdbFile(dest_file)
        buraki.close()

    query_db("INSERT INTO user_queue(jid, email, receptor_sequence, ligand_sequence, ligand_ss, \
            hide, project_name) VALUES(?,?,?,?,?,?,?)",\
            [jid, form.email.data, receptor_seq, ligand_seq, \
            ligand_ss, hide, form.name.data], insert=True)
    return (jid, receptor_seq, ligand_seq, form.name.data,form.email.data)

@app.route('/_add_const_toDB', methods=['POST', 'GET'])
def user_add_constraints():
    if request.method == 'POST':
        jid = request.form.get('jid','')
        if jid=='':
            return Response("OJ OJ", status=404,mimetype='text/plain')

        constraints = request.form.getlist('constr[]')
        weights = request.form.getlist('constr_w[]')
        scaling_factor =   request.form.get('overall_weight','1.0')
        query_db("DELETE FROM constraints WHERE jid=?", [jid], insert=True)
        query_db("UPDATE user_queue SET constraints_scaling_factor=? WHERE jid=?",
                [scaling_factor, jid], insert=True)

        for r in zip(constraints,weights):
            query_db("INSERT INTO constraints(jid,constraint_definition,force) \
                    VALUES(?,?,?)", [jid,r[0],r[1]], insert = True) 
            print r[0], r[1]
        print scaling_factor, jid

    return Response("HAHAHAahahahakier",status=200,mimetype='text/plain')

@app.route('/',methods=['GET','POST'])
def index_page():
    form = MyForm()
    if request.method == 'POST':
        if form.validate():
            jid, rec, lig, nam,email = add_init_data_to_db(form)
            flash('<strong>Input data:</strong> Ligand sequence: %s; Receptor \
                    sequence: %s; Project name: %s' %(lig,rec,nam),'info')
            return redirect(url_for('index_constraints', jid=jid))
        else:
            flash('Something goes wrong. Check errors within data input panel','error')
    return render_template('index.html', form=form)

