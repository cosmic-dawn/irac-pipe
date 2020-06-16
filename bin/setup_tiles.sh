#!/bin/bash
#PBS -S /bin/bash
#PBS -N preTiles_@PID@
#PBS -o setup_tiles.out
#PBS -j oe
#PBS -l nodes=1:ppn=@PPN@,walltime=@WTIME@
#
#-----------------------------------------------------------------------------
# File:     setup_tiles.sh @INFO@
# Purpose:  wrapper for setup_tiles.py
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
module=setup_tiles

if [[ "$0" =~ "$module" ]]; then
	WRK=$(pwd)
    echo "## This is ${module}.sh: running as shell script on $node"
    if [[ "${@: -1}" == 'dry' ]]; then dry=1; else dry=0; fi
else
    echo "## This is ${module}.sh: running via qsub on $node"
	WRK=@WRK@   # data are here
    dry=0
fi

#-----------------------------------------------------------------------------
# Begin work
#-----------------------------------------------------------------------------

mycd $WRK

PID=$(grep  '^PIDname ' supermopex.py | cut -d\' -f2)
tdir=$(grep '^TMPDIR '  supermopex.py | cut -d\' -f2 | tr -d \/)
odir=$(grep '^OutputDIR ' supermopex.py | cut -d\' -f2 | tr -d \/)

# Build the command line
comm="python $module.py"

echo " - Work dir is:  $WRK"
echo " - Starting on $(date) on $(hostname)"
echo " - command line is: "
echo " % $comm"

if [ $dry -eq 1 ]; then
	echo " $module finished in dry mode"; exit 1
fi

# Now do the work
echo ""
echo ">> input lists are $PID.irac.?.sub.lst with these entries:"
wc -l $odir/$PID.irac.?.sub.lst
echo ""
echo ">> ==========  Begin python output  ========== "

$comm
echo ">> ==========   End python output   ========== "
echo ""

# check log of fiducial_image_frame run done via mosaic.pl
logfile=$module.log   
fin=$(tail -1 $logfile)
if [ $(echo $fin | grep terminated\ normally | wc -l) -eq 1 ]; then
	echo ">> fiducial_image_frame ternimated normally"
	errcode=0
else
	echo ">> WARNING: abnormal termination of fiducial_image_frame ... check $logfile"
	errcode=3
fi

# check logs of mosaic_geometry

# 1. check for expected number of logfiles
nexp=$(grep tile $tdir/AllTiles.tbl | wc -l)  # number expected (I think)
nout=$(ls $tdir/mosaic_geom_*.log | wc -l)    # number found
if [ $nout -eq $nexp ]; then
    echo "# Found all $nout expected mosaic_geom logfiles"
else
    echo "# PROBLEM: Found only $nout mosaic_geom logfile for $nexp expected ..."
	errcode=4
fi

# 2. check last line for normal termination
RES=$(mktemp)
for f in $tdir/mosaic_geom_*.log; do
    echo "$f: $(tail -5 $f | strings | tail -1)" >> $RES
done

nbad=$(grep -v normally $RES | wc -l)
if [ $nbad -eq 0 ]; then
    ec "# All mosaic_geom jobs terminated normally"
	rm $RES
else
    ec "## ERROR: imporoper termination of $nbad setup_tile job(s)"
    errcode=5
fi


echo ""
echo "------------------------------------------------------------------"
echo " >>>>  $module finished on $(date) - walltime: $(wt)  <<<<"
echo "------------------------------------------------------------------"
echo ""
exit $errcode
