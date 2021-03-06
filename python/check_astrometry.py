#-----------------------------------------------------------------------------
# module check_astrometry.py (par)
#-----------------------------------------------------------------------------

from supermopex import *
from spitzer_pipeline_functions import *

import sys
import numpy as np
from astropy.io import ascii
from astropy.table import Table, Column, MaskedColumn, hstack
from functools import partial
import multiprocessing as mp


#read in the log file and get IRAC info
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
ascii.write(JobList, OutputDIR + 'jobs.check_astrometry.tbl', format="ipac",overwrite=True)  

#Get the size of the array
Njobs = len(JobList)

#Read the refined fluxes and postions
StarData = ascii.read(StarTable,format="ipac") #read the data

#fill in missing proper motions with zeros
StarData['pmra'].fill_value=0.0
StarData['pmdec'].fill_value=0.0
StarData['pmra_error'].fill_value=0.0
StarData['pmdec_error'].fill_value=0.0
StarData['parallax'].fill_value=1e-8


print("Starting check_astrometry: {:} jobs with {:} threads".format(Njobs, Nthred))

pool = mp.Pool(processes=Nthred)
results = pool.map(partial(check_astrometry,log=log,Nrows=Njobs,JobList=JobList,AstrometryStars=StarData), range(0,Njobs))
pool.close()

#for i in range(0,Njobs):
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

