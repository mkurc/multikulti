#!/usr/bin/env python
import os
production = False

DIR = os.path.dirname(os.path.realpath(__file__))
PROJECT_DIR = os.path.join(DIR, "playground")

if production:
    ws = "http://212.87.3.12/knotprot/"
else:
    ws = "http://localhost:5000/"

config_remote = {
    'currdir': DIR,
    'webserver_url': ws,
    'secret_key': "23",
    'psipred_path': '/cloud/CABSservices/bin/psipred',
    'userjob_pool_max_cpus': 2,
    'compute_directory': PROJECT_DIR
    }
