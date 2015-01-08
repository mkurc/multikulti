#!/usr/bin/env bash
#poprawia po bbq. NAdpisuje plik wejsciowy plikiem poprawionym

model=$1
gmx pdb2gmx -f $model  -heavyh -dist 0.5 -ff charmm27 -water none
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
ns_type= simple
coulombtype= cut-off
rcoulomb= 0.5
rvdw= 0.5
constraints= none
lincs-order             = 8
constraint-algorithm = LINCS
pbc= xyz
EOF

gmx grompp -f minim.mdp -c conf.gro -p topol.top -o em.tpr -maxwarn 5
gmx mdrun -s em.tpr -o tr.pdb -c mini.pdb
echo 2 | gmx trjconv  -f mini.pdb -s em.tpr -o BLBLBL.pdb  -pbc nojump
mv BLBLBL.pdb $model
rm mdout.mdp tr.pdb.trr ener.edr mini.pdb topol* posre* conf.gro em.tpr minim.mdp
mv md.log $model".md.log"
