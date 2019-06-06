#!/opt/local/bin/python

from supermopex import *
from spitzer_pipeline_functions import *

import numpy as np
from astropy.io import ascii
from astropy.table import Table, Column, MaskedColumn, hstack
from functools import partial
import multiprocessing as mp

#Read the log file and get IRAC info
rawlog = ascii.read(LogTable,format="ipac")
log = rawlog[:][(rawlog['Instrument']=='IRAC').nonzero()]

#get the list of AORs
AORlist = list(set(log['AOR']))
Naor = len(AORlist)

#make a list of frame indexes for each AORS
#also a list of output data to collect results
JobList=list()
JobNo=0
for aorIDX in range(0,Naor):
     IDlist = list(set(log['ExposureID'][(log['AOR']==AORlist[aorIDX]).nonzero()]))
     for ID in IDlist:
          ChMax = np.max(log['Channel'][((log['AOR']==AORlist[aorIDX])&(log['ExposureID']==ID)).nonzero()])
          JobList.append([JobNo,AORlist[aorIDX],ID,ChMax])
          JobNo+=1

JobList = Table(rows=JobList,names=['JobNo','AOR','ExposureID','ChannelMax'])

#Get the size of the array
Nrows = len(JobList)
#Read the refined fluxes and postions
StarData = ascii.read(GaiaTable,format="ipac") 


print("Starting fix_astrometry on {} jobs with {} threads.".format(Nrows, Nproc))

pool = mp.Pool(processes=Nproc)
results = pool.map(partial(fix_astrometry,log=log,Nrows=Nrows,JobList=JobList,AstrometryStars=StarData), range(0,Nrows))
pool.close()

DCElist = log['DCE']
OutputList=list()
for DCE in DCElist:
    ID = (log['DCE']==DCE).nonzero()
    AOR = int(log['AOR'][ID])
    ExposureID = int(log['ExposureID'][ID])
    JobID = int(JobList['JobNo'][((JobList['AOR']==AOR)&(JobList['ExposureID']==ExposureID)).nonzero()]) # get the job number for this
    OutputList.append([JobID,results[JobID][1],results[JobID][2],results[JobID][3],results[JobID][4],results[JobID][5]])

#add in some columns from the log first, then make table with astrometry
OutputTable = hstack([log['Filename','DCE','AOR','ExposureID','Channel','RA','DEC'],Table(rows=OutputList,names=['JobID','dRA','dDEC','error_dRA','error_dDEC','Nstars'])])

#write output table
print("")
print("Writing astrometry corrections to " + str(AstrometryFixFile))
ascii.write(OutputTable,AstrometryFixFile,format="ipac",overwrite=True)
