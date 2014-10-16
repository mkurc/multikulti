#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask#jsonify,request
from flask.ext.babel import Babel

app = Flask(__name__)
babel = Babel(app)
@babel.localeselector
def get_locale():
#    return g.get('current_lang', 'en')
    return 'pl'
import multikulti.views
import multikulti.viewsutils
