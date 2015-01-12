#!/bin/bash

#poprawia po bbq. NAdpisuje plik wejsciowy plikiem poprawionym
source /usr/local/gromacs/bin/GMXRC.bash
model=$1
echo "jestem jestem" $model

cat << EOF > minim.mdp
cpp= /lib/cpp; Preprocessor
integrator= steep
emtol= 1.0
nsteps= 15000
nstenergy= 10000
energygrps= System
nbfgscorr = 100
lincs-iter = 1000
lincs-warnangle = 90
ns_type = simple
coulombtype= cut-off
constraints= none
lincs-order = 8
constraint-algorithm = LINCS
pbc= xyz
EOF
export PATH=$PATH:/usr/local/gromacs/bin/
pdb2gmx -f $model  -heavyh -dist 0.5 -ff charmm27 -water none
grompp -f minim.mdp -c conf.gro -p topol.top -o em.tpr -maxwarn 5
mdrun -s em.tpr -o tr.pdb -c mini.pdb -nt 1
echo 2 | trjconv  -f mini.pdb -s em.tpr -o BLBLBL.pdb  -pbc nojump
mv BLBLBL.pdb $model
rm mdout.mdp tr.pdb.trr ener.edr mini.pdb topol* posre* conf.gro em.tpr minim.mdp md.log
#mv md.log $model".md.log"
