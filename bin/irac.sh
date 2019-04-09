#!/bin/bash

#-----------------------------------------------------------------------------
# File:      irac.sh
#-----------------------------------------------------------------------------
# Purpose:   Pipeline for Spitzer/IRAC data processing
# Requires: 
# - work directory with data, given by $WRK env. var.
# - python3 for one module run directly from pipeline;
# - python3 and mopex for the scripts (loaded therein)
# Author:    A. Moneti - Dec.18
#-----------------------------------------------------------------------------
# Versions:
# v1.00: first complete / reliable version
# v1.01: wait loops now wait for .out file; rm parallelisation in find_stars. 
# v1.10: new functions: write_module, submit, check_outps, check_dry, end_step
# v1.11: chk_dry and submit included in write_module; fixed but in get_catals;
#        get NODE variable from $WRK
# v1.20: split make_mosaic to run each chan on a different node, and get NODE
#        and NPROC from supermopex.py (22.Dec.18)
# v1.30: add logging to irac.log and purpose details to local supermopex.py 
#        and wrapper shell scripts 
# v1.40: various fixes (and to make_medians, subtract_medians, build_mosaic)
#        to handle HDR files  (30.Dec.18)
# v1.41: minor fixes (mostly to scripts)
# v1.42: minor fixes (mostly to scripts)
# v1.50: split build_mosaic in two parts  (17.Jan.19)
# v2.00: using new scripts from Peter Capak, ex. make_mosaics (27.Feb.19)
# v2.10: with parallelised version of make_mosaics (13.Mar.19)
# v2.11: add check_stars and check_astrom; other details (26.mar.19)
# v2.12: add use_rel var to select devel or release scripts; etc. (29.mar.19)
# v2.13: minor reorganisation of code; minor other changes (09.apr.19)
#-----------------------------------------------------------------------------
set -u        # exit if a variable is not defined
#-----------------------------------------------------------------------------

vers="2.12 (29.mar.19)"
if [ $# -eq 0 ]; then
    echo "# SYNTAX:"
    echo "    irac.sh option (dry or auto)"
    echo "  Needs WRK environment variable defined to be work dir."
    echo "#------------------------------------------------------------------ "
	echo "# data processing options:"
    grep "^### -" $0 | cut -c6-99
	exit 0
else
	if [[ $1 =~ "ver" ]]; then 
		echo ">> $0 version $vers"; exit 0
	fi 
fi

#-----------------------------------------------------------------------------
# Check that $WRK and $NODE environment variables exist; set Nproc
#-----------------------------------------------------------------------------

if [ -z ${WRK+x} ]; then 
	echo " ERROR: $WRK (workdir) variable not defined" 
	exit 20
fi

if [ -z ${use_rel+x} ]; then 
	echo "###  ATTN: setting use_rel=T: use release scripts; "
	echo "###  export use_rel=F to use development scripts" 
	use_rel=T
fi

if [ ! -e $WRK/supermopex.py ]; then 
	NODE=$(echo $WRK | sed 's|/automnt||' | cut -c2-4)	 # use local node by default
else 
	NODE=$(grep RootNode $WRK/supermopex.py | cut -d\' -f2)
fi

get_nproc() {
	cnodes | grep cores\] | cut -c2-5,23-25 | grep $NODE | cut -c5,6 ;
}

if [[ $(hostname) =~ "candid" ]]; then
	Nproc=$(($(get_nproc) - 3))
else
	echo "####"
	echo "####----------------------------------------------------"
	echo "####  ATTN: Should be running pipeline from login node!!"
	echo "####----------------------------------------------------"
	echo "####"
	Nproc=0    # to avoid giving unbound variable error

fi

#-----------------------------------------------------------------------------
# Functions
#-----------------------------------------------------------------------------

ec() {    # echo with date
    if [ $dry == "T" ]; then echo "[DRY MODE] $1";
    else echo "$(date "+[%d.%h.%y %T]") $1 " | tee -a $pipelog 
    fi
} 
ecn() {   # idem for -n
    if [ $dry == "T" ]; then echo -n "[DRY MODE] $1"
    else echo -n "$(date "+[%d.%h.%y %T]") $1 " | tee -a $pipelog
    fi 
}

mycd() {  # cd with check
	if [ -d $1 ]; then \cd $1; echo " --> $PWD"; 
	else echo "!! ERROR: $1 does not exit ... quitting"; exit 5; 
	fi 
}

askuser() {  # ask user if ok to continue
	echo -n " ==> Is this ok? (yes/no):  "  >> $pipelog
	while true; do read -p " ==> Is this ok? (yes/no): " answer
		echo $answer  >> $pipelog
		case $answer in
			[yYpl]* ) ec "Continue ..."; break	;;
			*		) ec "Quitting ..."; exit 3 ;;
		esac
	done  
}

