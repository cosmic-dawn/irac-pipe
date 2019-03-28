#!/opt/local/bin/python

from supermopex import *
from spitzer_pipeline_functions import *

import re
import os,shutil

import numpy as np
from astropy.io import ascii
from astropy.io import fits
from scipy.interpolate import interp1d
from functools import partial
import multiprocessing as mp
from optparse import OptionParser

def first_frame_correct(JobNo):
    
    AOR = JobList['AOR'][JobNo]
    Ch = JobList['Channel'][JobNo]
    
    #make the list of files for this AOR and Channel
    LogIDX = ((log['Channel']==Ch) & (log['AOR']==AOR)).nonzero()  # get the indexes of files we should use
    files = log['Filename'][LogIDX]
    MJDs = log['MJD'][LogIDX]
    DCElist = log['DCE'][LogIDX]
    Nframes = len(files)
    
    print('Running Job ' + str(JobNo) + ' of ' + str(Njobs) + ' AOR ' + str(AOR) + ' Channel ' + str(Ch)) #,end="\r")
    
    for fileNo in range(0,Nframes):
    
        MJD = MJDs[fileNo]
        BCDfilename = files[fileNo]
        
        #Check if we are in the Cryo mission
        if (MJD > WarmMJD):
            cryo = 0
        else:
            cryo = 1
        
        #setup  some file names
        #Setup file suffixes re replace
        inputSuffix  = '_' + bcdSuffix + '.fits'  #used in search

        outputSuffix = '_' + corDataSuffix + '.fits'
        ImageFile     = re.sub(inputSuffix,outputSuffix,BCDfilename) #Image File
        
        outputSuffix = '_' + ffSuffix + '.fits'
        FFcorFile     = re.sub(inputSuffix,outputSuffix,BCDfilename) #First Frame Corrected File
        
        #remove output files
        rmCMD = 'rm -rf ' + FFcorFile
        os.system(rmCMD)
        while os.path.exists(FFcorFile):     #wait for file to be deleted
            wait = 1

        #Only do correction for warm mission given the data we have in hand
        if cryo:
            print('Wrote ' + str(fileNo +1) + ' of ' + str(Nframes) + ' No Correction, just copying ' + ImageFile) #,end='\r')
            shutil.copy(ImageFile,FFcorFile)  #just copy over the file
        else:
            #read the image
            imageHDU = fits.open(ImageFile)
            
            #get some file info
            exptime = imageHDU[0].header['EXPTIME']
            delay = imageHDU[0].header['FRAMEDLY']
            fluxconv = imageHDU[0].header['FLUXCONV']
            
            if (delay > delayInfo[len(delayInfo)-1].delay):
                DelayIDX = len(delayInfo)-2
                DelayFrac = (delay-delayInfo[DelayIDX].delay)/(delayInfo[DelayIDX+1].delay-delayInfo[DelayIDX].delay)
            else:
                DelayFrac = delay_to_index(delay)
                DelayIDX = int(DelayFrac)
                DelayFrac -= DelayIDX
            
            #interpolate the fits images to get the corrected frame
            corrframe = delayData[Ch-1,DelayIDX]*(1.0-DelayFrac)+delayData[Ch-1,DelayIDX+1]*DelayFrac
            corrframe *= fluxconv / exptime  #scale to the exposure time
            corrframe /= flatData[cryo,Ch-1]  #put the flat into the correction
            #do the correction
            imageHDU[0].data -= corrframe
            imageHDU.writeto(FFcorFile,overwrite='True')  #write out the final star subtracted image
            print('Wrote ' + str(fileNo +1) + ' of ' + str(Nframes) + ' ' + FFcorFile) #,end="\r")


#read in the log file
#rawlog = ascii.read(LogFile,format="commented_header",header_start=-1)
rawlog = ascii.read(LogTable,format="ipac")
#get just IRAC info
log = rawlog[:][(rawlog['Instrument']=='IRAC').nonzero()]

#Get the size of the array
Nrows = log['Filename'].size

#read in the AOR properties log
AORlog = ascii.read(AORinfoTable,format="ipac")

#genreate a joblist for parallelization
JobList = make_joblist(log,AORlog)
Njobs = len(JobList)

#read in the flat data
print('Reading in flat data')
flatData = np.zeros([2,4,256,256],dtype=np.double) #delay data
#just doing ch1/2 for warm mission right now, leaving in option for others if/when those corrections become available
for cryo in range(0,1):
    for Ch in range(1,3):
        flatHDU = fits.open(flatFiles[cryo,Ch-1])
        flatData[cryo,Ch-1]=flatHDU[0].data

#read in the delay files
print('Reading in Frame Delay Data')

#Read the delay files for the first frame correction
delayInfo = np.recfromtxt(FrameDelayFile,
                          dtype=[('frame', np.int),     #Number
                                 ('delay', np.float32)  #delay since last frame
                                 ]
                          )

#create a lookup index for the frame delay correction
delay_to_index =interp1d(delayInfo.delay,delayInfo.frame,bounds_error=False,fill_value='extrapolate')


#Read the fits files
delayData = np.zeros([2,len(delayInfo),256,256],dtype=np.double) #delay data
for i in range(0,len(delayInfo)):
    for Ch in range(1,3):
        delayFile = './cal/labdark.' + str(i) + '.' + str (Ch) + '.fits'
        delayHDU = fits.open(delayFile)
        delayData[Ch-1,i]=delayHDU[0].data

print("Starting correction with " + str(Nproc) + " threads.")
pool = mp.Pool(processes=Nproc)
results = pool.map(first_frame_correct, range(0,Njobs))

print("Done!")
#for i in range(1216,1250):
#first_frame_correct(1)
