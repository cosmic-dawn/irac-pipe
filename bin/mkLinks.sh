#!/bin/sh

#-----------------------------------------------------------------------------
# File: mkLinks.sh
# Author: A. Moneti - Dec.18
#-----------------------------------------------------------------------------
# Setup new directory for SPitzer/IRAC data processing .
# New directory should exist and should be given by WRK env. var.
# NB. probably best to run it on the node on which $WRK is found.
#-----------------------------------------------------------------------------

# link to the data from P.Capak
#RAW=/n08data/Spitzer/CDFS     # ==> /n08data/CDFS
#RAW=/n08data/Spitzer/NEP      # ==> /n08data/NEP
#RAW=/n08data/Spitzer/EGS      # ==> /n09data/EGS
#RAW=/n08data/Spitzer/HDFN     # ==> /n08data/HDFN
#RAW=/n08data/Spitzer/XMM-LSS  # ==> /n09data/XMM
#RAW=/n08data/Spitzer/COSMOS   # ==> /n09data/COSM
#RAW=/n09data/Spitzer/COSMOS_Data   # ==> /n09data/cosmctr    central part of COSMOS field
#RAW=/n09data/Spitzer/COSMOS_Data   # ==> /n09data/cosmos155   r155* AORs (45) of COSMOS field
RAW=/n09data/Spitzer/COSMOS_New     # ==> /n09data/COSnew      75 AORs

loc=$(pwd | cut -d\/ -f3)   # nominally name of Spitzer field 

if [ $loc == 'mini' ]; then loc=COSMOS; fi  
if [ $loc == 'COSnew' ]; then RAW=/n09data/Spitzer/COSMOS_New; fi 
#RAW=/n08data/Spitzer/$loc    

echo "Raw data linked from $RAW"  #; exit

if [ ! -d AllData ]; then mkdir AllData Data cal; fi

# link all relevant data to AllData; later (manually) mv to Data the
# AORs to preocess

echo "# 1) build raw data links to files into $RAW"

if [ ! -e shortlist ]; then  # get all the data
	echo ">> Build links to all raw data into AllData dir"
	cd AllData; echo " --> $PWD"
	for d in ${RAW}/r???*/ch?/bcd; do 
		r=$(echo $d | cut -d\/ -f5-7); echo " $d  ==>  ./$r"
		if [ ! -d $r ]; then mkdir -p $r; fi
		ln -sf $d/SPI*_[b,c]*.fits ./$r
	done
else   # get only data in shortlist
	echo ">> Build links to AORs in shortlist into Data dir"
	cd Data; echo " --> $PWD"
	for a in $(cat ../shortlist); do 
		for d in ${RAW}/$a/ch?/bcd; do 
			r=$(echo $d | cut -d\/ -f5-7) #; echo " $d  ==>  ./$r"
			if [ ! -d $r ]; then mkdir -p $r; fi
			echo "ln -sf $d/SPI*_[b,c]*.fits ./$r"
			ln -sf $d/SPI*_[b,c]*.fits ./$r
		done
	done
fi

#exit 0
echo " >> Built links for $(ls -d r????* | wc -l) AORs with $(ls -d r????*/ch? | wc -l) channel dirs"
cd ..; echo " --> $PWD"

# link these to version on /n09data/Spitzer
echo "# 2) link calib and other auxiliary files into cal and cdf"

# need to write into cal so link contents
if [ ! -d cal/flat1.fits ]; then ln -sf /n08data/Spitzer_pipe/cal/* cal/; fi
# do not need to write into cdf, so link directory
ln -sf /home/moneti/sls/cdf .

echo "# setup for $(echo $RAW | cut -d\/ -f3-4) data reduction done ... enjoy!"
exit 0
#-----------------------------------------------------------------------------
