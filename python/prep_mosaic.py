#-----------------------------------------------------------------------------
# prep_mosaic.py
# Requires: python 3
#-----------------------------------------------------------------------------
# Original from P.Capak; adapted by AMo. 6.dec.18 
# - work in a separate dirs for each chan, and in parallel. AMo 16.Dec
# - split preps from original: prepare needed tables. AMo 21.Dec
#-----------------------------------------------------------------------------

import sys,re,os,shutil
import numpy.ma as ma
from astropy.io import ascii
from astropy import units as u
from astropy.table import Table, Column, MaskedColumn
import multiprocessing as mp

from supermopex import *     # imports parameters from supermopex.py (local)

#-----------------------------------------------------------------------------

print("------ Begin prep_mosaic.py ------")
print("")

# read in the log file
rawlog = ascii.read(LogTable, format="ipac")
# get just IRAC info
logIRAC = rawlog[:][(rawlog['Instrument']=='IRAC').nonzero()]
logMIPS = rawlog[:][(rawlog['Instrument']=='MIPS').nonzero()]

# Do IRAC if there are IRAC files
if (len(logIRAC) == 0):
    print("ERROR: no files to process ... quitting")
    sys.exit()

# make the common FIF for the mosaics
FIFlist = OutputDIR + PIDname + '.irac.FIF.' + corDataSuffix + '.lst' 
iracFIF = OutputDIR + PIDname + '.irac.FIF.tbl' 

print("LogTable:    {}; length {}".format(LogTable, len(logIRAC)))
print("FIFlist:     {} (not used??)".format(FIFlist))
print("iracFIF:     {}".format(iracFIF))

cmd = 'mosaic.pl -n irac_FIF.nl -I ' + FIFlist + ' -O ' + TMPDIR
print(cmd)  
os.system(cmd)    

# Figure out number of channels and loop over them
ChMax = np.max(logIRAC['Channel'])
print("--- found {} channels to mosaic".format(ChMax))

print("------ Finished prep_mosaic.py ------")
