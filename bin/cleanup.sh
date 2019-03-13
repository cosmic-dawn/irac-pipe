#!/bin/sh

#-----------------------------------------------------------------------------
# File:  cleanup.sh
# Author: A. Moneti - Dec.18
#-----------------------------------------------------------------------------
# Clean up the current work dir: 
# - if an argument is given and it is a directory, move all products and 
#   scripts etc. to that dir 
# - if no argument, then delete products and scripts
# In both cases:
# - keep the raw data (links) 
# - but delete other products in the Data/rnnn/ch?/bcd dirs
# - delete contents of temp dir
#-----------------------------------------------------------------------------

#cd $WRK
odir=$(grep 'OutputDIR  =' supermopex.py | cut -d\' -f2 | tr -d \/)
rdir=$(grep 'RawDataDir =' supermopex.py | cut -d\' -f2 | tr -d \/)

echo $rdir
echo $odir  ; exit

if [ $# -eq 1 ]; then
	if [ -d $1 ]; then
		echo " move products to $1"
		keep=1
	else
		echo " remove products ..."
		keep=0
	fi
fi

for f in $rdir/r*/ch?/bcd; do 
	echo "- now clean $f"
	rm $f/SPI*_[f-z]*.fits $f/SPI*.tbl
done

echo " remove command etc. files"
if [ $keep -eq 1 ]; then
	mv *.sh *.py *.out *.qall *.err addkey* FIF.tbl $1
	mv medians $odir  cdf  supermopex.py   $1
	rm -rf temp__pycache__ 
else
	rm -f *.sh *.py *.out *.qall *.err addkey* FIF.tbl cdf/log_*  # supermopex.py
	rm -rf temp __pycache__ medians/* $odir/*
fi

#rm *.lst *.fits *stars
#cp ~/sls/irac.sh .

#--------------------------------------------------------------------------
