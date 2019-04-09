#!/bin/bash
#PBS -S /bin/bash
#PBS -N mkTile_@JOB@_@PID@
#PBS -o make_tile_@JOB@.out
#PBS -j oe
#PBS -l nodes=1:ppn=11,walltime=48:00:00
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
procTmpDir=/scratch/tmpfiles_tile_$jobNo             # to be deleted if all ok

# Build the command line
comm="python $module.py $jobNo"

echo " - Work dir is:  $WRK"
echo " - Command is: $comm"
echo " - Starting on $(date) on $(hostname)"
echo " - command line is: "
echo " % $comm"

if [ $dry -eq 1 ]; then
	echo ">> $module finished in dry mode"; exit 1
fi

# Now do the work
echo ""
echo ">> ==========  Begin python output  ========== "

$comm
echo ">> ==========   End python output   ========== "
echo ""

# check that the tile is built
pars=$WRK/supermopex.py
odir=$(grep '^OutputDIR '   $pars | cut -d\' -f2 | tr -d \/)
PID=$(grep  '^PIDname '     $pars | cut -d\' -f2)
tlf=$(grep '^TileListFile ' $pars | cut -d\' -f2) #; echo "$PID, $tlf"; exit
tlf=$odir/${PID}$tlf                              #; echo "$PID, $tlf"

nline=$(($jobNo+5))  # line number for job
outf=$(sed "${nline}q;d" $tlf | awk '{printf "'$PID'.irac.tile.%s.%s.mosaic.fits",$2,$3}')
outp=$(sed "${nline}q;d" $tlf | awk '{printf "'$PID'.irac.tile.%s.%s.*mosaic*.fits",$2,$3}')
np=$(ls -l $odir/$outp | wc -l)   # number of products build - should be 6

if [ $np -eq 6 ]; then 
	echo ">> Job $jobNo Done: built $odir/$outf and partners ... Good job!!"
	echo ">> Deleting process temp dir $procTmpDir"
	rm -rf $procTmpDir
else
	echo ">> PROBLEM: Job $jobNo  built only $np products: "
	echo ">> -- kept process temp dir $procTmpDir on $node"
	ls -l $odir/$outp 
fi

echo ""
echo "------------------------------------------------------------------"
echo " >>>>  $module $jobNo finished on $(date) - walltime: $(wt)  <<<<"
echo "------------------------------------------------------------------"
echo ""
exit 0
