#!/bin/sh
#PBS -S /bin/bash
#PBS -N CombTiles_@PID@
#PBS -o $HOME/combine_tiles.out
#PBS -j oe
#PBS -l nodes=1:ppn=18,walltime=12:00:00
#
#-----------------------------------------------------------------------------
# File:     combine_tiles.sh @INFO@
# Purpose:  use swarp to combine tiles into final mosaics; the _cov files are
#           used as weight maps (NB: the _cov files from mopex count the number
#           of frames that went into the pixes, weighted by the exposure time.
#-----------------------------------------------------------------------------
# 
set -u 

ec()  { echo    "$(date "+[%d.%h.%y %T"]) $1 " ; } 
ecn() { echo -n "$(date "+[%d.%h.%y %T"]) $1 " ; } 
mycd() { if [ -d $1 ]; then \cd $1; echo " --> $PWD"; 
    else echo "!! ERROR: $1 does not exit ... quitting"; exit 5; fi; }

wt() { echo "$(date "+%s.%N") $bdate" | \
	awk '{printf "%0.2f hrs\n", ($1-$2)/3600}'; }  # wall time

# load needed softs and set paths
module () {	 eval $(/usr/bin/modulecmd bash $*); }
module purge ; module load intelpython/3-2019.4   

bindir=/home/moneti/softs/irac-pipe/bin
pydir=/home/moneti/softs/irac-pipe/python

# check if dry mode
if [[ "${@: -1}" == 'dry' ]]; then dry=1; else dry=0; fi
#-----------------------------------------------------------------------------

bdate=$(date "+%s.%N")       # start time/date
node=$(hostname)   # NB: compute nodes don't have .iap.fr in name

# check if running via shell or via qsub:
module=combine_tiles

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

export PATH="~/bin:/softs/astromatic/bin:/softs/dfits/bin:$PATH"
mycd $WRK

field=$(pwd | cut -d\/ -f3 | tr "A-Z" "a-z")

pars=$WRK/supermopex.py
odir=$(grep '^OutputDIR '   $pars | cut -d\' -f2 | tr -d \/)
PID=$(grep  '^PIDname '     $pars | cut -d\' -f2)
tlf=$(grep '^TileListFile ' $pars | cut -d\' -f2) #; echo "$PID, $tlf"; exit
tlf=${odir}/${PID}$tlf                            #; echo "$PID, $tlf"

# which channels?
chans=$(grep irac $tlf | sort -u -nk3 | tr -s \  | cut -d\  -f4)

# global head file:
if [[ $field == 'full' ]]; then 
	glhead=$WRK/cdf/global_cosmos.head
else
	glhead=$WRK/cdf/global_${field}.head
fi

mycd $odir
args="-WEIGHT_SUFFIX _cov.fits -WEIGHT_TYPE MAP_WEIGHT -VERBOSE_TYPE LOG "
resy="-RESAMPLE Y  -RESAMPLING_TYPE LANCZOS2 -SUBTRACT_BACK N"

for c in $chans; do 
	root=${PID}.tilemosaic.${c}    # root name for output files
	list=$root.lst
	ls $PID.irac.tile.*.${c}.mosaic.fits > $list        # build list of tiles
	echo "## Found $(cat $list | wc -l) tiles for chan $c"
	mos=${root}.fits
	wgt=${mos%.fits}_cov.fits

	comm="swarp @$list -IMAGEOUT_NAME $mos  -WEIGHTOUT_NAME $wgt  -RESCALE_WEIGHTS N  $args $resy"
	echo $comm
	if [ $dry -eq 1 ]; then
		echo "# dry mode: do nothing ..."
	else
		$comm
		python $pydir/set_nans.py $mos
		python $pydir/set_nans.py $wgt
		ls -lh $mos $wgt
	fi
	echo "#-------------------------------------------------------"
done

echo ""
echo "------------------------------------------------------------------"
echo " >>>>  combine_tiles finished on $(date) - walltime: $(wt)  <<<<"
echo "------------------------------------------------------------------"
echo ""

#----------------------------------------------------------------------------
exit 0


