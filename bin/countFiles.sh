#!/bin/sh
#-----------------------------------------------------------------------------
# File:      countFiles.sh - used by IRAC pipeline irac.sh
#-----------------------------------------------------------------------------
# Purpose:   count _bcd files in each AOR in the rad data dir, by channel
# Author:    A. Moneti - Dec.18
#-----------------------------------------------------------------------------
set -u        # exit if a variable is not defined

if [ -z ${WRK+x} ]; then 
	echo " ERROR: $WRK (workdir) variable not defined" 
	exit 20
fi

rdir=$(grep 'RawDataDir =' supermopex.py | cut -d\' -f2 | tr -d \/)
cd $WRK/$rdir

for d in r????*; do 
	root=$(echo $d | cut -d\/ -f1 )
	n1=$(ls $root/ch1/bcd/SPI*_bcd.fits 2> /dev/null | wc -l)
	n2=$(ls $root/ch2/bcd/SPI*_bcd.fits 2> /dev/null | wc -l)
	n3=$(ls $root/ch3/bcd/SPI*_bcd.fits 2> /dev/null | wc -l)
	n4=$(ls $root/ch4/bcd/SPI*_bcd.fits 2> /dev/null | wc -l)
	echo "$root $n1 $n2 $n3 $n4)" | \
		awk '{printf "%-9s  %4i %4i %4i %4i  %5i\n", $1,$2,$3,$4,$5,$2+$3+$4+$5 }'
done  > cc

cat cc | tr -d r | sort -nk1,1 | awk '{print "r"$0 }'; rm cc

exit 0
#---------------------------------------------------------------------------
