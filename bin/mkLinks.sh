#!/bin/sh

#-----------------------------------------------------------------------------
# File: mkLinks.sh
# Author: A. Moneti - Dec.18
#-----------------------------------------------------------------------------
# Setup new directory for SPitzer/IRAC data processing .
# New directory should exist and should be given by WRK env. var.
# NB. probably best to run it on the node on which $WRK is found.
#-----------------------------------------------------------------------------
if [[ "${@: -1}" =~ 'dry' ]]; then dry=T; else dry=F; fi

# check that WRK is defined
if [[ -z "$WRK" ]]; then 
    echo " ERROR: \$WRK (workdir) environment variable not defined ... quitting" 
    exit 20
fi

cd $WRK; echo " --> $PWD"
field=$(pwd | cut -d\/ -f3)   # nominally name of Spitzer field 

# mar.2020: RAW data moved to $WRK/RAW

RAW="$WRK/RAW"
naor=$(ls -d $RAW/r???* | wc -l)
echo ">> Field is $field; raw data linked from $RAW ... "
echo ">> Found $naor AORs in $RAW ... OK?"  #; exit
echo ">> ...  ^C to quit if not correct"  
sleep 10 #; exit


if [ ! -d Data ]; then echo " -- create Data dir "; mkdir Data; fi
if [ ! -d cal ];  then echo " -- create cal dir  "; mkdir cal;  fi

# link all relevant data to AllData; later (manually) mv to Data the
# AORs to preocess

echo "# 1) build raw data links to files into $RAW"

if [ ! -e shortlist ]; then  # get all the data
	echo ">> Build links to all raw data into Data dir"
	cd Data; echo " --> $PWD"
	if [ $dry == "T" ]; then
		echo "   ### dry mode ... do nothing ###"
	else
		for d in ${RAW}/r???*/ch?/bcd; do 
			r=$(echo $d | cut -d\/ -f5-7); echo " $d  ==>  ./$r"
			if [ ! -d $r ]; then mkdir -p $r; fi
			ln -sf $d/SPI*_[b,c]*.fits ./$r
		done
	fi
else   # get only data in shortlist
	echo ">> Build links to AORs in shortlist into Data dir"
	cd Data; echo " --> $PWD"
	if [ $dry == "T" ]; then
		echo "   ### dry mode ... do nothing ###"
	else
		for a in $(cat ../shortlist); do 
			for d in ${RAW}/$a/ch?/bcd; do 
				r=$(echo $d | cut -d\/ -f5-7) #; echo " $d  ==>  ./$r"
				if [ ! -d $r ]; then mkdir -p $r; fi
				echo "ln -sf $d/SPI*_[b,c]*.fits ./$r"
				ln -sf $d/SPI*_[b,c]*.fits ./$r
			done
		done
	fi
fi

if [ $dry != "T" ]; then
	echo " >> Built links for $(ls -d r????* | wc -l) AORs with $(ls -d r????*/ch? | wc -l) chan dirs"
fi

#exit 0
cd ..; echo " --> $PWD"

echo "# 2) link calib and other auxiliary files into cal and cdf"

if [ $dry == "T" ]; then
	echo "   ### dry mode ... do nothing ###"
else
    # need to write into cal so link contents
	if [ ! -d cal/flat1.fits ]; then ln -sf /n08data/Spitzer_pipe/cal/* cal/; fi
    # do not need to write into cdf, so link directory
	cp -r /home/moneti/softs/irac-pipe/cdf .
fi

echo "# setup for $(echo $RAW | cut -d\/ -f3-4) data reduction done ... enjoy!"
exit 0
#-----------------------------------------------------------------------------
