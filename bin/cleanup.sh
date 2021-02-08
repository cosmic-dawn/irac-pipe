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
if [[ "${@: -1}" =~ 'dry' ]]; then dry=T; else dry=F; fi

# check that WRK is defined
if [[ -z "$WRK" ]]; then 
    echo " ERROR: \$WRK (workdir) environment variable not defined ... quitting" 
    exit 20
fi

cd $WRK; echo " --> $PWD"
field=$(pwd | cut -d\/ -f3)   # nominally name of Spitzer field 

if [ -e supermopex.py ]; then
	odir=$(grep 'OutputDIR  =' supermopex.py | cut -d\' -f2 | tr -d \/)
	RAW=$(grep 'RawDataDir =' supermopex.py | cut -d\' -f2 | tr -d \/)
else
	echo "supermopex.py not found; quitting"  
	exit 0
fi

#-----------------------------------------------------------------------------

naor=$(ls -d $RAW/r???* | wc -l)
echo ">> Field is $field; raw data linked from $RAW ... "
echo ">> Found $naor AORs in $RAW ... OK?"  #; exit

# move or delete?
if [ $# -eq 1 ]; then
	if [ -d $1 ]; then
		echo " move products to $1"
		keep="T"
	else
		echo "ERROR: output directory $1 not found - quitting"
		exit 3
	fi
else
	echo " remove products ..."
	keep="F"
fi

echo ">> ...  ^C to quit if not correct"  
sleep 10 #; exit

#-----------------------------------------------------------------------------

# check that raw data dir exists
if [ ! -d $RAW ]; then
	echo "ERROR: $RAW not found - quitting!"
	exit 1
fi

# delete intermediate products from raw data dir
for f in $RAW/r*/ch?/bcd; do 
	echo "- now clean $f"
	rm -f $f/SPI*_[f-z]*.fits $f/SPI*.tbl
done

if [[ $keep == "T" ]]; then
	echo "## move command etc. files to $1"
	mv *.sh *.py *.out *.err addkey* FIF.tbl $1
	mv medians $odir irac.log make_tiles* countFiles.dat  $1
else
	echo "## delete command etc. files"
	rm -f *.sh *.py *.out build.* *.err addkey* FIF.tbl cdf/log_*  # supermopex.py
	rm -rf medians $odir countFiles.dat irac.log 
fi

rm -rf temp/* __pycache__ 


exit 0
#rm *.lst *.fits *stars
#cp ~/sls/irac.sh .

#--------------------------------------------------------------------------
