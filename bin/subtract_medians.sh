#!/bin/bash
#PBS -S /bin/bash
#PBS -N submeds_@PID@
#PBS -o subtract_medians.out
#PBS -j oe
#PBS -l nodes=1:ppn=@PPN@,walltime=@WTIME@
#
#-----------------------------------------------------------------------------
# File:     subtract_medians.sh @INFO@
# Purpose:  wrapper for subtract_medians.py
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
module=subtract_medians

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

# Build the command line
comm="python $module.py"

echo " - Work dir is:  $WRK"
echo " - Command is: $comm"
echo " - Starting on $(date) on $(hostname)"
echo " - command line is: "
echo " % $comm"

if [ $dry -eq 1 ]; then
	echo ">> $module finished in dry mode"; exit 1
fi

# Now do the work
echo ""
echo ">> ==========  Begin python output  ========== "

$comm
echo ">> ==========   End python output   ========== "
echo ""

echo ""
echo ">> Check all products produced:"

dir=$(grep ^AORoutput supermopex.py | cut -d\' -f2 | tr -d \/)
chkmeds() {            # loop over tables in medians/ directory
	for f in $dir/files.*.tbl; do
		for i in $(grep _bcd.fits $f | cut -d' ' -f2); do
			if [ ! -e ${i%_bcd.fits}_sub.fits ]; then 
				str=$(echo ${i%_bcd.fits}_sub.fits | cut -d\/ -f5-8)
				echo "  ATTN: ${str} NOT FOUND"
			fi
		done
	done
}

chkmeds > missing_submeds.list
nmiss=$(cat missing_submeds.list | wc -l)
if [ $nmiss -gt 0 ]; then
	echo "PROBLEM:  $nmiss _sub.fits files not build - see missing_submeds.list"
	exit=1
else
	exit=0
fi

echo "------------------------------------------------------------------"
echo " >>>>  $module finished on $(date) - walltime: $(wt)  <<<<"
echo "------------------------------------------------------------------"
echo ""
exit $exit

# for each _bcd.fits frame there shoud be a _sub.fits and an _sbunc.fits
data=$(grep ^RawDataDir supermopex.py | cut -d\' -f2 | tr -d \/)

# loop over files
for d in $data/r*; do       # split loop to avoid lists too long for OS
	for f in ch?/bcd/SPI*_bcd.fits; do 
		root=${f%_bcd.fits}
		if [ ! -e ${root}_sub.fits ]; then 
			echo "  ATTN: $d/${root}_sub.fits NOT FOUND"
		fi
	done
done
