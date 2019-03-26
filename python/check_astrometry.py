#!/opt/local/bin/python

from supermopex import *
from spitzer_pipeline_functions import *

import numpy as np
from astropy.io import ascii
from astropy.table import Table, Column, MaskedColumn, hstack
from functools import partial
import multiprocessing as mp


#read in the log file
#rawlog = ascii.read(LogFile,format="commented_header",header_start=-1)
rawlog = ascii.read(LogTable,format="ipac")

#get just IRAC info
log = rawlog[:][(rawlog['Instrument']=='IRAC').nonzero()]

#get the list of AORs
AORlist = list(set(log['AOR']))
Naor = len(AORlist)

#make a list of frame indexes for each AORS
#also a list of output data to collect results
JobList=list()
JobNo=0
for aorIDX in range(0,Naor):
#    IDMax = np.max(log['ExposureID'][(log['AOR']==AORlist[aorIDX]).nonzero()])
#    for ID in range(0,IDMax+1):
     IDlist = list(set(log['ExposureID'][(log['AOR']==AORlist[aorIDX]).nonzero()]))
     for ID in IDlist:
        ChMax = np.max(log['Channel'][((log['AOR']==AORlist[aorIDX])&(log['ExposureID']==ID)).nonzero()])
        JobList.append([JobNo,AORlist[aorIDX],ID,ChMax])
        JobNo+=1

JobList = Table(rows=JobList,names=['JobNo','AOR','ExposureID','ChannelMax'])

#Get the size of the array
Nrows = len(JobList)

#Read the refined fluxes and postions
StarData = ascii.read(StarTable,format="ipac") #read the data
StarMatch = SkyCoord(StarData['ra'],StarData['dec'])


print("Starting astrometry check with " + str(Nproc) + " threads.")

pool = mp.Pool(processes=Nproc)
results = pool.map(partial(check_astrometry,log=log,Nrows=Nrows,JobList=JobList,AstrometryStars=StarData), range(0,Nrows))
pool.close()

#for i in range(0,Nrows):
#fix_astrometry(i)

DCElist = log['DCE']
OutputList=list()
for DCE in DCElist:
    ID = (log['DCE']==DCE).nonzero()
    AOR = int(log['AOR'][ID])
    ExposureID = int(log['ExposureID'][ID])
    JobID = int(JobList['JobNo'][((JobList['AOR']==AOR)&(JobList['ExposureID']==ExposureID)).nonzero()]) # get the job number for this
    OutputList.append([results[JobID][1],results[JobID][2],results[JobID][3],results[JobID][4]])

#add in some columns from the log first, then make table with astrometry
OutputTable = hstack([log['Filename','DCE','AOR','ExposureID','Channel','RA','DEC'],Table(rows=OutputList,names=['dRA','dDEC','error_dRA','error_dDEC'])])


#write output table
print("")
print("Writing astrometry corrections to " + str(AstrometryCheckFile))
ascii.write(OutputTable,AstrometryCheckFile,format="ipac",overwrite=True)

