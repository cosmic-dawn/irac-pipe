#!/bin/bash
#PBS -S /bin/bash
#PBS -N preTiles_@PID@
#PBS -o setup_tiles.out
#PBS -j oe
#PBS -l nodes=@NODE@:ppn=@NPROC@,walltime=24:00:00
#
#-----------------------------------------------------------------------------
# File:     merge_stars.sh @INFO@
# Purpose:  wrapper for merge_stars.py
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
node=$(hostname)   # NB: compute nodes don't have .iap.fr in name

# check if running via shell or via qsub:
module=setup_tiles

if [[ "$0" =~ "$module" ]]; then
	WRK=$(pwd)
    echo "## This is $module: running as shell script on $node"
    if [[ "${@: -1}" == 'dry' ]]; then dry=1; else dry=0; fi
else
    echo "## This is $module: running via qsub on $node"
	WRK=@WRK@   # data are here
    dry=0
fi

#-----------------------------------------------------------------------------
# Begin work
#-----------------------------------------------------------------------------

mycd $WRK

# Build the command line
comm="python $module.py"

echo " - Work dir is:  $WRK"
echo " - Command is: $comm"
echo " - Starting on $(date) on $(hostname)"
echo " - command line is: "
echo " % $comm"

if [ $dry -eq 1 ]; then
	echo " $module finished in dry mode"; exit 1
fi

# Now do the work
echo ""
echo ">> ==========  Begin python output  ========== "

$comm
echo ">> ==========   End python output   ========== "
echo ""

echo ""
echo "------------------------------------------------------------------"
echo " >>>>  $module finished on $(date) - walltime: $(wt)  <<<<"
echo "------------------------------------------------------------------"
echo ""
exit 0
