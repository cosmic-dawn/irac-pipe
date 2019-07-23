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
#        and NPROC from supermopex.py                              (22.Dec.18)
# v1.30: add logging to irac.log and purpose details to local supermopex.py 
#        and wrapper shell scripts 
# v1.40: various fixes (and to make_medians, subtract_medians, build_mosaic)
#        to handle HDR files                                       (30.Dec.18)
# v1.41: minor fixes (mostly to scripts)
# v1.42: minor fixes (mostly to scripts)
# v1.50: split build_mosaic in two parts                           (17.Jan.19)
#-----------------------------------------------------------------------------
# v2.00: using new scripts from Peter Capak, ex. make_mosaics      (27.Feb.19)
# v2.10: with parallelised version of make_mosaics                 (13.Mar.19)
# v2.11: add check_stars and check_astrom; other details           (26.mar.19)
# v2.12: add use_rel var to select devel or release scripts; etc.  (29.mar.19)
# v2.13: minor reorganisation of code; minor other changes         (13.apr.19)
# v2.14: improve handling of large number of jobs in make_tiles    (16.apr.19)
# v2.15: fix logfiles, checks on products, improve logging         (26.apr.19)
# v2.16: more checks on products, improve logging of modules       (10.may.19)
# v2.17: improved Irsa queries; find_stars walltime now dynamic    (07.jun.19)
# v2.18: dynamic walltime for other modules; preps for new modules (11.jun.19)
# v2.19: switch to intelpython/3-2019.4 and other minor changes    (19.jun.19)
# v2.20: rm use_rel variable, add Nthred=Nproc/2 for py scripts    (24.jun.19)
# v2.21: add find_outliers, comb_rmasks, make_mosaics; reset tabs
#        adjust dynamic walltime,                                  (30.jun.19)
# v2.22: more checks on find_outliers, and more                    (10.jul.19)
# v2.23: find_outliers now parallelised by node                    (10.jul.19)
# v2.24: dynamic ppn and walltime for outliers and more            (23.jul.19)
#-----------------------------------------------------------------------------
set -u        # exit if a variable is not defined
#-----------------------------------------------------------------------------

vers="2.24 (23.jul.19)"
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
# Load needed softs and set PATHs
#-----------------------------------------------------------------------------

module () {      eval $(/usr/bin/modulecmd bash $*); }
module purge ; module load intelpython/3-2019.4   mopex 

#-----------------------------------------------------------------------------
# setup dry and auto-continue modes
#-----------------------------------------------------------------------------

dry=F       # dry mode - do nothing
auto=F      # auto-continue defined at each step
xdone=F     # set to T when one part is executed; else will give list of options

# if last param is 'dry' or 'test' then set dry mode
if [ "${@: -1}" == 'dry' ] || [ "${@: -1}" == 'test' ]; then dry=T; fi
if [ $1 == "pars" ] || [ $1 == "env" ]; then dry=T; fi

#-----------------------------------------------------------------------------
# Check that $WRK and $NODE environment variables exist; set Nproc
#-----------------------------------------------------------------------------

if [ -z ${WRK+x} ]; then 
    echo " ERROR: $WRK (workdir) variable not defined" 
    exit 20
fi

#if [ -z ${use_rel+x} ]; then 
#       echo "###  ATTN: setting use_rel=T: use release scripts; "
#       echo "###  export use_rel=F to use development scripts" 
#       use_rel=T
#fi

if [ ! -e $WRK/supermopex.py ]; then 
    NODE=$(echo $WRK | sed 's|/automnt||' | cut -c2-4)   # use local node by default
else 
    NODE=$(grep RootNode $WRK/supermopex.py | cut -d\' -f2)
fi

get_nproc() {
    cnodes | grep cores\] | cut -c2-5,23-25 | grep $NODE | cut -c5,6 ;
}

if [[ $(hostname) =~ "c" ]]; then
    if [ -e supermopex.py ]; then 
        Nproc=$(grep  '^Nproc'  supermopex.py | tr -s ' ' | cut -d\  -f3)
        Nthred=$(grep '^Nthred' supermopex.py | tr -s ' ' | cut -d\  -f3)
    else
        Nproc=$(($(get_nproc) - 3))
        Nthred=$(($(get_nproc)/2))
    fi
else
    echo "     ####"
    echo "     ####---------------------------------------------####"
    echo "     ####  Attn: MUST run pipeline from login node!!  ####"
    echo "     ####        Switching to DRY mode                ####"
    echo "     ####---------------------------------------------####"
    echo "     ####"
    Nproc=0    # to avoid giving unbound variable error 
    Nthred=0   # idem
    if [ $dry == "F" ]; then dry="T"; fi 
fi

wtime="18:00:00"   # default value
Naor="2"           # a dummy vaue
ppn=3
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
    while true; do read -p " ====> Ok to continue? (yes/no): " answer
        echo $answer  >> $pipelog
        case $answer in
            [yYpl]* ) ec "Continue ..."; break  ;;
            *           ) ec "Quitting ..."; exit 3 ;;
        esac
    done  
}

chk_prev() {  
    # check given step is done (presence of .out file), 
    # and copy python scripts for current module
    if [[ $1 != "NULL" ]]; then 
        if [ ! -e $1.out ] || [[ $1 == "NULL" ]]; then 
            ec "ERROR: $1.out not found ... previous step not complete? "
            askuser
        fi
    fi
    xdone=T   # partly done ... (do not print list of steps)
    # copy python scripts to work dir
    comm="rsync -au $pydir/$module.py ."; $comm
    fn=$pydir/${module%.py}_function.py
#    if [ -e $fn ]; then comm="rsync -au $fn ."; ec "$comm"; $comm; fi
    if [ -e $fn ]; then comm="rsync -au $fn ."; $comm; fi
}

