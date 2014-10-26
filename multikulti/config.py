#!/usr/bin/python
# -*- coding: utf-8 -*-
# Michal Jamroz, 2014, jamroz@chem.uw.edu.pl

from flask import g
from os import path
import sys
import bz2
import gzip
import uuid
import re
import sqlite3

production=True # production = paths on ptb2, False = discordia


prefix = path.dirname(path.realpath(__file__))+"/"


config = \
    dict(DATABASE=prefix+'database-full.db',
         CACHE=prefix+'cache/',
         STATIC=prefix+'static/',
         ALLOWED_EXTENSIONS = ['pdb','PDB'],
         UPLOAD_FOLDER=prefix+'upload/',
         USERJOB_DIRECTORY=prefix+'computations/',
         REMOTE_SERVER_SECRET_KEY = "23",
         REMOTE_SERVER_IP = ["127.0.0.1"],
         DEBUG=True, 
         DEFAULT_MAIL_SENDER="biocomp@chem.uw.edu.pl",                      # FROM field in sent mail
         MAX_CONTENT_LENGTH=25 * 1024 * 1024, # 25MB
         #ADMIN_EMAILS=["michal@yerbamate.com.pl","jsulkows@gmail.com"], # admin mails. Send errors, info about new knots, etc.
         #SMTP_SERVER = "localhost",             # if authorization needed, modify send_mail() method
         PRODUCTION = False,
         PAGINATION=3)                         # # of records on /browse/ page


#def send_mail(to='', subject="Test",body="Body"):
#    global config
#    if to=='':
#        db = sqlite3.connect(config['MAILS_DATABASE'])
#        cur = db.cursor()
#        cur.execute('INSERT INTO mails(subject,body,date) values (?,?,datetime())',[subject, body])
#        db.commit()
#        db.close()
#
#    else: # mail to user - send immadietly
#        server = smtplib.SMTP(config['SMTP_SERVER'],25)
#        fromaddr = config['DEFAULT_MAIL_SENDER']
#        if type(to) is list:
#            for tomail in to:
#                msg = MIMEText(body)
#                msg['Subject'] = "[KnotProt] "+subject
#                msg['From'] = fromaddr
#                msg['To'] = tomail
#                server.sendmail(fromaddr, tomail, msg.as_string() )
#        else:
#            msg = MIMEText(body)
#            msg['Subject'] = "[KnotProt] "+subject
#            msg['From'] = fromaddr
#            msg['To'] = to
#            server.sendmail(fromaddr, to, msg.as_string() )
#
#       static server.quit()

def gunzip(filename):
    gunzipped = ".".join(filename.split(".")[:-1])
    with  open(gunzipped, 'w') as f_out:
        with gzip.open(filename, 'rb') as f_in:
            f_out.writelines(f_in)

def unique_id():
    return hex(uuid.uuid4().time)[2:-1]

def regexp(expr, item):
    r = re.compile(expr)
    return r.match(item) is not None


def connect_db():
    """Connects to the specific database."""

    rv = sqlite3.connect(config['DATABASE'])
    rv.create_function('regexp', 2, regexp)
    rv.row_factory = sqlite3.Row
    return rv

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """

    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

def query_db(query, args=(), one=False,insert=False):
    mydb = get_db()
    cur = mydb.execute(query,args)
    if insert:
        g.sqlite_db.commit()
        cur.close()
        return cur.lastrowid
    else:
        rv = cur.fetchall()
        cur.close()
        return ((rv[0] if rv else None) if one else rv)

