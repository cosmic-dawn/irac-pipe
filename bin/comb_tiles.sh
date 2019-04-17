#!/bin/sh
#PBS -S /bin/bash
#PBS -N CombTiles_@PID@
#PBS -o comb_tiles.out
#PBS -j oe
#PBS -l nodes=1:ppn=22,walltime=32:00:00
#
#-----------------------------------------------------------------------------
# File:     comb_tiles.sh @INFO@
# Purpose:  use swarp to combine tiles into final mosaics
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

if [[ "${@: -1}" == 'dry' ]]; then dry=1; else dry=0; fi
#-----------------------------------------------------------------------------

WRK=$PWD
#WRK=/n09data/cos45
mycd $WRK

pars=$WRK/supermopex.py
odir=$(grep '^OutputDIR '   $pars | cut -d\' -f2 | tr -d \/)
PID=$(grep  '^PIDname '     $pars | cut -d\' -f2)
tlf=$(grep '^TileListFile ' $pars | cut -d\' -f2) #; echo "$PID, $tlf"; exit
tlf=${odir}/${PID}$tlf                            #; echo "$PID, $tlf"

# which channels?
chans=$(grep irac $tlf | sort -u -nk3 | tr -s \  | cut -d\  -f4)

# global head file:
glhead=global.head

mycd $odir
args="-WEIGHT_SUFFIX _cov.fits -WEIGHT_TYPE MAP_WEIGHT -VERBOSE_TYPE QUIET "
resy="-RESAMPLE Y  -RESAMPLING_TYPE LANCZOS2 "
resn="-RESAMPLE N "

for c in $chans; do 
	list=${PID}_ch${c}.lst
	ls $PID.irac.tile.*.${c}.mosaic.fits > $list   # build list of tiles
	echo "# Found $(cat $list | wc -l) tiles for chan $c"
	mos=mosaic_ch${c}.fits
	wgt=${mos%.fits}_cov.fits
	ln -sf $glhead ${mos%.fits}.head    # build link to global head file
	comm="swarp @$list -IMAGEOUT_NAME $mos -WEIGHTOUT_NAME $wgt  $args $resy"
	echo $comm
	if [ $dry -eq 1 ]; then
		echo "# dry mode: do nothing ..."
	else
		$comm
		ls -lh mosaic_ch${c}*.fits
	fi
done

# to do:
# - need an external headfile
# - replace -1E30 by nan


#----------------------------------------------------------------------------
exit 0


