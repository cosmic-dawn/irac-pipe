#!/bin/sh
#PBS -S /bin/bash
#PBS -N s_scamp_@PID@
#PBS -o s_scamp.out
#PBS -j oe
#PBS -l nodes=1,walltime=2:00:00
#-----------------------------------------------------------------------------
# File:    run_sex_scamp.sh: 
# Purpose: wrapper to run sextractor, scamp on mosaics
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
module=run_sex_scamp

if [[ "$0" =~ "$module" ]]; then
    WRK=$(pwd)
    echo "## This is ${module}.sh: running as shell script on $node"
	if [[ "${@: -1}" =~ 'sol' ]]; then solve=1; else solve=0; fi  # to solve astrometry, or only match
	if [[ "${@: -1}" == 'dry' ]] || [[ "${@: -1}" == 'test' ]]; then dry=T; fi
	dry=F
#	echo $dry ; echo $solve
#    if [[ "${@: -1}" == 'dry' ]]; then dry=1; else dry=0; fi
else
    echo "## This is ${module}.sh: running via qsub on $node"
    WRK=@WRK@   # data are here
	solve=0
    dry=0
fi

#-----------------------------------------------------------------------------
# Begin work
#-----------------------------------------------------------------------------

#slsdir=/home/moneti/sls
confdir=/home/moneti/softs/irac-pipe/cdf
conf=$confdir/config-forscamp.sex
para=$confdir/photom_scamp.param

pars=supermopex.py
if [ ! -e $pars ]; then
	echo "## ERROR: not in a working directory ... quitting"
	exit 3
fi

