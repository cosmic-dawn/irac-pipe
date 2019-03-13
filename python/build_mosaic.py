#-----------------------------------------------------------------------------
# build_mosaic.py
# Requires: python 3
#-----------------------------------------------------------------------------
# Original from P.Capak; adapted by AMo. 6.dec.18 
# - work in a separate dirs for each chan, and in parallel. AMo 16.Dec
# - split build proper from original, takes channel as argument. AMo 21.Dec
#-----------------------------------------------------------------------------

import sys,re,os,shutil
import numpy.ma as ma
from astropy.io import ascii
from astropy import units as u
from astropy.table import Table, Column, MaskedColumn
import multiprocessing as mp

from supermopex import *     # parameters

#-----------------------------------------------------------------------------

def mosaic(Ch):

    print("--- Build mosaic for Chan {}".format(Ch))

    # list of files
    filenames = logIRAC['Filename'][(rawlog['Channel']==int(Ch)).nonzero()]
    # chan-specific temp dir:
    chandir = TMPDIR +Ch+ '/'
    print("--- Chandir is {}".format(chandir))

    # input lists  
    imagelist = OutputDIR + PIDname + '.irac.' + Ch + '.' + SubtractedSuffix + '.lst' 
    masklist  = OutputDIR + PIDname + '.irac.' + Ch + '.' + starMaskSuffix   + '.lst' 
    unclist   = OutputDIR + PIDname + '.irac.' + Ch + '.' + ScaledUncSuffix  + '.lst' 
    
    # copy FIF files into place
    shutil.copy(iracFIF, 'FIF.tbl')
    shutil.copy(iracFIF, chandir+'FIF.tbl')

    # Run Mosaic - by default with beginMosaic.nl 
    cmd = 'mosaic.pl -n beginMosaic.nl -I ' + imagelist + ' -S ' + unclist + ' -d ' + masklist + ' -M ' + IRACPixelMasks[int(Ch)-1] + ' -O ' + chandir
    print(cmd)
    os.system(cmd)

    # copy rmask back to directory
    Nfiles = len(filenames)
    file = 0 #counters for file number
    for filename in filenames:
        file += 1

        inputSuffix  = '_' + bcdSuffix + '.fits'  #used in search
        outputSuffix = '_' + rmaskSuffix + '.fits' 
        basename = re.sub(inputSuffix,'',re.split('/',filename)[-1])

        rmaskimage = chandir + 'Rmask-mosaic/' + basename + '_' + SubtractedSuffix + outputSuffix
        outputMask =  re.sub(inputSuffix, outputSuffix, filename)  #masked pixel input

        print("Copy file {}: {} to {}".format(file, rmaskimage, outputMask))
        shutil.copy(rmaskimage,outputMask)

    # move the files
    mosaiccov = OutputDIR + PIDname + '.irac.' + Ch + '.mosaic_cov.fits'
    shutil.move(chandir + 'Combine-mosaic/mosaic_cov.fits', mosaiccov)

    mosaicstd = OutputDIR + PIDname + '.irac.' + Ch + '.mosaic_std.fits'
    shutil.move(chandir + 'Combine-mosaic/mosaic_std.fits', mosaicstd)

    mosaicunc = OutputDIR + PIDname + '.irac.' + Ch + '.mosaic_unc.fits'
    shutil.move(chandir + 'Combine-mosaic/mosaic_unc.fits', mosaicunc)

    mosaic    = OutputDIR + PIDname + '.irac.' + Ch + '.mosaic.fits'
    shutil.move(chandir + 'Combine-mosaic/mosaic.fits', mosaic)

    medmosaic = OutputDIR + PIDname + '.irac.' + Ch + '.median_mosaic.fits'
    shutil.move(chandir + 'Combine-mosaic/median_mosaic.fits', medmosaic)

    medmosaicunc = OutputDIR + PIDname + '.irac.' + Ch + '.median_mosaic_unc.fits'
    shutil.move(chandir + 'Combine-mosaic/median_mosaic_unc.fits', medmosaicunc)

    print("Finished mosaic for Ch{}".format(Ch))

#-----------------------------------------------------------------------------

Ch = sys.argv[1]
print("------ Begin build_mosaic.py for Ch {} ------".format(Ch))

#-----------------------------------------------------------------------------

# read in the log file
# print("LogTable:    {}".format(LogTable))
rawlog = ascii.read(LogTable, format="ipac")

# get just IRAC info
logIRAC = rawlog[:][(rawlog['Instrument']=='IRAC').nonzero()]

# Do IRAC if there are IRAC files
if (len(logIRAC) == 0):
    print("ATTN: No files to process in Channel {} ... quitting".format(Ch))
    sys.exit()

# make the common FIF for the mosaics
#FIFlist = OutputDIR + PIDname + '.irac.FIF.' + corDataSuffix + '.lst' 
iracFIF = OutputDIR + PIDname + '.irac.FIF.tbl' 
shutil.copy('FIF.tbl', iracFIF)

print("LogTable:    {}; length {}".format(LogTable, len(logIRAC)))
#print("FIFlist:     {} (not used??)".format(FIFlist))
print("iracFIF:     {}".format(iracFIF))
print("")

mosaic(Ch)
      	
print("------ Finished build_mosaic.py for Ch {} ------".format(Ch))
#-----------------------------------------------------------------------------

