#!/usr/bin/python
# -*- coding: utf-8 -*-
# Michal Jamroz, 2014, jamroz@chem.uw.edu.pl

from flask import g
from os import path
import gzip
import uuid
import re
from sys import maxint
import MySQLdb
import MySQLdb.cursors
import smtplib
from email.MIMEText import MIMEText


prefix = path.dirname(path.realpath(__file__))+"/"


config = \
    dict(CACHE=prefix+'cache/',
         STATIC=prefix+'static/',
         ALLOWED_EXTENSIONS=['pdb', 'PDB'],
         UPLOAD_FOLDER=prefix+'upload/',
         USERJOB_DIRECTORY=prefix+'computations/',
         DELETE_USER_JOBS_AFTER="90",
         EXAMPLE_JOB = '6795ce3b55ab1fa', # last job in benchmark
         MYSQL_USER='cabsdock',
         MYSQL_PASS='cabsdock123',
         MYSQL_DATA='cabsdock',
         REMOTE_SERVER_SECRET_KEY="23",
	 REMOTE_SERVER_IP = ["127.0.0.1", "212.87.3.12", "212.87.3.11"],
         DEBUG=True,
         DEFAULT_MAIL_SENDER="biocomp@chem.uw.edu.pl",  # FROM field
         MAX_CONTENT_LENGTH=625 * 1024 * 1024,  # 225MB
         ADMIN_EMAILS=["michal@yerbamate.com.pl",
                       "sebastian.kmiecik@gmail.com",
                       "mkurcinski@gmail.com"],
         # admin mails. Send errors, info about new knots, etc.
         SMTP_SERVER="localhost",
         # if authorization needed, modify send_mail() method
         PRODUCTION=True,
         PAGINATION=25)                         # # of records on /browse/ page


def send_mail(to='', subject="Test", body="Body"):
    global config
    if to == '':
        send_mail(to=config['ADMIN_EMAILS'], subject=subject, body=body)
    else:  # mail to user - send immadietly
        server = smtplib.SMTP(config['SMTP_SERVER'], 25)
        fromaddr = config['DEFAULT_MAIL_SENDER']
        if type(to) is list:
            for tomail in to:
                msg = MIMEText(body)
                msg['Subject'] = "[CABSdock] "+subject
                msg['From'] = fromaddr
                msg['To'] = tomail
                server.sendmail(fromaddr, tomail, msg.as_string())
        else:
            msg = MIMEText(body)
            msg['Subject'] = "[CABSdock] "+subject
            msg['From'] = fromaddr
            msg['To'] = to
            server.sendmail(fromaddr, to, msg.as_string())

        server.quit()


def gunzip(filename):
    gunzipped = ".".join(filename.split(".")[:-1])
    with open(gunzipped, 'w') as f_out:
        with gzip.open(filename, 'rb') as f_in:
            f_out.writelines(f_in)


def unique_id():
    return hex(uuid.uuid4().time)[2:-1]


def regexp(expr, item):
    r = re.compile(expr)
    return r.match(item) is not None


def connect_db():
    """Connects to the specific database."""
    rv = MySQLdb.connect(host="localhost", user=config['MYSQL_USER'], 
                         cursorclass=MySQLdb.cursors.DictCursor,
                         passwd=config['MYSQL_PASS'], 
                         db=config['MYSQL_DATA'], 
                         charset='utf8')
    return rv


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """

    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


def query_db(query, args=(), one=False, insert=False):
    mydb = get_db()
    cur = mydb.cursor()
    cur.execute(query, args)
    if insert:
        mydb.commit()
        cur.close()
        return cur.lastrowid
    else:
        rv = cur.fetchall()
        cur.close()
        return ((rv[0] if rv else None) if one else rv)


# copied from http://nedbatchelder.com/blog/200712.html#e20071211T054956
def tryint(s):
    try:
        return int(s)
    except:
        return s
    
def alphanum_key(s):
    """ Turn a string into a list of string and number chunks.
        "z23a" -> ["z", 23, "a"]
    """
    return [ tryint(c) for c in re.split('([0-9]+)', s) ]
