#!/usr/bin/env bash
DIR="$( cd "$( dirname "$0" )" && pwd )"
newgrp cabsdock << END
python $DIR/listJobs.py |xargs -n1 -P50  python $DIR/runJob_unbound.py
END
#runJob.py 


