#!/usr/bin/env python

production = False

if production:
    ws = "http://212.87.3.12/knotprot/"
    compprefix = "/home/mjamroz/"
else:
    ws = "http://localhost:5000/"
    compprefix = "/tmp"

config_remote = {
        'webserver_url': ws,                                                                        # must ends with /  
        'secret_key': "23",                                                                         # must be identical like on remote/webpage
        'userjob_pool_max_cpus': 2,                                                                 # set max parallel execution of user jobs NOTE if max_cpus and timeout is not correctly estimated, it may result in high server load. Probably better to move into sge queue
        'compute_directory': compprefix+"computational_remote_server/playground" # remote server working directory
        }
