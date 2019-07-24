
from supermopex import *
from spitzer_pipeline_functions import *
import numpy as np
import numpy.ma as ma
from astropy.io import ascii
from astropy import units as u
from astropy.table import Table, Column, MaskedColumn
import re, sys, os, shutil
from functools import partial
import multiprocessing as mp

#read in the log file and get irac info
rawlog = ascii.read(LogTable,format="ipac")
logIRAC = rawlog[:][(rawlog['Instrument']=='IRAC').nonzero()]

# AMo: name of table with all tiles - before discarding those tiles with no data
AllTiles = TMPDIR + 'AllTiles.tbl'
locnode = os.uname().nodename.split('.')[0]  # name of process node

# AMo: to avoid doing this all the time when testing bottom part.
if not os.path.isfile(AllTiles):
    #make the common FIF for the mosaics
    FIFlist = OutputDIR + PIDname + '.irac.FIF.' + corDataSuffix + '.lst' 

    # now run fiducial_frame.pl (wrapper forFIF  fiducial_image_frame) to build header_list.tbl
    print('# Run FIF to figure out mosaic geometry (build {:}header_list.tbl)'.format(TMPDIR))
    logfile = 'setup_tiles.log'
    cmd = 'mosaic.pl -n irac_FIF.nl -I {:} -O {:} > {:} 2>&1'.format(FIFlist, TMPDIR , logfile)
    print("# Command line is:\n  " + cmd)
    os.system(cmd)

    # if all went well there should be a FIF.tbl file in the work dir.  
    if os.path.isfile('FIF.tbl'):
        print('# mosaic.pl run successful; Built header list and FIF.tbl file ... contiuue')
    else:
        print("# ERROR: FIF.tbl file not build; check {:} ... quitting".format(logfile))
        sys.exit(5)

    # copy the FIF to OutputDIR
    iracFIF = OutputDIR + PIDname + '.irac.FIF.tbl' 
    shutil.move('FIF.tbl',iracFIF)

    # read in the FIF
    FIFfile = open(iracFIF,"r")
    
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
    print("# Split mosaic into Nx={} x Ny={} tiles".format(Nx,Ny))

    # make new FIFs for each tile
    tileID=0
    FIFlist = list()
    for y in range(0,Ny):
        for x in range(0,Nx):
            xc = (x+0.5)*MosaicTileSize-MosaicEdge-CRPIX1
            yc = (y+0.5)*MosaicTileSize-MosaicEdge-CRPIX2
            # new CRPIX values must not be interger values
            if (xc % 1 == 0.0): xc += 0.5
            if (yc % 1 == 0.0): yc += 0.5

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
                    
            tileFIFfile.close()  # write it out
            tileID+=1

    print("# Wrote FIF files for {} tiles".format(tileID))
#    print("# Now build job list")

    #Make a job list for the mosaic tiles
    #Figure out number of channels and loop over them
    ChMax = np.max(logIRAC['Channel'])

    JobList = list()
    #initialize frame list to zero, we will run mosaic geometry to figure out what to actually use
    Nframes = 0 
    for tileIDX in range(0,len(FIFlist)):
        for Ch in range(1,ChMax+1):
            JobList.append([FIFlist[tileIDX],(tileIDX+1),Ch,Nframes])
    JobList = Table(rows=JobList,names=['FIF','TileNumber','Channel','NumFrames'])
    Njobs = len(JobList)

    #write it out
    ascii.write(JobList, AllTiles, format="ipac",overwrite=True)
    print("# Wrote list of all tiles: {:} with {:} jobs".format(AllTiles, Njobs))

else:
    print("# Using previously built list of all tiles {:}".format(AllTiles))
    JobList = ascii.read(AllTiles, format="ipac")
    Njobs = len(JobList)


# now lets run mosaic geometry to see if there are any files in each tile
# and restrict job list to "occupied" tiles
nproc = int(2*Nproc/3)

print("# Find exposures for each tile with {} threads".format(nproc))
pool = mp.Pool(processes=nproc)
results = pool.map(partial(run_mosaic_geometry,JobList=JobList), range(0,Njobs))
pool.close()

JobList['NumFrames']=results

#Find the tiles with frames associated
GoodTiles = JobList[:][np.where(JobList['NumFrames'] > 0)]

#Write list of tiles with data to an output
print("")
print("# Write list of mosaic tiles with data (job list) to {:}".format(TileListFile))
ascii.write(GoodTiles, TileListFile, format="ipac", overwrite=True)
