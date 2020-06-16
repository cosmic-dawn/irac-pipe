#!/bin/bash
#PBS -S /bin/bash
#PBS -N ols_@PID@_@JOB@
#PBS -o $WRK/outliers_@JOB@.out
#PBS -j oe
#PBS -l nodes=1:ppn=@PPN@,walltime=@WTIME@,mem=@MEM@gb
#
#-----------------------------------------------------------------------------
# File:     find_outliers_job.sh @INFO@
# Purpose:  wrapper for find_outliers_function.py
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
module=find_outliers_function

if [[ "$0" =~ "$module" ]]; then
    WRK=$(pwd)
    echo "## This is ${module}.sh: running as shell script on $node"
    if [ $# -eq 0 ]; then 
        echo "ERROR: Must give a job number"
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
    echo "## This is ${module}.sh: running via qsub on $node"
    WRK=@WRK@   # data are here
    jobNo=@JOB@
    dry=0
fi

#-----------------------------------------------------------------------------
# Begin work
#-----------------------------------------------------------------------------

mycd $WRK

# Build the command line
comm="python $module.py $jobNo"

echo " - Work dir is:  $WRK"
echo " - Starting on $(date) on $(hostname) for @NFRAMES@ frames"
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

# check mopex logfile for proper termination
logfile=outliers_$jobNo.log
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
echo " >>>>  outliers $jobNo finished on $(date) - walltime: $(wt)  <<<<"
echo "------------------------------------------------------------------"
echo ""
exit $errcode
