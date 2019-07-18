#!/bin/bash
#PBS -S /bin/bash
#PBS -N mos_ch@CHAN@_@PID@
#PBS -o build_mosaic_ch@CHAN@.out
#PBS -j oe
#PBS -l nodes=1:ppn=@PPN@,walltime=@WTIME@
#
#-----------------------------------------------------------------------------
# File:     build_mosaic.sh @INFO@
# Purpose:  wrapper for build_mosaic.py
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
module purge ; module load intelpython/3-2019.4   mopex 

#-----------------------------------------------------------------------------

bdate=$(date "+%s.%N")       # start time/date
node=$(hostname)   # NB: compute nodes don't have .iap.fr in name

# check if running via shell or via qsub:
module=build_mosaics

if [[ "$0" =~ "$module" ]]; then
    WRK=$(pwd)
    echo "## This is ${module}.sh: running as shell script on $node"
    if [[ "${@: -1}" == 'dry' ]]; then dry=1; else dry=0; fi
else
    echo "## This is ${module}.sh: running via qsub on $node"
    WRK=@WRK@   # data are here
	chan=@CHAN@
    dry=0
fi

#-----------------------------------------------------------------------------
# Begin work
#-----------------------------------------------------------------------------

mycd $WRK
Nthred=$(grep '^Nthred' supermopex.py | tr -s ' ' | cut -d\  -f3)

# Build the command line
comm="python make_mosaics_function.py @CHAN@"

echo " - Work dir is:  $WRK"
echo " - Starting on $(date) on $(hostname) with $Nthred threads"
echo " - command line is: "
echo " % $comm"

if [ $dry -eq 1 ]; then
    echo ">> build_mosaic ch@CHAN@ finished in dry mode";    echo ""; exit 1
fi

# Now do the work
echo ""
echo ">> ==========  Begin python output  ========== "

$comm
echo ">> ==========   End python output   ========== "
echo ""

# check mopex logfile for proper termination
logfile=build_mosaic_ch@CHAN@.log
fin=$(tail -1 $logfile)
if [ $(echo $fin | grep terminated\ normally | wc -l) -eq 1 ]; then
	echo ">> $fin"
	errcode=0
else
	echo ">> WARNING: abnormal termination of mopex.pl ... check $logfile"
	errcode=3
fi

echo ""
echo "------------------------------------------------------------------"
echo " >>>>  build_mosaic ch@CHAN@ finished on $(date) - walltime: $(wt)  <<<<"
echo "------------------------------------------------------------------"
echo ""
exit $errcode
