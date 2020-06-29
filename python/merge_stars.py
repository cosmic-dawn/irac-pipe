#-----------------------------------------------------------------------------
# Module:   merge_stars.py
# Purpose:  merge the root_bright.tbl catalogues
#-----------------------------------------------------------------------------

import numpy as np
from astropy.io import ascii
import sys, re, os
from astropy.coordinates import SkyCoord
from astropy import units as u
from astropy.table import Table, Column, MaskedColumn
from supermopex import *

#read the logfile and get IRAC info
rawlog = ascii.read(LogTable,format="ipac")
log = rawlog[:][(rawlog['Instrument']=='IRAC').nonzero()]

#Get the size of the array
Nrows = log['Filename'].size

#read the stars table and convert to the correct format
stars = ascii.read(StarTable,format="ipac")     # here read the GAIA-WISE merged catal
StarMatch = SkyCoord(stars['ra'],stars['dec'])  # i.e. global catal

#make an array of data to hold the star info
RA     = np.zeros(len(stars),dtype=np.double)
RAWt   = np.zeros(len(stars),dtype=np.double)
DEC    = np.zeros(len(stars),dtype=np.double)
DECWt  = np.zeros(len(stars),dtype=np.double)
Flux   = np.zeros([4,len(stars)],dtype=np.double)
FluxWt = np.zeros([4,len(stars)],dtype=np.double)

print(">> Reading Catalogs")
for ch in range(1,5):

    files = log['Filename'][np.where(log['Channel']==ch)]  # names of the spitzer catalogs
    Nfiles = files.size # number of catalogs for this channel
    print(">> Begin chan {:} with {:} files ... ".format(ch, Nfiles)) ##, end="\r")

    # loop through the images in this channel
    for i in range(0,Nfiles):
        # Setup file suffixes re replace    
        inputSuffix  = '_' + bcdSuffix + '.fits'  #used in search
        outputSuffix = '_' + BrightStarTableSuffix
        catfile = re.sub(inputSuffix,outputSuffix,files[i])  # get the name of the local catal, here _bright.tbl
        starData = ascii.read(catfile,format="ipac")         # read the data for this frame
#        print("- file {:} with {:} stars".format(i+1,len(starData)))   # DEBUG  #,end="\r")
        
        dataMatch = SkyCoord(starData['RA']*u.deg,starData['Dec']*u.deg) # put the local catalog RA/Dec into the matching format
        idx,d2d,d3d = dataMatch.match_to_catalog_sky(StarMatch)          # do the match to the global catal 
        if len(idx > 0):
            for n in range(len(idx)):
                print(" - file # {:4d}: {:40s} {:0.2f} arcsec ".format(i+1, files[i].split('/')[-1], 3600*d2d[n]), end="")
                flux_ratio = (starData['flux'][n] / stars[WISEchannel[ch-1]][idx[n]]) / WISEratio[ch-1] 
                print(" ==> ratio: {:0.4f} ; num: {:5d}  RA/Dec: {:8.4f} {:8.4f}".format(flux_ratio, idx[0], starData['RA'][n], starData['Dec'][n])) #; sys.exit()   # DEBUG
        
        # Put the fluxes and positions into the holding arrays
        for sidx in range(0,len(idx)):
            if(starData['delta_flux'][sidx]>0): #make sure error is valid
                
                # check the flux with respect to WISE and reject outliers
                # compute the sums of the weighted values and of the weights
                flux_ratio = (starData['flux'][sidx] / stars[WISEchannel[ch-1]][idx[sidx]]) / WISEratio[ch-1]
                if ((flux_ratio > 1.0/WISEratioCut) & (flux_ratio < WISEratioCut)):
                    wt = 1./(starData['delta_flux'][sidx]*starData['delta_flux'][sidx])
                    Flux[ch-1,idx[sidx]]   += starData['flux'][sidx] * wt
                    FluxWt[ch-1,idx[sidx]] += wt
            
                    wt = 1./(starData['delta_RA'][sidx]*starData['delta_RA'][sidx])
                    RA[idx[sidx]]    += starData['RA'][sidx] * wt
                    RAWt[idx[sidx]]  += wt
            
                    wt = 1./(starData['delta_Dec'][sidx]*starData['delta_Dec'][sidx])
                    DEC[idx[sidx]]   += starData['Dec'][sidx] * wt
                    DECWt[idx[sidx]] += wt
                    #print("   . Accepted star {:}: ratio = {:0.4f}".format(idx[sidx], flux_ratio))
                else:
                    print("   ## Rejected star {:}: ratio = {:0.4f}".format(idx[sidx], flux_ratio))
#        if len(idx > 0): sys.exit()
    print(">> merged {:} files for chan {:}".format(i,ch)   )  # finished channel

StarInfo=list()

# Now the weighted averages are the sums of the weighted values / sums of the weights
for i in range(0,len(stars)):
    if (RAWt[i]>0):
        oneStar=list()
        oneStar.append(stars[StarIDcol][i])

        #get the Spitzer RA/DEC
        oneStar.append(RA[i]/RAWt[i])
        oneStar.append(DEC[i]/DECWt[i])

        #get the fluxes
        for ch in range(1,5):
            if(Flux[ch-1,i]>0):
                oneStar.append(Flux[ch-1,i]/FluxWt[ch-1,i])
            else:
                oneStar.append(0.0)

        #Copy over the info from WISE
        oneStar.append(stars['ra'][i])
        oneStar.append(stars['dec'][i])
        oneStar.append(stars['w1'][i])
        oneStar.append(stars['w2'][i])
        oneStar.append(stars['w3'][i])
        oneStar.append(stars['w4'][i])
        StarInfo.append(oneStar)

if (len(StarInfo) > 0):
    data = Table(rows=StarInfo,names=['ID','ra','dec','ch1','ch2','ch3','ch4','wRA','wDEC','w1','w2','w3','w4'])
    ascii.write(data,RefinedStarCat,format="ipac",overwrite=True)
    print(">> Done - wrote Products/stars.refined.tbl with {:} entries".format(len(StarInfo)))
else: 
    print(">> No bright stars ... write empty stars.refined table")
    os.system("cp refined.tbl Products/stars.refined.tbl")
