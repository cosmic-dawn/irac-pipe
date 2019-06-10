
from supermopex import *
from spitzer_pipeline_functions import *
import numpy as np
import numpy.ma as ma
from astropy.io import ascii
from astropy import units as u
from astropy.table import Table, Column, MaskedColumn
import re
import os,shutil
from functools import partial
import multiprocessing as mp

#read in the log file
#log = ascii.read(LogFile,format="commented_header",header_start=-1)
rawlog = ascii.read(LogTable,format="ipac")
#get just IRAC info
logIRAC = rawlog[:][(rawlog['Instrument']=='IRAC').nonzero()]
logMIPS = rawlog[:][(rawlog['Instrument']=='MIPS').nonzero()]

#Do IRAC if there are IRAC files
if (len(logIRAC) > 0):

    #make the common FIF for the mosaics
    FIFlist = OutputDIR + PIDname + '.irac.FIF.' + corDataSuffix + '.lst' 
    iracFIF = OutputDIR + PIDname + '.irac.FIF.tbl' 

    print('Running FIF to figure out mosaic geometry.')
    cmd = 'mosaic.pl -n irac_FIF.nl -I ' + FIFlist + ' -O ' + TMPDIR
    os.system(cmd)
    
    #make a copy of the FIF
    shutil.copy('FIF.tbl',iracFIF)
    
    #read in the FIF
    FIFfile = open('FIF.tbl',"r")
    FIFlines = FIFfile.readlines()
    linecnt=0
    for line in FIFlines:
        items = line.split()
        
        if (len(items)>2):
            if(items[1] == 'CRPIX1'):
                CRPIX1line=linecnt
                CRPIX1 = np.double(items[3])
            if(items[1] == 'CRPIX2'):
                CRPIX2line=linecnt
                CRPIX2 = np.double(items[3])
            if(items[1] == 'NAXIS1'):
                NAXIS1line=linecnt
                NAXIS1=int(items[3])
            if(items[1] == 'NAXIS2'):
                NAXIS2line=linecnt
                NAXIS2=int(items[3])
        linecnt+=1

    #Figure out number of tiles
    Nx = int(np.floor(np.double(NAXIS1)/MosaicTileSize)+1)
    Ny = int(np.floor(np.double(NAXIS2)/MosaicTileSize)+1)
    Ntot = Nx*Ny

    #make new FIFs for each tile
    tileID=0
    FIFlist = list()
    for y in range(0,Ny):
        for x in range(0,Nx):
            xc = (x+0.5)*MosaicTileSize-MosaicEdge-CRPIX1
            yc = (y+0.5)*MosaicTileSize-MosaicEdge-CRPIX2
            
            tileFIFfilename = OutputDIR + PIDname + ".irac.tile." + str(tileID+1) + ".FIF.tbl"
            FIFlist.append(tileFIFfilename)
            tileFIFfile = open(tileFIFfilename,"w")
            
            linecnt=0
            for line in FIFlines:
                if((linecnt == CRPIX1line) | (linecnt == CRPIX2line) | (linecnt == NAXIS1line) | (linecnt == NAXIS2line)):
                    items = line.split()
                    
                    if (linecnt == CRPIX1line):
                        items[3] = str(xc)
                    if (linecnt == CRPIX2line):
                        items[3] = str(yc)
                    if (linecnt == NAXIS1line):
                        items[3] = str(MosaicTileSize + MosaicEdge*2.0)
                    if (linecnt == NAXIS2line):
                        items[3] = str(MosaicTileSize + MosaicEdge*2.0)
                        
                    FIFline = ''
                    for item in items:
                        FIFline += item + ' '
                    FIFline+='\n'
                    tileFIFfile.write(FIFline)
                    
                else:
                    tileFIFfile.write(line)
                linecnt+=1
                    
            tileFIFfile.close()
            tileID+=1

    #Make a job list for the mosaic tiles
    #Figure out number of channels and loop over them
    ChMax = np.max(logIRAC['Channel'])

    JobList=list()
    Nframes=0 #initialize frame list to zero, we will run mosaic geometry to figure out what to actually use
    for tileIDX in range(0,len(FIFlist)):
        for Ch in range(1,ChMax+1):
            JobList.append([FIFlist[tileIDX],(tileIDX+1),Ch,Nframes])
    JobList = Table(rows=JobList,names=['FIF','TileNumber','Channel','NumFrames'])

    Njobs = len(JobList)

    print("Finding exposures for each tile with " + str(Nproc) + " threads.")

    #now lets run mosaic geometry to see if there are any files in each tile
    pool = mp.Pool(processes=Nproc)
    results = pool.map(partial(run_mosaic_geometry,JobList=JobList), range(0,Njobs))
    pool.close()

    JobList['NumFrames']=results

    #Find the tiles with frames associated
    GoodTiles = JobList[:][np.where(JobList['NumFrames'] > 0)]
    #BadTiles = JobList[:][np.where(JobList['NumFrames'] == 0)]

    #Write list of tiles with data to an output
    print("")
    print("Writing list of mosaic tiles to " + str(TileListFile))
    ascii.write(GoodTiles,TileListFile,format="ipac",overwrite=True)


