#!/opt/local/bin/python


import numpy as np
from astropy.io import ascii
import re
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
stars = ascii.read(StarTable,format="ipac") #read the data

StarMatch = SkyCoord(stars['ra'],stars['dec'])

#make an array of data to hold the star info
RA = np.zeros(len(stars),dtype=np.double)
RAWt = np.zeros(len(stars),dtype=np.double)
DEC = np.zeros(len(stars),dtype=np.double)
DECWt = np.zeros(len(stars),dtype=np.double)
Flux = np.zeros([4,len(stars)],dtype=np.double)
FluxWt = np.zeros([4,len(stars)],dtype=np.double)

print("Reading Catalogs")
for ch in range(1,5):

    files = log['Filename'][np.where(log['Channel']==ch)]  # names of the spitzer catalogs
    Nfiles = files.size # number of catalogs for this channel
    
    #loop through the images in this channel
    for i in range(0,Nfiles):
        #Setup file suffixes re replace    
        inputSuffix  = '_' + bcdSuffix + '.fits'  #used in search
        outputSuffix = '_' + BrightStarTableSuffix
        catfile = re.sub(inputSuffix,outputSuffix,files[i])  #get the name of the file we are reading
        starData = ascii.read(catfile,format="ipac") #read the data
        
        dataMatch = SkyCoord(starData['RA']*u.deg,starData['Dec']*u.deg) #put the catalog into the matching format
        idx,d2d,d3d=dataMatch.match_to_catalog_sky(StarMatch) #do the match
        
        progress = "Ch " + str(ch) + "; File " + str(i+1) + " of " + str(Nfiles)
        print(progress) #,end="\r")
        
        #Put the fluxes and positions into a holding array
        for sidx in range(0,len(idx)):
            if(starData['delta_flux'][sidx]>0): #make sure error is valid
                
                #check the flux with respect to WISE and reject outliers
                flux_ratio = (starData['flux'][sidx] / stars[WISEchannel[ch-1]][idx[sidx]])/WISEratio[ch-1]
                if ((flux_ratio > 1.0/WISEratioCut) & (flux_ratio < WISEratioCut)):
                    Flux[ch-1,idx[sidx]]+=starData['flux'][sidx]/(starData['delta_flux'][sidx]*starData['delta_flux'][sidx])
                    FluxWt[ch-1,idx[sidx]]+=1.0/(starData['delta_flux'][sidx]*starData['delta_flux'][sidx])
            
                    RA[idx[sidx]]+=starData['RA'][sidx]/(starData['delta_RA'][sidx]*starData['delta_RA'][sidx])
                    RAWt[idx[sidx]]+=1.0/(starData['delta_RA'][sidx]*starData['delta_RA'][sidx])
            
                    DEC[idx[sidx]]+=starData['Dec'][sidx]/(starData['delta_Dec'][sidx]*starData['delta_Dec'][sidx])
                    DECWt[idx[sidx]]+=1.0/(starData['delta_Dec'][sidx]*starData['delta_Dec'][sidx])
    print("")#line return after catalogs

StarInfo=list()



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

        #Copy over teh info from WISE
        oneStar.append(stars['ra'][i])
        oneStar.append(stars['dec'][i])
        oneStar.append(stars['w1'][i])
        oneStar.append(stars['w2'][i])
        oneStar.append(stars['w3'][i])
        oneStar.append(stars['w4'][i])
        StarInfo.append(oneStar)


data = Table(rows=StarInfo,names=['ID','ra','dec','ch1','ch2','ch3','ch4','wRA','wDEC','w1','w2','w3','w4'])
ascii.write(data,RefinedStarCat,format="ipac",overwrite=True)