wdir=$(grep '^RootDIR '    $pars | cut -d\' -f2 )
odir=$(grep '^OutputDIR '  $pars | cut -d\' -f2 | tr -d \/)
PID=$(grep  '^PIDname '    $pars | cut -d\' -f2)

echo "#-----------------------------------------------------------------------------"
echo ">> Begin sex/scamp ... for field $PID"  # in $wdir/$odir" ; echo $PID
cd $wdir/$odir; echo " --> $PWD"

nims=$(ls ${PID}.irac.?.mosaic.fits | wc -l)
echo "# Found $nims stacks to measure "

for ima in $(ls ${PID}.irac.?.mosaic.fits); do

	root=${ima%.fits}
	wgt=${root}_weight.fits
	rms=${root}_rms.fits
	cov=${root}_cov.fits
	if [ -e $wgt ]; then wt=" -WEIGHT_TYPE MAP_WEIGHT -WEIGHT_IMAGE $wgt"; fi
	if [ -e $cov ]; then wt=" -WEIGHT_TYPE MAP_WEIGHT -WEIGHT_IMAGE $cov"; fi
	if [ -e $rms ]; then wt=" -WEIGHT_TYPE MAP_RMS    -WEIGHT_IMAGE $rms"; fi
	filt=$(echo $ima | cut -d\_ -f2)
	cat=${ima%.fits}.ldac

    #-----------------------------------------------------------------------------
    # sextractor
    #-----------------------------------------------------------------------------

	echo "#-----------------------------------------------------------------------------"
	echo ">>>> SExtractor on "$ima
	echo "#-----------------------------------------------------------------------------"

	if [ -e $cat ]; then
		echo ">> WARNING: $cat already exists ... skips sextractor"
	else
		args="-CATALOG_NAME $cat  -CATALOG_TYPE FITS_LDAC  -SATUR_LEVEL 300000. 
          -DETECT_THRESH 5  -ANALYSIS_THRESH 5
          -STARNNW_NAME $confdir/default.nnw  -FILTER_NAME $confdir/gauss_2.0_5x5.conv
          -RESCALE_WEIGHTS N  -WEIGHT_GAIN N 
          -BACK_TYPE MANUAL   -BACK_VALUE 0.0  -SEEING_FWHM 0.8 "

		echo -n ">> input image:   "; ls -Lh $ima | tr -s ' ' | cut -d\  -f9-19
		if [ -e $wgt ]; then echo -n ">> weight image:  "; ls -Lh $wgt | tr -s ' ' | cut -d\  -f9-19; fi
		if [ -e $rms ]; then echo -n ">> rms image:     "; ls -Lh $rms | tr -s ' ' | cut -d\  -f9-19; fi
		echo -n ">> config file:   "; ls -lh $conf     | tr -s ' ' | cut -d\  -f9-19
		echo -n ">> param file:    "; ls -lh $para     | tr -s ' ' | cut -d\  -f9-19
		echo    ">> output catal:  $cat"
		echo ">> command line is: "
		
		sexcomm="sex $ima $wt  $args  -c $conf  -PARAMETERS_NAME $para  -VERBOSE_TYPE NORMAL " 
		echo -n "   "; $sexcomm  ;  echo ""

		if [[ $dry != "T" ]]; then
			$sexcomm > ${root}_sex.log 2>&1
			if [ $? -ne 0 ]; then echo "ERROR ... quitting"; exit 5; fi
			echo " ==> DONE: $(ls $cat) built ..."  
			echo ""
		else
			echo "####  DRY MODE -- DO NOTHING  ####" 
			echo ""
		fi
	fi
    #-----------------------------------------------------------------------------
    # scamp
    #-----------------------------------------------------------------------------

	# remote or local reference catalogue
	if [[ $(hostname) =~ "candid" ]]; then
		extras="-ASTREF_CATALOG GAIA-DR1  -SAVE_REFCATALOG Y "     # external ref. catal.
	else
		field=$(pwd | cut -d\/ -f2)
		case $PID in
			COSMOS ) catal=GAIA-DR1_1000+0211_r76.cat  ;;
			HDFN   ) catal=GAIA-DR1_1237+6222_r104.cat ;;
			CDFS   ) catal=GAIA-DR1_0332-2812_r178.cat ;;
			EGS    ) catal=GAIA-DR1_1419+5255_r65.cat  ;;
			NEP    ) catal=GAIA-DR1_1756+6627_r194.cat ;;
			XMM    ) catal=G  ;;
			sm1|sm2|ctr ) catal=GAIA-DR1_1000+0211_r76.cat ;;
			* ) echo "# ERROR: No GAIA catalogue for field $PID"  ;;
		esac
		extras="-ASTREF_CATALOG FILE  -ASTREFCAT_NAME $confdir/$catal "
	fi

	# match / solve astrometry params
	if [ $solve -ne 1 ]; then      # for simple matching
		args=" -c $confdir/scamp.conf  -MATCH N  -SOLVE_ASTROM N  -SOLVE_PHOTOM N"
	else 	# with solution
		args=" -c $confdir/scamp.conf  -MATCH Y  -SOLVE_ASTROM Y  -SOLVE_PHOTOM N  -DISTORT_DEGREES 1"
	fi

	echo "#-----------------------------------------------------------------------------"
	echo ">>>> Scamp for irac on $cat"
	echo "#-----------------------------------------------------------------------------"
	echo    ">> input catal:   $cat"
	echo -n ">> param file:    "; ls -lh $para     | tr -s ' ' | cut -d\  -f9-19
	echo  ">> command line is: "

	sccomm="scamp $cat  $args  $extras    -MOSAIC_TYPE UNCHANGED  -VERBOSE_TYPE FULL  -WRITE_XML Y" 
	echo -n "   "; echo $sccomm  ;  echo ""

	if [[ $dry != "T" ]]; then
		$sccomm > ${root}_scamp.log 2>&1
		if [ $? -ne 0 ]; then echo "ERROR ... quitting"; exit 5; fi
		rename astr ${root} astr*.png
		rename _1.p .p $root*.png
	else
		echo "####  DRY MODE -- DO NOTHING  ####"
		echo "" ; [ -e $rms ] && exit
	fi
done

echo "#-----------------------------------------------------------------------------"
echo ">> scamp Astrom detections:"
for f in *scamp.log; do echo "$f $(grep detections\ load $f)"; done

echo ">> scamp Astrom stats:"
grep -A2 external $PID.irac.?.mosaic_scamp.log | grep Group
echo "#-----------------------------------------------------------------------------"

# Now montage the scamp pngs:

nf=$(ls -d $PID.*error2d*.png | wc -l)

rm -f $PID.*_c.png astro*.png

for f in $PID.*2d*.png; do 
	convert -shave 75x70 $f ${f%.png}_c.png
done

size='700x700'
montage  -tile ${nf}x1  -geometry ${size}+4+1 $PID.*error2d_c.png ${PID}_astrom2d.png
montage  -tile ${nf}x1  -geometry ${size}+4+1 $PID.*error1d.png   ${PID}_astrom1d.png
rm $PID.*2d*_c.png 

echo ">> Montage of the scamp pngs:"
for f in ${PID}_astro*.png; do echo "   - $(ls $f)"; done

exit 0
