#!/bin/bash
#PBS -S /bin/bash
#PBS -N mkTile_@JOB@_@PID@
#PBS -o make_tile_@JOB@.out
#PBS -j oe
#PBS -l nodes=1:ppn=7,walltime=32:00:00
#
#-----------------------------------------------------------------------------
# File:     make_tile.sh @INFO@
# Purpose:  wrapper for make_tile.py
#-----------------------------------------------------------------------------
set -u 

ec()  { echo    "$(date "+[%d.%h.%y %T"]) $1 " ; } 
ecn() { echo -n "$(date "+[%d.%h.%y %T"]) $1 " ; } 
mycd() { if [ -d $1 ]; then \cd $1; echo " --> $PWD"; 
    else echo "!! ERROR: $1 does not exit ... quitting"; exit 5; fi; }

wt() { echo "$(date "+%s.%N") $bdate" | \
	awk '{printf "%0.2f hrs\n", ($1-$2)/3600}'; }  # wall time

# load needed softs and set paths

module () {  eval $(/usr/bin/modulecmd bash $*); }
module purge ; module load intelpython/3   mopex 

mexec=$(which mosaic.pl | cut -d\/ -f1-4)

#-----------------------------------------------------------------------------

bdate=$(date "+%s.%N")       # start time/date

# check if running via shell or via qsub:
module=make_tile
node=$(hostname)   # NB: compute nodes don't have .iap.fr in name

if [[ "$0" =~ "$module" ]]; then
	WRK=$(pwd)
    echo "## This is $module: running as shell script on $node"
    if [ $# -eq 0 ]; then 
    	echo "ERROR: Must give a job nomber"
    	exit 5
    else
    	if [ $1 == 'dry' ]; then echo "ERROR: Must give a job number"
    		exit 5
    	else
    		jobNo=$1
    	fi
    fi
    if [[ "${@: -1}" == 'dry' ]]; then dry=1; else dry=0; fi
else
    echo "## This is $module: running via qsub on $node"
	WRK=@WRK@   # data are here
	jobNo=@JOB@
    dry=0
fi

#-----------------------------------------------------------------------------
# Begin work
#-----------------------------------------------------------------------------

mycd $WRK

# temp dir for current proces 
pars=$WRK/supermopex.py
odir=$(grep '^OutputDIR '   $pars | cut -d\' -f2 | tr -d \/)
PID=$(grep  '^PIDname '     $pars | cut -d\' -f2)

# dir on processing node for temp data ... to be deleted at end if all outputs produced
if [[ $node == 'n04' ]] || [[ $node == 'n07' ]] || [[ $node == 'n08' ]] || [[ $node == 'n09' ]]; then 
	procTmpDir=/${node}data/tmpdir_${PID}_tile_j$jobNo
else
	procTmpDir=/scratch$(echo $node | tr -d n)/tmpdir_${PID}_tile_j$jobNo
fi

# Build the command line
comm="python $module.py $jobNo"

echo " - Work dir is:      $WRK"
echo " - Command is:       $comm"
echo " - mosaic.pl from:   $mexec"
echo " - Process temp dir: $procTmpDir "
echo " - Start on $(date) on $node"

if [ $dry -eq 1 ]; then
	echo ">> $module finished in dry mode"; exit 1
fi

# Now do the work
echo ""
echo ">> ==========  Begin python output  ========== "
echo ""

$comm
echo ""
echo ">> ==========   End python output   ========== "
echo ""

# check that the tile is built
tlf=$(grep '^TileListFile ' $pars | cut -d\' -f2) #; echo "$PID, $tlf"; exit
tlf=${odir}/${PID}$tlf                            #; echo "$PID, $tlf"

nline=$(($jobNo+5))  # line number for job
outf=$(sed "${nline}q;d" $tlf | awk '{printf "'$PID'.irac.tile.%s.%s.mosaic.fits",$2,$3}')
outp=$(sed "${nline}q;d" $tlf | awk '{printf "'$PID'.irac.tile.%s.%s.*mosaic*.fits",$2,$3}')

#mc=$(grep ^run_median_mosaic cdf/tile_par.nl | cut -c21)  # chk if median_mosaic was done
#if [ $mc -eq 1 ]; then nexp=6; else nexp=4; fi  # ... should be 4 or 6 
np=$(ls -l $odir/$outp | wc -l)  # number of products built ...
nexp=6

if [ $np -eq $nexp ]; then 
	echo ">> Job $jobNo Done: built $np $odir/$outf and partners ... Good job!!"
	echo ">> Deleting process temp dir $procTmpDir"
	rm -rf $procTmpDir
else
	echo ">> PROBLEM: Job $jobNo  built only $np products of $nexp expected: "
	echo ">> -- kept process temp dir $procTmpDir on $node"
	ls -lh $odir/$outp 
fi

echo ""
echo "------------------------------------------------------------------"
echo " >>>>  $module $jobNo finished on $(date) - walltime: $(wt)  <<<<"
echo "------------------------------------------------------------------"
echo ""
exit 0

echo "## Some diagnostic info ...."
ls -lh $procTmpDir/Coadd-mosaic/*.fits 
ls -lh $procTmpDir/Combine-mosaic/*.fits 
ls -lh $odir/$outp

grep ^${mexec} make_tile_${jobNo}.log | tr -s \  | cut -d\  -f1-4 | uniq  > test.stp
grep "^System Exit" make_tile_${jobNo}.log | uniq >> test.stp
echo "# steps done: $(grep mopex test.stp | wc -l)  $(grep Exit test.stp | wc -l)"
grep 64 test.stp
cp test.log test_$node.log
cp test.stp test_$node.stp

exit 0