write_module() {  # write local verions of py and sh modules
    info="for $WRK, built $(date +%d.%h.%y\ %T)"
    sed -e "s|@NPROC@|$Nproc|" -e "s|@WRK@|$WRK|" -e "s|@NODE@|$NODE|"   \
        -e "s|@INFO@|$info|" -e "s|@PID@|$PID|" -e "s|@WTIME@|$wtime|" \
		-e "s|@PPN@|$ppn|"   $bindir/$module.sh > ./$module.sh
    chmod 755 $module.sh
    ec "# Wrote $module.sh with: $(grep l\ nodes= $module.sh | cut -d\  -f3)"
    if [ $dry == "T" ]; then ec "----  EXITING DRY MODE  ---- "; exit 10; fi
    # submit module and wait for job to finish
    if [ -e $module.out ]; then rm $module.out; fi 
    ecn "# Submit $module file ... "; qsub $module.sh | tee -a $pipelog
    ec "# -- Wait for job to finish --"; sleep 20
    while :; do [ -e $module.out ] && break; sleep 30; done
    chmod 644 $module.out
    ec "# Job $module finished - PBS $(grep RESOURCESUSED $module.out | cut -d\, -f4)"
}

chk_outputs() {  # check outputs of module
    ec "# Check results:"
    # 1. check torque exit status
    grep EXIT\ STATUS $module.out > estats.txt
    nbad=$(grep -v STATUS:\ 0  estats.txt | wc -l)      # files w/ status != 0
    if [ $nbad -gt 0 ]; then
        ec "PROBLEM: $module.sh exit status not 0: "
        grep -v STATUS:\ 0 estats.txt ; askuser
    fi
    ec "# ==> torque exit status ok;"; rm -f estats.txt
    # 2. check .out file for other errors (python)
    errfile=$module.err
    grep -i -n -e Error -e Exception -e Traceback -e MALLOC -e Errno $module.out > $errfile
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
chkmeds() {  # check for presence of products of subtract_medians
    # loop over files.aor...tbl tables
    for f in $mdir/files.*.tbl; do               
        aordir=$(tail -1 $f | cut -d\/ -f1-7)   #; echo $aordir; exit
        # loop over filenames found in files.aor.ch.#.tbl  file
        for i in $(grep _bcd.fits $f | cut -d' ' -f2); do
            if [ ! -e ${i%_bcd.fits}_sub.fits ]; then 
                s1=$(echo ${i%_bcd.fits}_sub.fits | cut -d\/ -f5-8)
                echo "  PROBLEM: ${s1} not found"
            elif [ ! -e ${i%_bcd.fits}_sbunc.fits ]; then
                s2=$(echo ${i%_bcd.fits}_sbunc.fits | cut -d\/ -f5-8)
                echo "  PROBLEM: ${s2} not found"
            fi
        done
    done
}
wt() {   # to get wall time
        echo "$(date "+%s.%N") $bdate" | awk '{printf "%0.2f hrs\n", ($1-$2)/3600}'
}

#-----------------------------------------------------------------------------
# Variables useful for processing:
#-----------------------------------------------------------------------------

cd $WRK
pars=supermopex.py
pipelog=$WRK/irac.log

bindir=/home/moneti/softs/irac-pipe/bin
pydir=/home/moneti/softs/irac-pipe/python

ec "   #=================================================#"
ec "   #                                                 #"
ec "   #    This is irac.sh ver $vers         #"
ec "   #                                                 #"
ec "   #=================================================#"
ec "|-------  Check parameters  -----------------------------"
ec "| Machine info and more:"
ec "| - Work node:          $NODE"
ec "| - Work dir (\$WRK):    $WRK"
#ec "| - Shell scripts in:   $bindir/"
#ec "| - Python scripts in:  $pydir/"
ec "|--------------------------------------------------------"
module list 2> ml
ec "| Loaded modules: "
ec "| $(grep -v Loaded ml) " ; rm ml
ec "|--------------------------------------------------------"

# Rebuild supermopex.py if not preset
if [ ! -e $pars ]; then 
    ec "|#### ATTN: Build local $pars - template is:"  # | tee -a $pipelog
    ec "|#### $pydir/$pars"
    info="built for $WRK on $(date +%d.%h.%y\ %H:%M)"
    PID=$(pwd | tr \/ \  | awk '{print $NF}')
    sed -e "s|@INFO@|$info|"  -e "s|@NPROC@|$Nproc|"  -e "s|@NTHRED@|$Nthred|" \
        -e "s|@NODE@|$NODE|"  -e "s|@ROOTDIR@|$WRK|"  -e "s|@PID@|$PID|"  \
        -e "s|@CLUSTER@|candide|"  $pydir/$pars > ./$pars
else 
    ec "|####        ATTN: Using local $pars         ####"            #### | tee -a $pipelog
    ec "|####   $(grep mopex.py $pars | grep built | cut -d' ' -f3-9)    ####" #### | tee -a $pipelog
fi

ec "|--------------------------------------------------------"
ec "| Params from $pars:"

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
ec "| - Cluster is:        $(grep 'cluster ' $pars | cut -d\' -f2 )"
ec "| - Nproc requested:   $(grep 'Nproc  ' $pars | cut -d\= -f2 | cut -d\  -f2 )"
ec "| - Nthread requested: $(grep 'Nthred  ' $pars | cut -d\= -f2 | cut -d\  -f2 )"
ec "|--------------------------------------------------------"
ec "| Data info:"

if [ -d $(echo $rdir | tr -d \/) ]; then
    NAORs=$(ls -d $rdir/r???* 2> /dev/null| wc -l)
    ec "| - Num AORs found:    $NAORs"
else 
    ec "| ###### ./$rdir not found or contains no AORs ######"
fi       
if [ -e $odir/$ltab ]; then 
	Nframes=$(grep -v '^|' $odir/$ltab | wc -l)
	Nframes1=$(grep '_I1_' $odir/$ltab | wc -l)
	Nframes2=$(grep '_I2_' $odir/$ltab | wc -l)
	Nframes3=$(grep '_I3_' $odir/$ltab | wc -l)
	Nframes4=$(grep '_I4_' $odir/$ltab | wc -l)
	ec "| - setup_pipeline already run; found $Nframes frames in Products/$ltab; "
	ec "| - $Nframes1 in ch1, $Nframes2 in ch2,  $Nframes3 in ch3,  $Nframes4 ch4"
fi

ec "|-------  End parameter check  --------------------------"
echo ""

if [ $1 == "pars" ] || [ $1 == "env" ] || [ $NAORs -eq 0 ]; then
    exit 0               # quit here ...
fi

# python processing scripts are copied when needed.  Here copy the flunctions library
comm="rsync -a $pydir/spitzer_pipeline_functions.py ."; $comm
#ec "$comm"

#-----------------------------------------------------------------------------
# Finished preambling ... now get to work
#-----------------------------------------------------------------------------

# check Products dir and temp dir
if [[ ! -z $(ls $tdir) ]]; then
    ec "##### ATTN: ${tdir} directory not empty ..."
    if [ $dry == 'F' ]; then askuser; fi
fi

if [[ ! -z $(ls $odir) ]]; then
    ec "##### ATTN: ${odir} directory not empty ..."
    if [ $dry == 'F' ]; then askuser; fi
fi

str=""
if [ $auto == "T" ]; then str="- in auto mode"; fi
if [ $dry == "T" ];  then str="- in dry mode";  fi

ec "#-----------------------------------------------------------------------------"
ec "##  Begin Spitzer data reduction pipeline $str  "

#-----------------------------------------------------------------------------
### -  1. setup pipeline
#-----------------------------------------------------------------------------

if [[ $1 =~ "setup_pipe" ]]     || [ $1 == "setup" ]; then

    if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
    
    ec "#-----------------------------------------------------------------------------"
    ec "# >>>>  1. Setup pipeline  <<<<"
    ec "#-----------------------------------------------------------------------------"
    module=setup_pipeline
    bdate=$(date "+%s.%N")       # start time/date
    chk_prev NULL 
    if [ -e $fn ]; then comm="rsync -au $fn ."; ec "$comm"; $comm; fi
    
	Naor=$(ls -d $rdir/r* | wc -l)
	if [ $Naor -gt 99 ]; then ppn=46; else ppn=30; fi
	#ppn=$Nproc
	wtime=$((5+$Naor/25)):00:00
    write_module
    ec "# Job $module finished - unix walltime=$(wt)"
    chk_outputs
    
    nfra=$(grep Found $module.out | cut -d\  -f2)
    nrej=$(grep Rejecting $module.out | wc -l)
    ec "# Found $nfra frames; rejected $nrej because of bad header"
    
    # other results
    Nframes=$(grep -v '^|' $odir/$ltab | wc -l)
	Nframes1=$(grep '_I1_' $odir/$ltab | wc -l)
	Nframes2=$(grep '_I2_' $odir/$ltab | wc -l)
	Nframes3=$(grep '_I3_' $odir/$ltab | wc -l)
	Nframes4=$(grep '_I4_' $odir/$ltab | wc -l)
    ec "# Num frames kept in $odir/$ltab: $Nframes"
    ec "# - in Ch1:        $Nframes1)"
    ec "# - in Ch2:        $Nframes2)"
    ec "# - in Ch3:        $Nframes3)"
    ec "# - in Ch4:        $Nframes4)"
    
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
    naor=$(cat countFiles.dat | wc -l)
    nzer=$(grep -o \ 0\  countFiles.dat | wc -l)
    ec "# Number of AOR x valid channels:  $(($naor*4 -  $nzer))"
    
    end_step
fi

#-----------------------------------------------------------------------------
### -  2. get catalogs
#-----------------------------------------------------------------------------

if [[ $1 =~ "get_cat" ]]        || [ $1 == "catals" ] || [ $auto == "T" ]; then

    if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
    ec "#-----------------------------------------------------------------------------"
    ec "# >>>>  2. Get catalogues  <<<<"
    ec "#-----------------------------------------------------------------------------"
    module=get_catalogs 
    bdate=$(date "+%s.%N")       # start time/date
    chk_prev setup_pipeline
    
    if [ $(hostname) == "candid01.iap.fr" ]; then
        echo "# Running ${module}.py on login node" > ${module}.out
        echo "" >> ${module}.out
        if [ $dry == 'T' ]; then ec "----  EXITING PIPELINE DRY MODE     ---- "; exit 10; fi
        python ${module}.py > ${module}.out
        ec "# Job $module finished - unix walltime=$(wt)"
    else
        ec "PROBLEM: can't run on $(hostname) to get external catals ... quitting"
        exit 12
    fi
    
    errfile=$module.err
    grep -v WARNING $module.out | grep -i -n -e Error -e Exception > $errfile
    nerr=$(cat $errfile | wc -l)
    if [ $nerr -gt 0 ]; then
        ec "PROBLEM: found $nerr errors in .out files ... check file $errfile"
        head -6 $errfile ; askuser
    fi
    ec "# ==> no errors found ... continue "; rm -f $errfile 
    grep -e range -e Area $module.out | awk '{print "[INFO]  "$0}' | tee -a $pipelog
    grep -e Already -e Downloaded $module.out | awk '{print "[INFO]  "$0}' | tee -a $pipelog
    
    end_step
fi

#-----------------------------------------------------------------------------
### -  3. first_frame_corr  (ffcorr)
#-----------------------------------------------------------------------------
#Nframes=280000
if [[ $1 =~ "first_frame" ]]    || [ $1 == "ffcorr" ] || [ $auto == "T" ]; then

    if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
    ec "#-----------------------------------------------------------------------------"
    ec "# >>>>  3. First frame correction  <<<<"
    ec "#-----------------------------------------------------------------------------"
    module=first_frame_corr
    bdate=$(date "+%s.%N")       # start time/date
    chk_prev get_catalogs

	if [ $Nframes -ge 100000 ]; then ppn=46; else ppn=30; fi 
    wtime=$((5+$Nframes/500000)):00:00
    write_module
    ec "# Job $module finished - unix walltime=$(wt)"
    # fix logfile (missing CRs)
    strings $module.out | sed 's/fits)Read/fits)\nRead/' > xx; mv xx $module.out
    chk_outputs; end_step
fi


#-----------------------------------------------------------------------------
### -  4. find_stars
#-----------------------------------------------------------------------------

if [[ $1 =~ "find_st" ]]        || [ $1 == "stars" ]  || [ $auto == "T" ]; then

    if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
    ec "#-----------------------------------------------------------------------------"
    ec "# >>>>  4. Find stars  <<<<"
    ec "#-----------------------------------------------------------------------------"
    module=find_stars
    bdate=$(date "+%s.%N")       # start time/date
    # estimate 0.5 min/frame ==> divide by 2 for 1.5 margin

	if [ $Nframes -ge 100000 ]; then ppn=46; else ppn=30; fi 
    wtime=$((5+$Nframes/10000)):00:00
    ec "# for $Nframes frames set PBS walltime to $wtime"
    #echo "$Nframes $Nproc ==> $wtime"  ; exit
    
    chk_prev first_frame_corr
    write_module
    ec "# Job $module finished - unix walltime=$(wt)"
    # fix logfile (missing CRs)
    strings $module.out | sed -e 's/s:\#\#/s:\n\#\#/' > xx; mv xx $module.out
    
    chk_outputs
    # any aborted jobs??
    grep -i aborted $module.out > $module.aborted
    nab=$(cat $module.aborted | wc -l)
    if [ $nab -ne 0 ]; then
        ec "WARNING: $nab jobs aborted ... see $module.aborted"
        askuser
    else
        rm $module.aborted
    fi
    
    end_step
fi

#-----------------------------------------------------------------------------
### -  5. merge stars
#-----------------------------------------------------------------------------

if [[ $1 =~ "merge_st" ]]       || [ $1 == "merge" ]  || [ $auto == "T" ]; then

    if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
    ec "#-----------------------------------------------------------------------------"
    ec "# >>>>  5. Merge stars  <<<<"
    ec "#-----------------------------------------------------------------------------"
    module=merge_stars
    chk_prev find_stars
    bdate=$(date "+%s.%N")       # start time/date

    wtime=$((1+$Nframes/25000)):00:00
    if [ $Nframes -ge 100000 ]; then ppn=46; else ppn=30; fi 
    write_module
    ec "# Job $module finished - unix walltime=$(wt)"
    chk_outputs; end_step
fi

#-----------------------------------------------------------------------------
### -  6. subtract stars
#-----------------------------------------------------------------------------

if [[ $1 =~ "subtract_st" ]]    || [ $1 == "substars" ] || [ $auto == "T" ]; then

    if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
    ec "#-----------------------------------------------------------------------------"
    ec "# >>>>  6. Subtract stars  <<<<"
    ec "#-----------------------------------------------------------------------------"
    module=subtract_stars
    bdate=$(date "+%s.%N")       # start time/date
    chk_prev merge_stars
    
    wtime=$((1+$Nframes/10000)):00:00
    if [ $Nframes -ge 100000 ]; then ppn=46; else ppn=30; fi 
    write_module
    ec "# Job $module finished - unix walltime=$(wt)"
    
    # fix logfile
    sed -i 's/ts\#\#/ts\n\#\#/' $module.out
    chk_outputs 
    nbeg=$(grep '## Begin ' $module.out | wc -l)
    nfin=$(grep '## Finis ' $module.out | wc -l)
    if [ $nbeg -eq $nfin ]; then
        ec "# Ran $nfin jobs of $(($naor*4 -  $nzer)) expected"
    fi
    end_step
fi

#-----------------------------------------------------------------------------
### -  7. make_medians
#-----------------------------------------------------------------------------

if [[ $1 =~ "make_med" ]]       || [ $1 == "medians" ] || [ $auto == "T" ]; then

    if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
    ec "#-----------------------------------------------------------------------------"
    ec "# >>>>  7. Make medians   <<<<"
    ec "#-----------------------------------------------------------------------------"
    module=make_medians
    bdate=$(date "+%s.%N")       # start time/date
    chk_prev subtract_stars
    
    wtime=$((3+$Nframes/50000)):00:00
    if [ $Nframes -ge 100000 ]; then ppn=46; else ppn=30; fi 
    write_module
    ec "# Job $module finished - unix walltime=$(wt)"
    # fix logfile (missing CRs)
    sed -i 's/s###/s\n###/' $module.out
    chk_outputs; end_step
fi

#-----------------------------------------------------------------------------
### -  8. fix astrometry
#-----------------------------------------------------------------------------

if [[ $1 =~ "fix_astr" ]] || [ $1 == "astrom" ]  || [ $auto == "T" ]; then

    if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
    ec "#-----------------------------------------------------------------------------"
    ec "# >>>>  8. Fix astrometry   <<<<"
    ec "#-----------------------------------------------------------------------------"
    module=fix_astrometry
    bdate=$(date "+%s.%N")       # start time/date
    chk_prev make_medians
    
    wtime=$((1+$Nframes/55500)):00:00
    if [ $Nframes -ge 100000 ]; then ppn=46; else ppn=30; fi 
    write_module
    ec "# Job $module finished - unix walltime=$(wt)"
    chk_outputs; end_step
fi

#-----------------------------------------------------------------------------
### -  9. subtract medians  (submeds)   -
#-----------------------------------------------------------------------------

if [[ $1 =~ "subtract_med" ]]   || [ $1 == "submeds" ] ||[ $auto == "T" ]; then

    if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
    ec "#-----------------------------------------------------------------------------"
    ec "# >>>>  9. Subtract medians    <<<<"
    ec "#-----------------------------------------------------------------------------"
    module=subtract_medians
    bdate=$(date "+%s.%N")       # start time/date
    chk_prev fix_astrometry
    
    wtime=$((3+$Nframes/80000)):00:00
    if [ $Nframes -ge 100000 ]; then ppn=46; else ppn=30; fi 
    write_module
    ec "# Job $module finished - unix walltime=$(wt)"
    chk_outputs
    # check for presence of expected products of subtract_medians 
    mdir=$(grep ^AORoutput supermopex.py | cut -d\' -f2 | tr -d \/)
    chkmeds > missing_submeds.list
    nmiss=$(cat missing_submeds.list | wc -l)
    if [ $nmiss -ne 0 ]; then
        ec "PROBLEM: Missing $nmiss products - see missing_submeds.list"
        askuser
    else 
        ec "# Found all expected products ... continue"
        rm missing_submeds.list
    fi
    
    end_step
fi

#-----------------------------------------------------------------------------
### - 10. check stars       (chkst)     - optional
#-----------------------------------------------------------------------------

if [[ $1 =~ "check_st" ]]       || [[ $1 =~ "chkst" ]] || [ $auto == "T" ]; then

    if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
    ec "#-----------------------------------------------------------------------------"
    ec "# >>>>  10. Check stars   <<<<"
    ec "#-----------------------------------------------------------------------------"
    module=check_stars
    bdate=$(date "+%s.%N")       # start time/date
    chk_prev subtract_medians
    
    if [ $Nframes -ge 100000 ]; then ppn=46; else ppn=30; fi 
    wtime=$((5+$Nframes/12000)):00:00
    write_module
    ec "# Job $module finished - unix walltime=$(wt)"
    chk_outputs; end_step
fi

#-----------------------------------------------------------------------------
### - 11. check astrometry  (chkast)    - optional
#-----------------------------------------------------------------------------

if [[ $1 =~ "check_astro" ]]    || [[ $1 =~ "chka" ]] || [ $auto == "T" ]; then

    if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
    ec "#-----------------------------------------------------------------------------"
    ec "# >>>>  11. Check astrometry   <<<<"
    ec "#-----------------------------------------------------------------------------"
    module=check_astrometry
    bdate=$(date "+%s.%N")       # start time/date
    chk_prev subtract_medians
    
    if [ $Nframes -ge 100000 ]; then ppn=46; else ppn=30; fi 
    wtime=$((5+$Nframes/100000)):00:00
    write_module
    ec "# Job $module finished - unix walltime=$(wt)"
    chk_outputs; end_step
fi

#-----------------------------------------------------------------------------
### - 12. setup tiles       (tiles)     - 
#-----------------------------------------------------------------------------

if [[ $1 =~ "setup_ti" ]]       || [ $1 == "tiles" ]  || [ $auto == "T" ]; then

    if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
    ec "#-----------------------------------------------------------------------------"
    ec "# >>>>  12. Setup tiles for mosaic    <<<<"
    ec "#-----------------------------------------------------------------------------"
    module=setup_tiles
    bdate=$(date "+%s.%N")       # start time/date
    chk_prev subtract_medians
    
    if [ $Nframes -ge 100000 ]; then ppn=46; else ppn=30; fi 
    wtime=$((5+$Nframes/25000)):00:00
    write_module
    ec "# Job $module finished - unix walltime=$(wt)"
    chk_outputs
    
    # check TileListFile:
    tlf=${odir}/${PID}$(grep '^TileListFile ' $pars | cut -d\' -f2) 
    njobs=$(cat $tlf | grep $PID | wc -l)
    if [ -e $tlf ] && [ $njobs -gt 0 ]; then
        ec "# ==>$(grep Split\ mosaic $module.out | cut -c2-99)"
        ec "# ==>$(grep Wrote\ FIF    $module.out | cut -c2-99)"
        ec "# ==> Built mosaic tile list with $njobs entries (jobs)"
    else
        ec "# PROBLEM: $tlf not found or Njobs = 0"
        askuser
    fi
    
    end_step
fi


#-----------------------------------------------------------------------------
### - 15. find_outliers     (outliers)  - parallel / multi-node version
### -     - mosaic.pl at native pix scale, to find outliers
#-----------------------------------------------------------------------------

if [[ $1 =~ "find_out" ]]     || [[ $1 =~ "outli" ]]  || [ $auto == "T" ]; then

    if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
    ec "#-----------------------------------------------------------------------------"
    ec "# >>>>  21. Build the tiles ... actually find_outliers    <<<<"
    ec "#-----------------------------------------------------------------------------"
    module=find_outliers          # for python modules
    shtmpl=find_outliers_job.sh   # template for sh scripts
    bdate=$(date "+%s.%N")        # start time/date
    chk_prev setup_tiles    
    
    rm -f run.outliers outliers.info outliers_*.sh outliers_*.??? 
#    rm -rf $odir/Rmasks/tile*  $odir/${PID}.irac.tile.*mosaic*.fits
        
    # Find number of jobs:
    parfile=$(grep '^IRACOutlierConfig ' $pars | cut -d\' -f2)
    tlf=$(grep '^TileListFile ' $pars | cut -d\' -f2) 
    tlf=$odir/${PID}$tlf 
    njobs=$(cat $tlf | grep $PID | wc -l)
    
    ec "# outliers config file: $parfile"
    ec "# outliers tile list:   $tlf, with $njobs jobs"
    ec "# template for shell scripts is \$bindir/$shtmpl "
    
    for j in $(seq 0 $(($njobs-1))); do
    #for j in $(seq 2); do    # for testing
        outmodule=outliers_$j.sh
        info="for $WRK, built $(date +%d.%h.%y\ %T)"
        nline=$(echo $j | awk {'print $1+5'})
        Ntile=$(sed "${nline}q;d" $tlf | awk '{print $2}')
        NChan=$(sed "${nline}q;d" $tlf | awk '{print $3}')
        Nfram=$(sed "${nline}q;d" $tlf | awk '{print $4}')
        wtime=$((8+$Nfram/1400)):00:00
		ppn=$((8+$Nfram/6000))
        sed -e "s|@WRK@|"$WRK"|" -e "s|@INFO@|$info|"  -e "s|@PID@|"$PID"|"  \
            -e "s|@JOB@|"$j"|"   -e "s|@PPN@|$ppn|"  -e "s|@WTIME@|$wtime|"  \
			$bindir/$shtmpl > $outmodule  
        chmod 755 $outmodule
        echo " $j $Ntile $NChan $Nfram $outmodule $ppn $wtime " | \
            awk '{printf "# job %3d for tile %2d ch %1d with %5d frames ==> %-15s with %2d ppn, wt %2d hr\n", $1,$2,$3,$4,$5,$6,$7}' | \
            tee -a outliers.info
        echo "qsub $outmodule; sleep 2" >> run.outliers
    done
    # check modules
    nmod=$(ls  outliers_*.sh  | wc -l)  # ; echo $nmod
    nsub=$(cat run.outliers   | wc -l)  # ; echo $nsub
    if [ $nsub -eq $njobs ]; then 
        ec "# Wrote $nmod outliers_nn.sh modules"  # | tee -a $pipelog
    else
        ec "# Wrote only $nmod modules of $njobs expected"
        askuser
    fi
    
    if [ $dry == "T" ]; then ec "----  EXITING PIPELINE DRY MODE         ---- "; exit 10; fi
    
    # submit the jobs and begin the wait loop
    ec "# Submit $nsub outliers_nn files ... " 
    source run.outliers | tee submit_outliers.log
    grep -v master submit_outliers.log > submit.errs   # to look for errors in submission
    nerr=$(cat submit.errs | wc -l)
    if [ $nerr -ge 1 ]; then 
        ec "# WARNING: there are some submission errors - check submit_outliers.log ... continuing"
    else
        ec "# All $nmod jobs submitted ok ..."
        rm submit.errs
    fi
    
    ec '# Begin wait loop -- wait for all outliers_* jobs to finish  --'
    n=0 # define loop counter to monitor progress
    while :; do 
        ndone=$(ls outliers_*.out 2> /dev/null | wc -l)
        [ $ndone -eq $nsub ] && break
        n=$((n+1))
        if [ $n -eq 120 ]; then  # 20: check every 10 min; 60 to check every 30 min, etc.
            echo "$(date "+[%d.%h %H:%M"]): $ndone jobs done; $(($nsub-$ndone)) outstanding"
            n=0
        fi
        sleep 30
    done
    ec "# Jobs outliers_nn finished - unix walltime: $(wt)"
    ec "# pbs logs in outliers_nn.out; mopex logs in outliers_nn.log"
    chmod 644 outliers_*.out
    
    ec "# Check results ..."
    # 1. check torque exit status
    grep EXIT\ STATUS outliers_*.out > estats.txt
    nbad=$(grep -v STATUS:\ 0  estats.txt | wc -l)      # files w/ status != 0
    if [ $nbad -gt 0 ]; then
        ec "PROBLEM: some outliers_nn.sh exit status not 0: "
        grep -v STATUS:\ 0 estats.txt ; askuser
    else
        ec "# ==> torque exit status ok;"; rm -f estats.txt
    fi

    # 2. Check .out files for incomplete processing
    grep PROBLEM  outliers_*.out > outliers.pbs
    npbs=$(cat outliers.pbs | wc -l)
    nmos=$(ls $odir/$PID.irac.tile.*.mosaic.fits | wc -l)
    if [ $npbs -ne 0 ]; then
        ec "PROBLEM: found $npbs jobs that did not build all expected outputs - see outliers.pbs"
        head outliers.pbs
    else
        rm outliers.pbs
    fi
    
    # 3. check .log files (from mopex) for other errors
    errfile=outliers.errs
    # Need to compesate for "allowed" errors in mosaic_combine (last mopex pipeline step with mem leak)
    grep -i -n -e Error -e Exception -e MALLOC outliers_*.log | grep -v -e mosaic_combine -e fsts > $errfile
    grep ^System\ Exit  outliers_*.log | grep -v ' 0' | grep -v mosaic_combine >> $errfile
    nerr=$(cat $errfile | wc -l)
    if [ $nerr -gt 0 ]; then
        ec "ATTN: found $nerr errors in .log files ... check file $errfile"
		askuser
    else
        ec "# ==> no other errors found "
        rm -f $errfile 
    fi
    
    # 4. check that all products are built
    nprods=$(ls $odir/$PID.irac.tile.*mosaic*.fits | wc -l)
    nexp=$(($nsub*6))
    if [ $nprods -eq $nexp ]; then
        ec "# All jobs built all expected outputs: "
        ec "# Found all $nmos expected mosaic tiles, and all ancillary products"
		ec "# ... mv outliers_*.* to outliers.files dir" 
        rm -f outliers.psb
    else
        ec "ATTN: Found only $nmos tiles of $nsub expected ..."
    fi
    
    if [ ! -d outliers.files ]; then mkdir outliers.files; fi
    mv outliers_*.?? outliers_*.???  outliers.info submit_outliers.log  outliers.files
    rm addkeyword.txt run.outliers

	# need this file for automatic continuation
	echo "# Keep me for automatic check of combine_rmasks" > $module.out 
    
    end_step
fi


#-----------------------------------------------------------------------------
### - 14. combine rmasks
#-----------------------------------------------------------------------------

if [[ $1 =~ "combine_rm" ]]     || [ $1 == "rmasks" ] || [ $auto == "T" ]; then

    if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
    ec "#-----------------------------------------------------------------------------"
    ec "# >>>>  14. Combine rmasks for mosaic    <<<<"
    ec "#-----------------------------------------------------------------------------"
    module=combine_rmasks
    bdate=$(date "+%s.%N")       # start time/date
    chk_prev find_outliers

    Nfram=$(cat $odir/$ltab | wc -l)
	if [ $Nfram -ge 25000 ]; then ppn=33; else ppn=25; fi
	echo $Nfram $ppn
    write_module
    ec "# Job $module finished - unix walltime=$(wt)"
    chk_outputs

    # fix logfile (missing CRs)
    sed -i 's/s##/s\n##/' $module.out
	for c in 1 2 3 4; do
		echo "# Wrote $(grep _I${c}_ $module.out | wc -l) combined masks for ch${c}"
	done

    nwarn=$(grep ERROR $module.out | wc -l)
    if [ $nwarn -ge 1 ]; then
        ec "# ATTN: found $nwarn jobs with NO files to combine"
    fi
    
    end_step
fi

#-----------------------------------------------------------------------------
### - 15. build_mosaics ... single run, one node per channel
#-----------------------------------------------------------------------------

if [[ $1 =~ "build_mos" ]] || [ $1 == "mosaics" ] || [ $auto == "T" ]; then

    if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
    ec "#-----------------------------------------------------------------------------"
    ec "# >>>>  15. Build mosaics - single run, one node per channel  <<<<"
    ec "#-----------------------------------------------------------------------------"
    module=build_mosaic
    chk_prev combine_rmasks
    fn=$pydir/make_mosaics_function.py
    if [ -e $fn ]; then comm="rsync -au $fn ."; ec "$comm"; $comm; fi
    bdate=$(date "+%s.%N")       # start time/date
    
    rm -f run.mosaics ${module}_ch?.out mosaics.info
    ec "# Namelist for mosaic.pl is: $(grep ^IRACMosaicConfig supermopex.py | cut -d\'  -f2,2)"

    chans=$(cut -d\  -f2 $odir/$ltab | grep 0000_0000 | sed 's|automnt/||' | cut -d\/ -f6 | sort -u | cut -c3,4)
    ecn "# Found channels: $(for c in $chans; do echo -n "$c "; done) "; echo '' | tee -a $pipelog #   ; exit

    # build local qsub scripts
    for chan in $chans; do
        outmodule=${module}_ch${chan}.sh
        info="for $WRK, built $(date +%d.%h.%y\ %T)"
        Nfram=$(grep _I${chan}_ $odir/$ltab | wc -l)
        wtime=$((5+$Nfram/1300)):00:00
		if [ $Nfram -ge 25000 ]; then ppn=46; else ppn=30; fi
        #ec "# Chan $chan has $Nfram frames ==> set ppn=$ppn, PBS walltime to $wtime ..."
        sed -e "s|@WRK@|$WRK|" -e "s|@INFO@|$info|" -e "s|@PID@|$PID|"  -e "s|@CHAN@|$chan|"  \
            -e "s|@WTIME@|$wtime|" -e "s|@PPN@|$ppn|"  -e "s|@NTHRED@|$Nthred|" \
			$bindir/${module}.sh > ./$outmodule
        chmod 755 $outmodule
		echo " $chan  $Nfram $outmodule $ppn $wtime" | \
			awk '{printf "# Ch%d with %6d frames ==> %s with %2d ppn, wt %2d hr\n", $1,$2,$3,$4,$5}' | \
            tee -a mosaics.info
        #ec " wrote $outmodule" 
        echo "qsub $outmodule; sleep 1" >> run.mosaics
    done
    if [ $dry == "T" ]; then ec "----  EXITING PIPELINE DRY MODE     ---- "; exit 10; fi

    nsub=$(cat run.mosaics | wc -l)
    ec "# Submit $nsub ${module}_ch? files ... "; source run.mosaics #| tee -a $pipelog
    
    # wait loop
    ec "--  Wait for ${module}_ch? to finish  --"; sleep 20
    while :; do 
        ndone=$(ls ${module}_ch?.out 2> /dev/null | wc -l)
        [ $ndone -eq $nsub ] && break
        sleep 30
    done
    chmod 644 ${module}_ch?.out
    for f in ${module}_ch?.out; do
        ec "# Job $f finished - PBS $(grep RESOURCESUSED $f | cut -d\, -f4)"
    done
    ec "# Build $nsub mosaics finished - unix walltime=$(wt)"

    ec "# Check results ..."
    # 1. check torque exit status
    grep EXIT\ STATUS ${module}_ch?.out > estats.txt
    nbad=$(grep -v STATUS:\ 0  estats.txt | wc -l)  # files w/ status != 0
    if [ $nbad -gt 0 ]; then
        ec "# PROBLEM: $module.sh exit status not 0: "
        grep -v STATUS:\ 0 estats.txt 
    else
        ec "# Torque exit status ok ..."; rm -f estats.txt
    fi
    
    # 2. check mopex logfiles (.log) for proper termination, and if not look for known errors
	for f in build_mosaic_ch?.log; do echo -n "$f: "; tail $f | strings | tail -1; done > mosaics.done
	npbs=$(cat mosaics.done | grep -v normally | wc -l)
	if [ $npbs -gt 0 ]; then
		errfile=$module.err
		grep -i -n -e Error -e Exception -e MALLOC build_mosaic_ch?.log  > $errfile
		grep ^System\ Exit  build_mosaic_ch?.log | grep -v ' 0'  >> $errfile
		nerr=$(cat $errfile | wc -l)
		if [ $nerr -gt 0 ]; then
			ec "PROBLEM: found $nerr errors in .out files ... check file $errfile"
			head -6 $errfile ; askuser
		fi
	else
		ec "# All build_mosaic jobs terminated normally (dixit mopex)"
    fi

    ec "# The mosaics are in:"
    for f in $odir/$PID.irac.?.mosaic.fits; do
		ec "# - $f"
	done

	# and finally cleanup.
	if [ ! -d mosaics.logfiles ]; then mkdir mosaics.logfiles; fi
	mv build_mosaic*.sh build_mosaic_*.??? mosaics.logfiles
    rm -f run.mosaics addkeyword.txt
    # NB FIF.tbl needed to rerun mosaics; else rebuild by prep_mosaic
    
    ec "#-----------------------------------------------------------------------------"
    ec "# >>>>  Pipeline step $module finished successfully ... good job!!  <<<<"
    ec "#-----------------------------------------------------------------------------"
    ec "#                                                                             "
    ec "    #=================================================#"
    ec "    #                                                 #"
    ec "    #          Here ends the irac pipeline            #"
    ec "    #                                                 #"
    ec "    #=================================================#"
    ec ""
#    ec "#-----------------------------------------------------------------------------"
#    echo "" | tee -a $pipelog
#    echo "# Summary of jobs run:" | tee -a $pipelog
#    echo "#--------------------------------------------------------------------------------------------------------------------------------" | tee -a $pipelog
#    echo "# Job end Date      User         Jobid    Jobname         Queue       Nodes     Memory        Cputime   Walltime     Exit   Nodes" | tee -a $pipelog
#    echo "#--------------------------------------------------------------------------------------------------------------------------------" | tee -a $pipelog
#    cjobshist | grep $PID | tee -a $pipelog
#    echo "#--------------------------------------------------------------------------------------------------------------------------------" | tee -a $pipelog
    
    exit 0
fi

### -#------------------------------------------------------------------
### -# old and superceded processing options
### -#------------------------------------------------------------------

#-----------------------------------------------------------------------------
### - NN. combine tiles into mosaics (swarp)
#-----------------------------------------------------------------------------

if [[ $1 =~ "combine_tiles" ]]  || [ $1 == "combTiles" ] || [ $auto == "T" ]; then

    if [ "${@: -1}" == 'auto' ] ; then auto=T; fi
    ec "#-----------------------------------------------------------------------------"
    ec "# >>>>  22. Combine tiles into mosaic (swarp)   <<<<"
    ec "#-----------------------------------------------------------------------------"
    module=combine_tiles
    #chk_prev  ... n/a for this - do by hand
    bdate=$(date "+%s.%N")       # start time/date
    nn=$(ls make_tiles/make_tile_*.out | wc -l)
    if [ $nn -eq 0 ]; then
        ec "ERROR: No make_tile_nnn.out found ... previous step not complete? "
        askuser
    fi
    
    write_module
    ec "# Job $module finished - unix walltime=$(wt)"
    
    # check products
    grep Found combine_tiles.out
    ec "# Built the following stacks: "
    ls -lh  $odir/mosaic_ch*.fits | tee -a $pipelog
    
    end_step
    exit 0

fi

#=============================================================================

#-----------------------------------------------------------------------------
# keep lines below - needed for options list
#-----------------------------------------------------------------------------
### -#------------------------------------------------------------------   
### -# information options:
### -#------------------------------------------------------------------   
### -  - version:   code version (to be taken with a grain of salt)
### -  - env:       list some processing and environment parameters
### -#------------------------------------------------------------------   
#-----------------------------------------------------------------------------

if [ $xdone == "F" ] ; then
    echo "#-----------------------------------------------------------------------------"
    echo "# ERROR: Invalid option $1; valid options are: "
    egrep "^### - " $0 | cut -c6-99
    exit 20
fi

#-----------------------------------------------------------------------------
exit 0
#-----------------------------------------------------------------------------
