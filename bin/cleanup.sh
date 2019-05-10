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
if [ -e supermopex.py ]; then
	odir=$(grep 'OutputDIR  =' supermopex.py | cut -d\' -f2 | tr -d \/)
	rdir=$(grep 'RawDataDir =' supermopex.py | cut -d\' -f2 | tr -d \/)
else
	echo "supermopex.py not found; "
	odir=Products
	rdir=Data
fi

# move or delete?
if [ $# -eq 1 ]; then
	if [ -d $1 ]; then
		echo " move products to $1"
		keep="T"
	else
		echo " remove products ..."
		keep="F"
	fi
fi

# check that raw data dir exists
if [ ! -d $rdir ]; then
	echo "ERROR: $rdir not found - quitting!"
	exit 1
fi

# delete intermediate products from raw data dir
for f in $rdir/r*/ch?/bcd; do 
	echo "- now clean $f"
	rm -f $f/SPI*_[f-z]*.fits $f/SPI*.tbl
done

if [[ $keep == "T" ]]; then
	echo "## move command etc. files to $1"
	mv *.sh *.py *.out *.qall *.err addkey* FIF.tbl $1
	mv medians $odir irac.log make_tiles* countFiles.dat  $1
	rm -rf temp __pycache__ 
else
	echo "## delete command etc. files"
	rm -f *.sh *.py *.out build.* *.err addkey* FIF.tbl cdf/log_*  # supermopex.py
	rm -rf temp __pycache__ medians/* $odir/* countFiles.dat irac.log make_tiles*
fi


exit 0
#rm *.lst *.fits *stars
#cp ~/sls/irac.sh .

#--------------------------------------------------------------------------