chk_prev() {  # check given step is done (presence of .out file)
	if [[ $1 != "NULL" ]]; then 
		if [ ! -e $1.out ] || [[ $1 == "NULL" ]]; then 
			ec "ERROR: $1.out not found ... previous step not complete? "
			askuser
		fi
	fi
	# copy python scripts to work dir
	xdone=T
	comm="rsync -au $pydir/$module.py ."; ec "$comm"; $comm
	fn=$pydir/${module%.py}_function.py
	if [ -e $fn ]; then	comm="rsync -au $fn ."; ec "$comm"; $comm; fi
}

write_module() {  # write local verions of py and sh modules
	info="for $WRK, built $(date +%d.%h.%y\ %T)"
	sed -e "s|@NPROC@|$Nproc|" -e "s|@WRK@|$WRK|" -e "s|@NODE@|$NODE|"  \
		-e "s|@INFO@|$info|"   -e "s|@PID@|$PID|"  $bindir/$module.sh > ./$module.sh
	chmod 755 $module.sh
	ec "# Wrote $module.sh"
	if [ $dry == "T" ]; then ec "----  EXITING DRY MODE	 ---- "; exit 10; fi
	# submit module and wait for job to finish
	if [ -e $module.out ]; then rm $module.out; fi 
	ecn "# Submit $module file ... "; qsub $module.sh | tee -a $pipelog
	ec "# -- Wait for job to finish --"; sleep 20
	while :; do [ -e $module.out ] && break; sleep 30; done
	chmod 644 $module.out
	ec "# Job $module finished - $(grep RESOURCESUSED $module.out | cut -d\, -f4)"
}

chk_outputs() {	 # check outputs of module
	ec "# Check results:"
	# 1. check torque exit status
	grep EXIT\ STATUS $module.out > estats.txt
	nbad=$(grep -v STATUS:\ 0  estats.txt | wc -l)	# files w/ status != 0
	if [ $nbad -gt 0 ]; then
		ec "PROBLEM: $module.sh exit status not 0: "
		grep -v STATUS:\ 0 estats.txt ; askuser
	fi
	ec "# ==> torque exit status ok;"; rm -f estats.txt
	# 2. check .out file for other errors (python)
	errfile=$module.err
	grep -i -e Error -e Exception -e Traceback -e MALLOC -e Errno $module.out > $errfile
	nerr=$(cat $errfile | wc -l)
	if [ $nerr -gt 0 ]; then
		ec "PROBLEM: found $nerr errors in .out files ... check file $errfile"
		head -6 $errfile ; askuser
	fi
	ec "# ==> no other errors found. "; rm -f $errfile 
}
end_step() {
	ec "# Pipeline step $module finished successfully ... good job!!  <<<<"

	if [ $auto == "F" ]; then
		ec "#-----------------------------------------------------------------------------"
		exit 0
	fi
}
#-----------------------------------------------------------------------------
# Load needed softs and set PATHs
#-----------------------------------------------------------------------------

module () {	 eval $(/usr/bin/modulecmd bash $*); }
module purge ; module load intelpython/3   mopex 

#-----------------------------------------------------------------------------
# setup dry and auto-continue modes
#-----------------------------------------------------------------------------

dry=F       # dry mode - do nothing
auto=F      # auto-continue defined at each step
xdone=F     # set to T when one part is executed; else will give list of options
#use_rel=F   # to use released (T) or development (F) scripts

# if last param is 'dry' or 'test' then set dry mode
if [ "${@: -1}" == 'dry' ] || [ "${@: -1}" == 'test' ]; then dry=T; fi

if [ $1 == "pars" ]	 || [ $1 == "env" ]; then
	dry=T
fi

#-----------------------------------------------------------------------------
# Variables useful for processing:
#-----------------------------------------------------------------------------

cd $WRK
pars=supermopex.py
pipelog=$WRK/irac.log

if [ $use_rel == "T" ]; then
	bindir=/home/moneti/softs/irac-pipe/bin
	pydir=/home/moneti/softs/irac-pipe/python
else
	bindir=/home/moneti/sls
	pydir=/home/moneti/sls
fi

ec "#==================================================#"
ec "#                                                  #"
ec "#    This is irac.sh ver $vers          #"
ec "#                                                  #"
ec "#==================================================#"
ec "|-------  Check parameters  ---------------------------"
ec "| Machine info and more:"
ec "| - Work node:          $NODE"
ec "| - Work dir (\$WRK):    $WRK"
if [ $use_rel != "T" ]; then
	ec "|### ATTN: using development scripts"
fi
ec "| - Shell scripts in:   $bindir/"
ec "| - Python scripts in:  $pydir/"
ec "|------------------------------------------------------"
ecn "| " ; module list
ec "|------------------------------------------------------"

