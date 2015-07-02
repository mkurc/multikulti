#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask

app = Flask(__name__)
import multikulti.views
import multikulti.viewsutils
import multikulti.client_listener
import multikulti.rest
