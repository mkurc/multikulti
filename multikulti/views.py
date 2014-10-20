#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Michal Jamroz 2014/09

import uuid

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
################################################################################

app.config.update(config)
app.secret_key = 'multikultitosmierdzcywilizacjieurpejzkij'
input_pdb = UploadSet('inputpdbs', extensions = app.config['ALLOWED_EXTENSIONS'],\
        default_dest = app.config['UPLOAD_FOLDER']) 

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
    if len(field.data)==4:
        pdb = fetchPDBinfo(field.data)
        first_chain = pdb.getFirstChain()
        pdb = fetchPDBinfo(field.data, chain=first_chain)
        flash('Chain not provided, using chain %s from %s' % (first_chain,field.data), 'info')
    elif len(field.data)==6:
        d = field.data.split(":")
        chain = d[1]
        pdbcode = d[0]
        pdb = fetchPDBinfo(pdbcode)
        if chain not in pdb.getChainIndexes():
            raise ValidationError('Provided chain (%s) seems to not exists in \
                    the structure (%s)' %(chain,pdbcode) )
        else:
            pdb = fetchPDBinfo(pdbcode,chain)
    else:
        raise ValidationError('Receptor structure is missing')

    missing = pdb.missing
    if len(missing)!=0:
        raise ValidationError('Chain breaks within structure: %s. \
                Provide continuous chain.' % ( ', '.join(missing)))

def pdb_input_validator(form, field):
    if not form.pdb_receptor.data and not form.receptor_file.data:
        raise ValidationError('PDB code or PDB file is required')
def pdb_input_code_validator(form, field):
    if len(field.data)>5 and len(field.data)<3 and not form.receptor_file.data:
        raise ValidationError('Receptor code must be 4-letter (2PCY) or 6-letter\
                (2PCY:A). Leave empty only if PDB file is provided')
    if not form.pdb_receptor.data and not form.receptor_file.data:
        raise ValidationError('Receptor PDB code or PDB file is required')

class MyForm(Form):
    print input_pdb.extensions
    name = StringField('Project name', validators=[Length(min=4,max=50),optional()])
    pdb_receptor = StringField('PDB code', \
            validators=[pdb_input_code_validator, structure_pdb_validator])
    receptor_file = FileField('OR PDB file', \
            validators=[FileAllowed(input_pdb.extensions, 'PDB file format only!'), pdb_input_validator])
    ligand_seq = TextAreaField('Ligand sequence', \
            validators=[Length(min=3,max=60),DataRequired(),sequence_validator])
    ligand_ss = TextAreaField('Ligand secondary structure', \
            validators=[Length(min=3,max=60),optional(),ss_validator])
    email = StringField('E-mail address', 
            validators = [optional(), Email()])
    show = BooleanField('Do not show my job on the results page', default=False)
    jid = HiddenField(default=unique_id())

@app.route('/add_constraints')
def index_constraints():
    return render_template('page_not_found.html')

def add_init_data_to_db(form):
    if form.show.data:
        hide = 1
    else:
        hide = 0
    ligand_seq = ''.join(form.ligand_seq.data.upper().replace(' ','').split())
    ligand_ss = ''.join(form.ligand_ss.data.upper().replace(' ','').split())
    query_db("INSERT INTO user_queue(jid, email, ligand_sequence, ligand_ss, \
            hide, project_name) VALUES(?,?,?,?,?,?)",\
            [form.jid.data, form.email.data, ligand_seq, \
            ligand_ss, hide, form.name.data], insert=True)

@app.route('/',methods=['GET','POST'])
def index_page():
    print app.config['DATABASE']
    form = MyForm()
    if request.method == 'POST':
        if form.validate():
            flash('udalo sie','info')
            add_init_data_to_db(form)
            return redirect(url_for('index_constraints'))
        else:
            flash('niestety, chujowo','error')
    return render_template('index.html', form=form)