if [ ! -e $pars ]; then 
	ec "|### ATTN: Build local $pars from ###"  # | tee -a $pipelog
	ec "|### template is $pydir/$pars"
	info="built for $WRK on $(date +%d.%h.%y\ %T)"
	PID=$(pwd | tr \/ \	 | awk '{print $NF}')
	sed -e "s|@INFO@|$info|"  -e "s|@NPROC@|$Nproc|"  -e "s|@NODE@|$NODE|" \
		-e "s|@NODE@|$NODE|"  -e "s|@ROOTDIR@|$WRK|"  -e "s|@PID@|$PID|"  \
		$pydir/$pars > ./$pars
else 
	ec "|### ATTN: Using local $pars ###"            #### | tee -a $pipelog
	ec "|### $(grep mopex.py $pars | grep built | cut -d' ' -f3-9) ###" #### | tee -a $pipelog
fi
ec "|------------------------------------------------------"
ec "| Python params from $pars:"

# extract params from supermopex
rnod=$(grep '^RootNode '   $pars | cut -d\' -f2)
wdir=$(grep '^RootDIR '    $pars | cut -d\' -f2)
rdir=$(grep '^RawDataDir ' $pars | cut -d\' -f2 | tr -d \/)
odir=$(grep '^OutputDIR '  $pars | cut -d\' -f2 | tr -d \/)
tdir=$(grep '^TMPDIR '     $pars | cut -d\' -f2 | tr -d \/)
ltab=$(grep '^LogTable '   $pars | cut -d\' -f2)
lfil=$(grep '^LogFile '    $pars | cut -d\' -f2)
PID=$(grep  '^PIDname '    $pars | cut -d\' -f2)

if [ ! -d $odir ]; then mkdir $odir; fi
if [ ! -d $tdir ]; then mkdir $tdir; fi

ec "| - PID name:          $PID"
ec "| - RootDIR:           $wdir"
ec "| - RawDataDir:        \$RootDIR/$rdir/"
ec "| - OutputDIR:         \$RootDIR/$odir/"
ec "| - LogTable:          \$RootDIR/${odir}/$ltab"
ec "| - TempDir:           \$RootDIR/$tdir/"
ec "| - Nproc requested:   $(grep 'Nproc  ' $pars | cut -d\= -f2 | cut -d\  -f2 )"

if [ -d $(echo $rdir | tr -d \/) ]; then
	NAORs=$(ls -d $rdir/r???* 2> /dev/null| wc -l)
	ec "| - Num AORs found:    $NAORs"
else 
	ec "| ###### ./$rdir not found or contains no AORs ######"
fi	 

ec "|-------  End parameter check  ------------------------"
echo ""

if [ $1 == "pars" ]	 || [ $1 == "env" ]	 || [ $NAORs -eq 0 ]; then
	exit 0		 # quit here ...
fi

# python processing scripts are copied when needed.  Here copy the flunctions library
comm="rsync -a $pydir/spitzer_pipeline_functions.py ."; $comm
#ec "$comm"

#-----------------------------------------------------------------------------
# Finished preambling ... now get to work
#-----------------------------------------------------------------------------

# check Products dir and temp dir
if [[ ! -z $(ls $tdir) ]]; then
	ec "##### ATTN: temp dir $tdir not empty ..."
	if [ $dry == 'F' ]; then askuser; fi
fi

if [[ ! -z $(ls $odir) ]]; then
	ec "##### ATTN: Products dir $odir not empty ..."
	if [ $dry == 'F' ]; then askuser; fi
fi
ec ""

ec "#-----------------------------------------------------------------------------"
ec "##  Begin Spitzer data reduction pipeline	 "

#-----------------------------------------------------------------------------
### -  1. setup:     setup_pipeline
#-----------------------------------------------------------------------------

if [ $1 == "setup" ]; then

	if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
	
	ec "#-----------------------------------------------------------------------------"
	ec "# >>>>  1. Setup pipeline  <<<<"
	ec "#-----------------------------------------------------------------------------"
	module=setup_pipeline
	chk_prev NULL 
	if [ -e $fn ]; then	comm="rsync -au $fn ."; ec "$comm"; $comm; fi

	write_module; chk_outputs

	# other results
	Nframes=$(grep -v '^|' $odir/$ltab | wc -l)
	ec "# Num images: $Nframes"
	ec "# - in Ch1:	   $(grep ch1 $odir/$ltab | wc -l)"
	ec "# - in Ch2:	   $(grep ch2 $odir/$ltab | wc -l)"
	ec "# - in Ch3:	   $(grep ch3 $odir/$ltab | wc -l)"
	ec "# - in Ch4:	   $(grep ch4 $odir/$ltab | wc -l)"

	rm -f countFiles.dat
	cd $rdir
	for d in r???*; do 
		root=$(echo $d | cut -d\/ -f1 )
		n1=$(ls $root/ch1/bcd/SPI*_bcd.fits 2> /dev/null | wc -l)
		n2=$(ls $root/ch2/bcd/SPI*_bcd.fits 2> /dev/null | wc -l)
		n3=$(ls $root/ch3/bcd/SPI*_bcd.fits 2> /dev/null | wc -l)
		n4=$(ls $root/ch4/bcd/SPI*_bcd.fits 2> /dev/null | wc -l)
		echo "$root $n1 $n2 $n3 $n4)" | \
			awk '{printf "%-10s: %4i %4i %4i %4i  %5i\n", $1,$2,$3,$4,$5,$2+$3+$4+$5 }' \
			>> ../countFiles.dat
	done
	cd $WRK

	ec "# Details by AOR in countFiles.dat "
	end_step
fi

#-----------------------------------------------------------------------------
### -  2. catals:    get_catalogs
#-----------------------------------------------------------------------------

if [ $1 == "catals" ] || [ $auto == "T" ]; then

	if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
	ec "#-----------------------------------------------------------------------------"
	ec "# >>>>  2. Get catalogues  <<<<"
	ec "#-----------------------------------------------------------------------------"
	module=get_catalogs 
	chk_prev setup_pipeline

	comm="rsync -au $pydir/$module.py ."; ec "$comm"; $comm
	if [ $(hostname) == "candid01.iap.fr" ]; then
		echo "# Running ${module}.py on login node" > ${module}.out
		echo "" >> ${module}.out
		python ${module}.py >> ${module}.out 2>&1
	else
		ec "PROBLEM: can't run on $(hostname) to get external catals ... quitting"
		exit 12
	fi
	
	errfile=$module.err
	grep -i -e Error -e Exception $module.out > $errfile
	nerr=$(cat $errfile | wc -l)
	if [ $nerr -gt 0 ]; then
		ec "PROBLEM: found $nerr errors in .out files ... check file $errfile"
		head -6 $errfile ; askuser
	fi
	ec "# Job $module finished - walltime=n/a"
	ec "# ==> no errors found ... continue "; rm -f $errfile 
	grep range $module.out | \
		awk '{printf "[INFO]  %3s in range %6.2f -- %6.2f\n", $1,$4,$6}' | tee -a $pipelog

	end_step
fi

#-----------------------------------------------------------------------------
### -  3. ffcorr:    first_frame_correction
#-----------------------------------------------------------------------------

if [ $1 == "ffcorr" ] || [ $auto == "T" ]; then

	if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
	ec "#-----------------------------------------------------------------------------"
	ec "# >>>>  3. First frame correction  <<<<"
	ec "#-----------------------------------------------------------------------------"
	module=first_frame_corr
	chk_prev get_catalogs

	write_module; chk_outputs; end_step
fi


#-----------------------------------------------------------------------------
### -  4. find:      find_stars
#-----------------------------------------------------------------------------

if [ $1 == "find" ] || [ $auto == "T" ]; then

	if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
	ec "#-----------------------------------------------------------------------------"
	ec "# >>>>  4. Find stars  <<<<"
	ec "#-----------------------------------------------------------------------------"
	module=find_stars
	chk_prev first_frame_corr

	write_module; chk_outputs; end_step
	# fix logfile (missing CRs)
	sed -i 's/sFind/s\nFind/' $module.out
fi

#-----------------------------------------------------------------------------
### -  5. merge:     merge stars
#-----------------------------------------------------------------------------

if [ $1 == "merge" ] || [ $auto == "T" ]; then

	if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
	ec "#-----------------------------------------------------------------------------"
	ec "# >>>>  5. Merge stars  <<<<"
	ec "#-----------------------------------------------------------------------------"
	module=merge_stars
	chk_prev find_stars

	write_module; chk_outputs; end_step
fi

#-----------------------------------------------------------------------------
### -  6. substars:  subtract_stars
#-----------------------------------------------------------------------------

if [ $1 == "substars" ] || [ $auto == "T" ]; then

	if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
	ec "#-----------------------------------------------------------------------------"
	ec "# >>>>  6. Subtract stars  <<<<"
	ec "#-----------------------------------------------------------------------------"
 	module=subtract_stars
	chk_prev merge_stars

	write_module; chk_outputs; end_step
fi

#-----------------------------------------------------------------------------
### -  7. medians:   make_medians
#-----------------------------------------------------------------------------

if [ $1 == "medians" ] || [ $auto == "T" ]; then

	if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
	ec "#-----------------------------------------------------------------------------"
	ec "# >>>>  7. Make medians   <<<<"
	ec "#-----------------------------------------------------------------------------"
	module=make_medians
	chk_prev subtract_stars

	write_module; chk_outputs
	# fix logfile (missing CRs)
	sed -i 's/s###/s\n###/' $module.out

	end_step
fi

#-----------------------------------------------------------------------------
### -  8. astrom:    fix_astrometry
#-----------------------------------------------------------------------------

if [ $1 == "astrom" ] || [ $auto == "T" ]; then

	if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
	ec "#-----------------------------------------------------------------------------"
	ec "# >>>>  8. Fix astrometry   <<<<"
	ec "#-----------------------------------------------------------------------------"
	module=fix_astrometry
	chk_prev make_medians

	write_module; chk_outputs; end_step
fi

#-----------------------------------------------------------------------------
### -  9. submeds:   sub_medians
#-----------------------------------------------------------------------------

if [ $1 == "submeds" ] || [ $auto == "T" ]; then

	if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
	ec "#-----------------------------------------------------------------------------"
	ec "# >>>>  9. Subtract medians    <<<<"
	ec "#-----------------------------------------------------------------------------"
	module=subtract_medians
	chk_prev fix_astrometry

	write_module; chk_outputs

	# get total number of AORs * chan
	nc=$(head -1 Products/AORs.tbl | \wc -c); nb=$(($nc-2))
	Ntot=$(grep IRAC Products/AORs.tbl | cut -c${nb}-${nc} | awk 'BEGIN { s = 0 }; { s = s + $1 }; END { print "" s  }')
	# get number of processed AORs * chan
	Nproc=$(grep ^Proces subtract_medians.out | wc -l)
	if [ $Ntot -ne $Nproc ]; then
		ec "# Processed $Nproc AOR*Chan out of $Ntot "
		askuser
	fi

	end_step
fi

#-----------------------------------------------------------------------------
### - 10. check stars:  check_stars      (optional)
#-----------------------------------------------------------------------------

if [[ $1 =~ "check_stars" ]] || [[ $1 =~ "chkst" ]] || [ $auto == "T" ]; then

	if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
	ec "#-----------------------------------------------------------------------------"
	ec "# >>>>  10. Check stars   <<<<"
	ec "#-----------------------------------------------------------------------------"
	module=check_stars
	chk_prev subtract_medians

	write_module; chk_outputs
	end_step
fi

#-----------------------------------------------------------------------------
### - 11. check_astro:  check_astrometry (optional)
#-----------------------------------------------------------------------------

if [[ $1 =~ "check_astro" ]] || [[ $1 =~ "chka" ]] || [ $auto == "T" ]; then

	if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
	ec "#-----------------------------------------------------------------------------"
	ec "# >>>>  11. Check astrometry   <<<<"
	ec "#-----------------------------------------------------------------------------"
	module=check_astrometry
	chk_prev subtract_medians


	write_module; chk_outputs
	end_step
fi

#-----------------------------------------------------------------------------
### - 12. set_tiles: setup_tiles
#-----------------------------------------------------------------------------

if [[ $1 =~ "set_tiles" ]] || [ $auto == "T" ]; then

	if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
	ec "#-----------------------------------------------------------------------------"
	ec "# >>>>  12. Setup tiles for mosaic    <<<<"
	ec "#-----------------------------------------------------------------------------"
	module=setup_tiles
	chk_prev subtract_medians

	write_module; chk_outputs

	# check TileListFile:
	tlf=${odir}/${PID}$(grep '^TileListFile ' $pars | cut -d\' -f2) 
	njobs=$(cat $tlf | grep $PID | wc -l)
	if [ -e $tlf ] && [ $njobs -gt 0 ]; then
		ec "# Built mosaic tile list: $tlf, with $njobs jobs"
	else
		ec "# PROBLEM: $tlf not found or $njobs = 0"
		askuser
	fi

	end_step
fi

#-----------------------------------------------------------------------------
### - 13. do_tiles:  make_tiles
#-----------------------------------------------------------------------------

if [ $1 == "do_tiles" ] || [ $1 == "make_tiles" ] || [ $auto == "T" ]; then

	module=make_tile
	chk_prev setup_tiles

	ec "#-----------------------------------------------------------------------------"
	ec "# >>>>  13. Build the tiles    <<<<"
	ec "#-----------------------------------------------------------------------------"

	rm -f build.tiles make_tile_*.sh
	comm="rsync -au $pydir/$module.py ."; ec "$comm"; $comm

	# Find number of jobs:
	parfile=$(grep  '^IRACMosaicConfig '     $pars | cut -d\' -f2)
	tlf=$(grep '^TileListFile ' $pars | cut -d\' -f2) 
	tlf=$odir/${PID}$tlf 
	njobs=$(cat $tlf | grep $PID | wc -l)
	
	ec "# Mosaic config file: $parfile"
	ec "# Mosaic tile list:   $tlf, with $njobs jobs"

	for j in $(seq 0 $(($njobs-1))); do
#	for j in $(seq 22 25); do    # for testing
		outmodule=${module}_$j.sh
		info="for $WRK, built $(date +%d.%h.%y\ %T)"
		sed -e "s|@WRK@|$WRK|" -e "s|@INFO@|$info|"  -e "s|@PID@|$PID|" \
			-e "s|@JOB@|$j|"   $bindir/${module}.sh > $outmodule
		chmod 755 $outmodule
		echo "wrote $outmodule" | tee -a $pipelog
		echo "qsub $outmodule; sleep 1" >> build.tiles
	done

	if [ $dry == "T" ]; then ec "----  EXITING PIPELINE DRY MODE	 ---- "; exit 10; fi

	nsub=$(cat build.tiles | wc -l)
	ec "# Submit $nsub ${module}_nn files ... " ; source build.tiles | tee -a $pipelog

	# wait loop
	ec "--  Wait for ${module}_ch? to finish  --"; sleep 20
	while :; do 
		ndone=$(ls ${module}_*.out 2> /dev/null | wc -l)
		[ $ndone -eq $nsub ] && break
		sleep 30
	done
	chmod 644 ${module}_*.out
	for f in ${module}_*.out; do
		ec "# Job $f finished - $(grep RESOURCESUSED $f | cut -d\, -f4)"
	done

	ec "# Check results ..."
	# 1. check torque exit status
	grep EXIT\ STATUS ${module}_*.out > estats.txt
	nbad=$(grep -v STATUS:\ 0  estats.txt | wc -l)	# files w/ status != 0
	if [ $nbad -gt 0 ]; then
		ec "PROBLEM: $module_nn.sh exit status not 0: "
		grep -v STATUS:\ 0 estats.txt ; askuser
	else
		ec "# ==> torque exit status ok;"; rm -f estats.txt
	fi

	# 2. check .log files (from mopex) for other errors
	errfile=$module.err
	grep -i -e Error -e Exception -e MALLOC ${module}_*.log > $errfile
	grep ^System\ Exit  ${module}_*.log | grep -v ' 0' >> $errfile
	nerr=$(cat $errfile | wc -l)
	if [ $nerr -gt 0 ]; then
		ec "PROBLEM: found $nerr errors in .log files ... check file $errfile"
		head -6 $errfile ; askuser
	else
		ec "# ==> no other errors found ... continue "; rm -f $errfile 
	fi

	end_step

	exit 0
fi

#-----------------------------------------------------------------------------
### - 14. mosaic:    combine_tiles
#-----------------------------------------------------------------------------

if [ $1 == "combTiles" ] || [ $auto == "T" ]; then

	if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
	#chk_prev make_tile

	ec "#-----------------------------------------------------------------------------"
	ec "# >>>>  14. Combine tiles into mosaic   <<<<"
	ec "#       !!!!   NOT YET IMPLEMENTED  !!!  "
	ec "#-----------------------------------------------------------------------------"
	
fi


#=============================================================================

#-----------------------------------------------------------------------------
### - 21. mosaic:    make_mosaics ... old style
#-----------------------------------------------------------------------------

if [ $1 == "oldmosaic" ] || [ $auto == "T" ]; then

	if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
	module=prep_mosaic
	chk_prev subtract_medians

	ec "#-----------------------------------------------------------------------------"
	ec "# >>>>  10a. prepare for building mosaics - part 0  <<<<"
	ec "#-----------------------------------------------------------------------------"
	
	# preps
	module=prep_mosaic
	if [ ! -e temp/header_list.tbl ]; then
		ec "# a) prepare tables and files ...."
		write_module
		chk_outputs	
	else
		ec "ATTN: temp/header_list.tbl already available, skip $module"
	fi

	# check if temp dirs already exist:
	ls -lhd $tdir/?/* 2> /dev/null  > tempdirs ; ndirs=$(cat tempdirs | wc -l)
	if [ -s tempdirs ]; then 
		ec "ATTN: temp dirs for mosaic products already exist: "
		cat tempdirs
		ec "ATTN: delete them or not, as necessary, before continuing"
		askuser
	fi
	rm -f tempdirs   # ; exit   ##################  stop here for now

	#-------------------------------------------------------------------------
	# build mosaic up to first two mosaic_outlier steps (i.e. before rmask)
	#-------------------------------------------------------------------------
	ec "#-----------------------------------------------------------------------------"
	ec "# >>>>  10b. Build mosaics - part 1  <<<<"
	ec "#-----------------------------------------------------------------------------"
	
	module=build_mosaic
	rm -f build.qall ${module}_ch?.out
	cp $pydir/$module.py .

	# doFull = 1: full build, else split into two parts; 
	doFull=1
	if [ $doFull -eq 1 ]; then
		ec "#####    do full build   #####"
		sed -i 's/beginMosaic/mosaic_FF/' $module.py 
	fi
	ecn "# namelist to begin mosaics is: "
	grep 'cmd = ' build_mosaic.py | tr -s ' ' | cut -d\  -f6,6

	chans=$(cut -d\  -f2 $odir/$ltab | grep 0000_0000 | sed 's|automnt/||' | cut -d\/ -f6 | sort -u | cut -c3,4)
	ecn "# Found channels: "; for c in $chans; do echo -n "$c "; done; echo "" #   ; exit
	# build local qsub scripts
	# look for unused totally free nodes
	avail=$(cnodes | grep free | grep -v \# | tr -d \[\] | tr -s ' ' |sort -nk 6 -r | cut -d\  -f2 | head -4)
	for chan in $chans; do
		case $chan in
			1 ) #NODE=$(grep  ^MosaicNODE $pars | cut -d\' -f2)
				NODE=$(echo $avail| cut -d\  -f1)
				NPROC=$(($(get_nproc) - 3))
				ecn "# ==> Chan 1: node=$NODE, ppn=$NPROC;";;
			2 ) #NODE=$(grep  ^MosaicNODE $pars | cut -d\' -f4)
				NODE=$(echo $avail| cut -d\  -f2)
				NPROC=$(($(get_nproc) - 3))
				ecn "# ==> Chan 2: node=$NODE, ppn=$NPROC;";;
			3 ) #NODE=$(grep  ^MosaicNODE $pars | cut -d\' -f6)
				NODE=$(echo $avail| cut -d\  -f3)
				NPROC=$(($(get_nproc) - 3))
				ecn "# ==> Chan 3: node=$NODE, ppn=$NPROC;";;
			4 ) #NODE=$(grep  ^MosaicNODE $pars | cut -d\' -f8)
				NODE=$(echo $avail| cut -d\  -f4)
				NPROC=$(($(get_nproc) - 3))
				ecn "# ==> Chan 4: node=$NODE, ppn=$NPROC;";;
		esac
		outmodule=${module}_ch${chan}.sh
		info="for $WRK, built $(date +%d.%h.%y\ %T)"
		sed -e "s|@WRK@|$WRK|" -e "s|@NODE@|$NODE|"  -e "s|@NPROC@|$NPROC|" \
			-e "s|@PID@|$PID|" -e "s|@INFO@|$info|"  -e "s|@CHAN@|$chan|"   \
			$bindir/${module}.sh > ./$outmodule
		NF=$(grep in\ Ch${chan} irac.log | tr -s \  | cut -d\  -f7)  # N frames this ch.
		if [ $NF -gt 40000 ]; then sed -i 's/time=48/time=100/' $outmodule; fi
		chmod 755 $outmodule
		echo "wrote $outmodule" | tee -a $pipelog
		echo "qsub $outmodule; sleep 1" >> build.qall
	done
	if [ $dry == "T" ]; then ec "----  EXITING PIPELINE DRY MODE	 ---- "; exit 10; fi

	nsub=$(cat build.qall | wc -l)
	ec "# Submit $nsub ${module}_ch? files ... "; source build.qall | tee -a $pipelog

	# wait loop
	ec "--  Wait for ${module}_ch? to finish  --"; sleep 20
	while :; do 
		ndone=$(ls ${module}_ch?.out 2> /dev/null | wc -l)
		[ $ndone -eq $nsub ] && break
		sleep 30
	done
	chmod 644 ${module}_ch?.out
	for f in ${module}_ch?.out; do
		ec "# Job $f finished - $(grep RESOURCESUSED $f | cut -d\, -f4)"
	done

	ec "# Check results ..."
	# 1. check torque exit status
	grep EXIT\ STATUS ${module}_ch?.out > estats.txt
	nbad=$(grep -v STATUS:\ 0  estats.txt | wc -l)	# files w/ status != 0
	if [ $nbad -gt 0 ]; then
		ec "PROBLEM: $module.sh exit status not 0: "
		grep -v STATUS:\ 0 estats.txt ; askuser
	else
		ec "# ==> torque exit status ok;"; rm -f estats.txt
	fi

	# 2. check .out file for other errors (python)
	errfile=$module.err
	grep -i -e Error -e Exception -e MALLOC ${module}_ch?.out > $errfile
	grep -n exit ${module}_ch?.out | grep -v ' 0' >> $errfile
	nerr=$(cat $errfile | wc -l)
	# There are $nsub FileNotFoundError from the copy files at the end that is
	# attempted in every case
	if [ $nerr -gt $nsub ]; then
		ec "PROBLEM: found $nerr errors in .out files ... check file $errfile"
		head -6 $errfile ; askuser
	else
		ec "# ==> no other errors found ... continue "; rm -f $errfile 
	fi
	# rename build_mosaic....out so that they won't be clobbered by the next step
	rename mosaic mosaic_p1 build_mosaic_ch?.out
	end_step
	if [ $doFull -eq 1 ]; then exit 0; fi
fi

#-----------------------------------------------------------------------------
### - 22. finish:    finish_mosaics
#-----------------------------------------------------------------------------

if [ $1 == "finish" ] || [ $auto == "T" ]; then

	if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
	chk_prev build_mosaic_p1_ch1   # for now

	ec "#-----------------------------------------------------------------------------"
	ec "# >>>>  11. Build mosaics - part 2   <<<<"
	ec "#-----------------------------------------------------------------------------"
	
	#-------------------------------------------------------------------------
	# finish mosaic, i.e. from rmask to end -  here we use the scame scripts as for part 1,
	# but with a different parameter file (namelist)
	#-------------------------------------------------------------------------
	module=build_mosaic
	# replace the paramter file in build_mosaic.py
	sed -i 's/beginMosaic/finishMosaic/' build_mosaic.py
	ecn "# namelist to finish mosaics is: "
	grep Mosaic build_mosaic.py | grep cmd | tr -s ' ' | cut -d\  -f6,6

	if [ $dry == "T" ]; then ec "----  EXITING PIPELINE DRY MODE	 ---- "; exit 10; fi

	nsub=$(cat build.qall | wc -l)
	ec "# Submit $nsub ${module}_ch? files ... "; source build.qall | tee -a $pipelog

	# wait loop
	ec "--  Wait for ${module}_ch? to finish  --"; sleep 20
	while :; do 
		ndone=$(ls ${module}_ch?.out 2> /dev/null | wc -l)
		[ $ndone -eq $nsub ] && break
		sleep 30
	done
	chmod 644 ${module}_ch?.out
	for f in ${module}_ch?.out; do
		ec "# Job $f finished - $(grep RESOURCESUSED $f | cut -d\, -f4)"
	done

	ec "# Check results ..."
	# 1. check torque exit status
	grep EXIT\ STATUS ${module}_ch?.out > estats.txt
	nbad=$(grep -v STATUS:\ 0  estats.txt | wc -l)	# files w/ status != 0
	if [ $nbad -gt 0 ]; then
		ec "PROBLEM: $module.sh exit status not 0: "
		grep -v STATUS:\ 0 estats.txt ; askuser
	else
		ec "# ==> torque exit status ok;"; rm -f estats.txt
	fi

	# 2. check .out file for other errors (python)
	errfile=$module.err
	grep -i -e Error -e Exception -e Traceback -e MALLOC ${module}_ch?.out > $errfile
	grep -n exit ${module}_ch?.out | grep -v ' 0' >> $errfile
	nerr=$(cat $errfile | wc -l)
	if [ $nerr -gt 0 ]; then
		ec "PROBLEM: found $nerr errors in .out files ... check file $errfile"
		head -10 $errfile ; askuser
	else
		ec "# ==> no other errors found ... continue "; rm -f $errfile 
	fi
	# rm build.qall addkeyword.txt
	# NB FIF.tbl needed to rerun mosaics; else rebuild by prep_mosaic
	rename mosaic mosaic_p2 build_mosaic_ch?.out

	# and more
	ec "# The mosaics are in:"
	ls -lthr $odir/$PID.irac.?.mosaic.fits | cut -d\  -f6-9
	ec "#-----------------------------------------------------------------------------"
	ec "# Pipeline step $module finished successfully ... good job!!  <<<<"
	ec "#-----------------------------------------------------------------------------"
	ec "# >>>>	End of Spitzer data reduction pipeline ... great job!!	<<<<"
	ec "#-----------------------------------------------------------------------------"
	echo "" | tee -a $pipelog
	echo "# Summary of jobs run:" | tee -a $pipelog
	echo "#--------------------------------------------------------------------------------------------------------------------------------" | tee -a $pipelog
	echo "# Job end Date      User         Jobid    Jobname         Queue       Nodes     Memory        Cputime   Walltime     Exit   Nodes" | tee -a $pipelog
	echo "#--------------------------------------------------------------------------------------------------------------------------------" | tee -a $pipelog
	cjobshist | grep $PID | tee -a $pipelog
	echo "#--------------------------------------------------------------------------------------------------------------------------------" | tee -a $pipelog

	exit 0
fi

#-----------------------------------------------------------------------------
# keep lines below - needed for options list
#-----------------------------------------------------------------------------
### -#------------------------------------------------------------------   
### -# other options:
### -  - version:   code version (to be taken with a grain of salt)
### -  - env:       list some processing and environment parameters
#-----------------------------------------------------------------------------

#if [ $1 != "qwerty" ] ; then
if [ $xdone == "F" ] ; then
	echo "#-----------------------------------------------------------------------------"
	echo "# ERROR: Invalid option $1; valid options are: "
	egrep "^### - " $0 | cut -c6-99
	exit 20
fi

#-----------------------------------------------------------------------------
exit 0
#-----------------------------------------------------------------------------
