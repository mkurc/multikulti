#!/usr/bin/env bash
#$ -cwd 
#$ -q web.q
#$ -o out
#$ -e err
#$ -r y
#$ -S /bin/bash
newgrp cabsdock << END
python /cloud/CABSservices/CABSDOCK/runJob_unbound.py $1
END
