#!/bin/sh
# run_sex_scamp.sh: 
# wrapper to run sextractor, scamp on subaru mosaics


if [[ "${@: -1}" == 'dry' ]] || [[ "${@: -1}" == 'test' ]]; then dry=T; fi

if [[ $1 =~ 'sol' ]]; then solve=1; else solve=0; fi  # to solve astrometry, or only match
		
echo "-----------------------------------------------------------------------------"
echo ">> Begin sex/scamp ..."

#slsdir=/home/moneti/sls
confdir=/home/moneti/sls/cdf
conf=$confdir/config-forscamp.sex
para=$confdir/photom_scamp.param

pars=supermopex.py
wdir=$(grep '^RootDIR '    $pars | cut -d\' -f2 )
odir=$(grep '^OutputDIR '  $pars | cut -d\' -f2 | tr -d \/)
PID=$(grep  '^PIDname '    $pars | cut -d\' -f2)

echo $wdir/$odir
echo $PID

cd $wdir/$odir; echo " --> $PWD"

for ima in $(ls ${PID}.irac.?.mosaic.fits); do

#	ima=$(echo $file | cut -d\/ -f2)  
#    echo $ima	; exit
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

	if [ -e $cat ]; then
		echo "-------------------------------------------------------"
		echo "$cat already exists ... skips sextractor"
		echo "-------------------------------------------------------"
	else
		args="-CATALOG_NAME $cat  -CATALOG_TYPE FITS_LDAC  -SATUR_LEVEL 300000. 
          -DETECT_THRESH 5  -ANALYSIS_THRESH 5
          -STARNNW_NAME $confdir/default.nnw  -FILTER_NAME $confdir/gauss_2.0_5x5.conv
          -RESCALE_WEIGHTS N  -WEIGHT_GAIN N 
          -BACK_TYPE MANUAL   -BACK_VALUE 0.0  -SEEING_FWHM 0.8 "

		echo "-----------------------------------------------------------------------------"
		echo ">>>> SExtractor on "$ima
		echo "-----------------------------------------------------------------------------"
		echo -n ">> input image:   "; ls -Lh $ima | tr -s ' ' | cut -d\  -f9-19
		if [ -e $wgt ]; then echo -n ">> weight image:  "; ls -Lh $wgt | tr -s ' ' | cut -d\  -f9-19; fi
		if [ -e $rms ]; then echo -n ">> rms image:     "; ls -Lh $rms | tr -s ' ' | cut -d\  -f9-19; fi
		echo -n ">> config file:   "; ls -lh $conf     | tr -s ' ' | cut -d\  -f9-19
		echo -n ">> param file:    "; ls -lh $para     | tr -s ' ' | cut -d\  -f9-19
		echo    ">> output catal:  $cat"
		echo ""
		
		sexcomm="sex $ima $wt  $args  -c $conf  -PARAMETERS_NAME $para  -VERBOSE_TYPE NORMAL " 
		echo $sexcomm  ;  echo ""

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
		extras="-ASTREF_CATALOG FILE  -ASTREFCAT_NAME $confdir/GAIA-DR1_1000+0211_r76.cat "
	fi

	# match / solve astrometry params
	if [ $solve -ne 1 ]; then      # for simple matching
		args=" -c $confdir/scamp.conf  -MATCH N  -SOLVE_ASTROM N  -SOLVE_PHOTOM N"
	else 	# with solution
		args=" -c $confdir/scamp.conf  -MATCH Y  -SOLVE_ASTROM Y  -SOLVE_PHOTOM N  -DISTORT_DEGREES 1"
	fi

	echo "-----------------------------------------------------------------------------"
	echo ">>>> Scamp for irac on $cat"
	echo "-----------------------------------------------------------------------------"
	echo    ">> input catal:   $cat"
	echo -n ">> param file:    "; ls -lh $para     | tr -s ' ' | cut -d\  -f9-19
	echo ""

	sccomm="scamp $cat  $args  $extras    -MOSAIC_TYPE UNCHANGED  -VERBOSE_TYPE FULL  -WRITE_XML Y" 
	echo $sccomm  ;  echo ""

	if [[ $dry != "T" ]]; then
		$sccomm > ${root}_scamp.log 2>&1
		if [ $? -ne 0 ]; then echo "ERROR ... quitting"; exit 5; fi
		rename astr ${root} astr*.png
		rename _1.p .p $root*.png
		echo " ==> DONE: $(ls $root.head ${root}*.png) built ..."  
#		echo "-----------------------------------------------------------------------------"
		echo ""
	else
		echo "####  DRY MODE -- DO NOTHING  ####"
		echo "" ; [ -e $rms ] && exit
	fi
done

echo " scamp Astrom detections:"
for f in *scamp.log; do echo "$f $(grep detections\ load $f)"; done

echo " scamp Astrom stats:"
grep -A2 external cos45.irac.?.mosaic_scamp.log | grep Group

exit 0

#grep ^Group  subaru_*_scamp*.log | grep -v \ 0\  
#grep ^Group  HSC_*_scamp*.log | grep -v \ 0\  
