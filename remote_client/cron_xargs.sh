#!/usr/bin/env bash
DIR="$( cd "$( dirname "$0" )" && pwd )"
python $DIR/listJobs.py |xargs -n1 -P50  python $DIR/runJob.py 


