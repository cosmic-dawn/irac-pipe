#!/bin/sh
#-----------------------------------------------------------------------------
# script: mkMosaics.sh
#-----------------------------------------------------------------------------
# Run mopex's mosaic_combine directly to (re)produce nominal products and to
# also produce additional ones not produced by the pipeline, all on the same
# pixel grid.  Requires keeping the temp directories created by the build_
# mosaic pipeline script (more precisely by the build_mosaic function in
# spitzer_pipeline_functions.py).
#-----------------------------------------------------------------------------
# NB: to remove last character from string: ${string::-1}
#     to get last character of string:      ${string: -1}
#     to get first n characters of string:  ${string:0:n}
#-----------------------------------------------------------------------------
if [[ "${@: -1}" == 'dry' ]]; then dry=T; else dry=F; fi
#-----------------------------------------------------------------------------

if [ -z "$WRK" ]; then 
    echo " ERROR: \$WRK (workdir) environment variable not defined ... quitting" 
    exit 20
fi
if [ $WRK != $PWD ]; then
	echo " #### ERROR: \$WRK == $WRK != $PWD ... "
	echo " #### NOT IN EXPECTED WORK DIRECTORY ... quitting"
	exit 0
fi

PID=$(echo $WRK | cut -d\/ -f3)

# get tmp dirs from build_mosaic log files
nn=$(ls build_mosaic_ch?.log | wc -l)
if [ $nn -ge 1 ]; then
	tdirs=$(grep coadd_Tiles_List build_mosaic_ch?.log | grep mopex | cut -d \  -f4 | cut -d\/ -f1-3)
else
	echo " #### ERROR: build_mosaic logfiles not found"
	if [ $PID != "COSMOS" ]; then exit 0; fi
fi

if [ $PID == "COSMOS" ]; then
	tdirs=$(cat BuildMosaic_tmpDirs.lst)
fi

#echo $tdirs  ; exit ## DEBUG

for tdir in $tdirs; do 
	cmdir=$tdir/Coadd-mosaic     # Coadd-mosaic dir
	ch=${tdir: -1}  

	# check what actually has been build for each tile
	nn=$(echo $tdir | grep tmpdir_ | wc -l)  #;  echo $nn
	if [ $nn -eq 0 ]; then 
		root=$(head -1 $cmdir/coadd_Tiles_List | cut -d\_ -f1-5)          # ====> f1-6  for BuildMosaicDir style
		tiles=$(ls -1 ${root}_*.fits | cut -d\_ -f6-9 | cut -d. -f1)      # ====> f7-9
	else
		root=$(head -1 $cmdir/coadd_Tiles_List | cut -d\_ -f1-6)          # ====> f1-6  for BuildMosaicDir style
		tiles=$(ls -1 ${root}_*.fits | cut -d\_ -f7-9 | cut -d. -f1)      # ====> f7-9
	fi
	echo -n "#### Ch $ch: $cmdir  ==> tiles: "; echo  $tiles # ; exit

	for tile in $tiles; do
		ls ${root}_$tile.fits > tlist   # written locally and deleted
		nn=$(cat tlist | wc -l)
		if [ $tile == "Image"   ]; then code=image; fi
		if [ $tile == "Cov"     ]; then code=cover; fi  # number of bdc files contributing to each pix
		if [ $tile == "Exp_Cov" ]; then code=covtm; fi  # total integration time per pix 
		if [ $tile == "Std_Unc" ]; then code=stunc; fi  # standard deviation of the interpolated pixels
		if [ $tile == "Unc"     ]; then code=uncer; fi  # propagated from the individual input uncertainties

		echo ">> For $tile list with $nn entries, build $code stack"
		cmd="mosaic_combine  -o ${PID}.irac.$ch.stack_$code.fits  -f $tdir/mosaic_fif.tbl  -g tlist"
		echo ">> $cmd"
		if [ $dry != "T" ]; then time $cmd; fi
	done
done
rm tlist
echo 

#-----------------------------------------------------------------------------
# Now replace zeroes by nans, and build exptm (ratio covtm/cover) files
#-----------------------------------------------------------------------------

pydir=/home/moneti/softs/irac-pipe/python
for d in $tdirs; do
	ch=${d: -1}  #;	echo $ch
	cmd="$pydir/clean_stacks.py $ch "
	if [ $dry == "T" ]; then echo $cmd; else $cmd;	fi
	cmd="$pydir/imratio.py  $PID.irac.$ch.stack_covtm.fits  $PID.irac.$ch.stack_cover.fits  $PID.irac.$ch.stack_exptm.fits "
	if [ $dry == "T" ]; then echo $cmd; else $cmd;	fi
done
#-----------------------------------------------------------------------------
