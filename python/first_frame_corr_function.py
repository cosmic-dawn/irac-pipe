#----------------------------------------------------------------------------
# module first_frame_corr_function.py
#----------------------------------------------------------------------------

from supermopex import *
from spitzer_pipeline_functions import *

import re
import sys,os,shutil

import numpy as np
from astropy.io import ascii
from astropy.io import fits
from scipy.interpolate import interp1d
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
    
    print('## Begin ffcorr job {:4d} - AOR {:8d} Ch {:}, {:3d} frames'.format(JobNo, AOR, Ch, Nframes))

    for fileNo in range(0,Nframes):
    
        MJD = MJDs[fileNo]
        BCDfilename = files[fileNo]
        
        #Check if we are in the Cryo mission
        if (MJD > WarmMJD):
            cryo = 0
            #print("  Warm mission: apply correction")  #DEBUG
        else:
            cryo = 1
            #print("  Cryo mission: nothing to correct")  #DEBUG
            
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
#            print('Wrote ' + str(fileNo +1) + ' of ' + str(Nframes) + ' No Correction, just copying ' + ImageFile) #,end='\r')
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
#            print('Wrote ' + str(fileNo +1) + ' of ' + str(Nframes) + ' ' + FFcorFile) #,end="\r")

    print('## Finished ffcorr job {:4d}: AOR {:8d} ch {:}'.format(JobNo, AOR, Ch))
    

#parse the arguments
usagestring ='%prog Job_Number'
parser = OptionParser()
parser = OptionParser(usage=usagestring)
(options, args) = parser.parse_args()

#fail if there aren't enough arguments
if len(args) < 1:
    parser.error("Incorrect number of arguments.")

#read job number
JobNo=int(args[0])

#Read the log file and get IRAC info
rawlog = ascii.read(LogTable,format="ipac")
log = rawlog[:][(rawlog['Instrument']=='IRAC').nonzero()]

#Get the size of the array
Nrows = log['Filename'].size

#read in the AOR properties log
AORlog = ascii.read(AORinfoTable,format="ipac")

#genreate a joblist for parallelization
JobList = make_joblist(log,AORlog)
Njobs = len(JobList)

if (JobNo > Njobs):
    die("Requested job number greater than number of jobs available " + str(Njobs) + "!");

#read in the flat data
print('Reading in flat data ', end='\r')
flatData = np.zeros([2,4,256,256],dtype=np.double) #delay data
#just doing ch1/2 for warm mission right now, leaving in option for others if/when those corrections become available
for cryo in range(0,1):
    for Ch in range(1,3):
        flatHDU = fits.open(flatFiles[cryo,Ch-1])
        flatData[cryo,Ch-1]=flatHDU[0].data

#read in the delay files
print('... and Frame Delay Data')

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

first_frame_correct(JobNo)
