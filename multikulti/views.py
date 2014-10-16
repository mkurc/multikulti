#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Michal Jamroz 2014/09
from multikulti import app
from config import config,query_db,unique_id

from flask import render_template, g, url_for, request, jsonify, flash, \
    session, Response, redirect, send_from_directory, send_file
from flask.ext.login import login_required,current_user
from urllib import quote


from flask_wtf import Form
from wtforms import StringField, BooleanField
from wtforms.validators import DataRequired,Length,Email, optional

app.config.update(config)
app.secret_key = \
    'omojatlasikurozwijajsie'

class MyForm(Form):
    name = StringField('Project name', validators=[DataRequired()])
    pdb = StringField('PDB code (required)', validators=[Length(min=3,max=4),DataRequired()])
    email = StringField('E-mail address (optional)', validators = [optional(), Email()])
    show = BooleanField('Do not show my job on the results page', default=False)

@app.route('/job')
def index_jobpage():
    return render_template('page_not_found.html')

@app.route('/',methods=['GET','POST'])
def index_page():
    form = MyForm()
    if request.method == 'POST':
        if form.validate():
            flash('udalo sie','info')
            return redirect(url_for('index_jobpage'))
        else:
            flash('niestety chujowo','error')
    return render_template('index.html', form=form)

