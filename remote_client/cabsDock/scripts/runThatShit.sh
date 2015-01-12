#! /bin/bash

export cabsHome=$(cd `dirname "${BASH_SOURCE[0]}"`/.. && pwd)
export cabsBin=$cabsHome/bin
export scripts=$cabsHome/scripts
export dssp=$cabsBin/dssp
export bioshell=$cabsHome/data/bioshell.bioinformatics-2.2.jar
export LC_ALL="C"

#pdb=$1
#ligSeq=$2
#rest=$3

pdb="input.pdb"
ligSeq="ligand.txt"
rest="restr.txt"
nCycUser=$1

#=============================PARAMETRY================================

nSteps=50	# liczba cykli MC
nCycle=$nCycUser	# odstep pomiedzy klatkami
T1=2.0		# temp startowa
T2=1.0		# temp koncowa
nReps=10	# liczba replik
separation=20	# odleglosc pomiedzy powierzchnia receptora i sfera
		# na ktorej poczatkowo rozmieszczone sa repliki liganda
dtemp=0.5   # odstep pomiedzy replikami [temperatura]

# do klastrowania
clMinN=10	# minimalny rozmiar klastra
clMaxD=5	# maksymalna odleglosc miedzy elementami w klastrze
clCount=10	# maksymalna liczba klastrow
# do filtrowania
fCount=1000	# liczba struktur po filtrowaniu

#======================================================================

# receptor

recCA=`mktemp -u -p .`
recSEQ=`mktemp -u -p .`
$scripts/ss.sh $pdb | $scripts/getCA.sh >$recCA
$scripts/pdbToSeq.sh $recCA >$recSEQ
fRest=`awk 'NR==1{print $NF}' $rest`

# dziury

tempGaps=`mktemp -u -p .`
$scripts/detectGaps.sh $recCA >$tempGaps
if [ -s $tempGaps ]; then
 temp=`mktemp -u -p .`
 $scripts/fixGaps.sh $recCA $tempGaps >$temp
 mv $temp $recCA
fi

# z inputu

ligLen=`wc -l $ligSeq | awk '{print $1}'`
recChID=`awk '/^(ATOM|HETATM)/{print substr($0,22,1)}' $recCA | sort | uniq | tr -d '\n'`

# zamien seq na format cabsa

tempLigSeq=`mktemp -u -p .`

awk '

function aaLong(_aaName, n){
 n=index(_aaShortNames,_aaName);
 if(n) return substr(_aaLongNames,n*3-2,3);
 else return "UNK";
}

function dsspToSeq(_ss){
 if(_ss=="H" || _ss=="G" || _ss=="I") return 2;
 else if(_ss=="T") return 3;
 else if(_ss=="B" || _ss=="E") return 4;
 else return 1;
}

BEGIN{
 _aaLongNames="ALAASXCYSASPGLUPHEGLYHISILEXLELYSLEUMETASNHOHPROGLNARGSERTHRUNKVALTRPXAATYRGLX";
 _aaShortNames="ABCDEFGHIJKLMNOPQRSTUVWXYZ";
}

{print aaLong($1),dsspToSeq(substr($2,1,1))}' $ligSeq > $tempLigSeq

# zrob szablon liganda

tempLigCa=`mktemp -u -p .`

awk -v donts=$recChID '

BEGIN{
 chID="A";
 allLetters="ABCDEFGHIJKLMNOPQRSTUVWXYZ";
 while(index(donts,chID)){
  n=index(allLetters,chID);
  chID=substr(allLetters,n+1,1);
 }
}

{
 printf "ATOM%7i  CA  %s %c%4i%12.3f%8.3f%8.3f%6.2f%6.2f\n",++m,$1,chID,m,0,0,0,$2,1;
}' $tempLigSeq >$tempLigCa

ligChID=`awk '/^ATOM/{print substr($0,22,1);exit}' $tempLigCa`

# zrob SEQ

{
 cat $recSEQ
 $scripts/pdbToSeq.sh $tempLigCa
} >SEQ

# zrob startowe pdb

recDim=`$cabsBin/restr -i=$pdb -g=1 | sort -n -k5 | tail -1 | awk '{print $5}'`
recCOM=`$scripts/centOfMass.sh $pdb`
sphere=`echo $recDim $separation | awk '{print 0.5*$1+$2}'`

$scripts/getRandLigands.sh $tempLigCa $nReps $cabsHome/data/1000ligands.pdb | $scripts/randomize.sh /dev/stdin $sphere | $scripts/movePdb.sh /dev/stdin $recCOM | awk -v fnm=$recCA '

/^MODEL/{
 print $0;
 system("cat "fnm);
}

!/^MODEL/{
 print $0;
}' >start.pdb

# zrob FCHAINS

$cabsBin/natcaf -i=start.pdb >FCHAINS

# zrob restr
# tu jeszcze pisze
# roboczo zeby sprawdzic czy dziala nie uwzlednia wiezow od uzytkownika

$cabsBin/restr -i=$recCA -min=5.0 -max=10.0 -r -g=5 >RESTR

# zrob INP

$scripts/makeINP.sh $nSteps $nCycle $T1 $T2 $fRest $dtemp >INP

# cabs

ln -s -f $cabsHome/params/* .
$cabsBin/dock

# dzielenie replik i nakladanie receptora

$scripts/splitReplicas.sh TRAF
tempAli=`mktemp -u -p .`
$scripts/getModels.sh start.pdb 1 | $cabsBin/align -p1=$recCA -p2=/dev/stdin >$tempAli
mkdir -p TRAFS

for((i=1;i<=$nReps;++i)); do
 tra=replica_$i".pdb"
 $scripts/trafToPdb.sh TRAF_$i SEQ | $cabsBin/rmsd -t=$recCA -q=/dev/stdin -a=$tempAli -o=TRAFS/$tra >/dev/null
 rm TRAF_$i
done

# klastrowanie
tempTra=`mktemp -u -p .`
tempClust=`mktemp -u -p .`
$scripts/lowEnergyFrames.sh TRAF $fCount | $scripts/trafToPdb.sh /dev/stdin SEQ | $cabsBin/rmsd -t=$recCA -q=/dev/stdin -a=$tempAli -o=$tempTra >/dev/null
$scripts/getChains.sh $tempTra $ligChID | $scripts/rmsd-nofit.sh /dev/stdin | java -classpath $bioshell apps.Clust -id=/dev/stdin -n=`awk '/^MODEL/{n++}END{print n}' $tempTra` -complete -min_size=$clMinN -max_dist=$clMaxD -oc=/dev/stdout | $scripts/clustDens.sh /dev/stdin | head -$clCount >$tempClust
$scripts/getClusters.sh $tempClust $tempTra

mkdir -p CLUST MODELS
rm -f CLUST/* MODELS/*

# odbudowa

tmpMdl=`mktemp -u -p .`
for i in cluster_*.pdb; do
 mdl=MODELS/model${i#cluster}
 $scripts/getMedoid.sh $i >$tmpMdl
 echo "hoh"
 $scripts/bbb.sh $tmpMdl | $scripts/scw.sh /dev/stdin >$mdl
 mv $i CLUST
done

for i in CLUST MODELS TRAFS; do
    echo $i
  cd $i
  for j in *.pdb; do

      if [ "$i" == "MODELS" ]
      then
        bash $scripts/optGro.sh $j >> ../outs_gromacs
      fi

      gzip $j
  done
  cd -
done


rm tmp.* SIDECENT QUASI3S CENTRO R1* ACHAINS_NEW OUT
