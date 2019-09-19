#!/opt/local/bin/python

import sys,os
import numpy as np
from astropy.io import ascii
from supermopex import *
from spitzer_pipeline_functions import *
import multiprocessing as mp
import pickle

def run_subtractmedians(JobNo):
    cmd = "cd " + RootDIR + "; " + pythonCMD + " subtract_medians_function.py " + str(JobNo)
    os.system(cmd)

#Read the log file and get just IRAC info
rawlog = ascii.read(LogTable,format="ipac")
log = rawlog[:][(rawlog['Instrument']=='IRAC').nonzero()]

#Get the size of the array
Nrows = log['Filename'].size

#read in the AOR properties log
AORlog = ascii.read(AORinfoTable,format="ipac")

#genreate a joblist for parallelization
JobList = make_joblist(log,AORlog)
Njobs = len(JobList)

# AMo: write out the joblist
JobListName = OutputDIR + 'jobs.subtract_medians'
ascii.write(JobList, JobListName, format="ipac",overwrite=True)    
print("Wrote job list {} with {} jobs".format(JobListName, Njobs))

### would be good to write it also in some internal format that can be read quickly
### BUT file written with pickle is larger that ascii file!!!!!
### And not yet clear how to read it back; so skip for now.

#JobListName = OutputDIR + PIDname + '.jobs_subtract_medians.dat'
#with open(JobListName, 'wb') as ff:
#    pickle.dump(JobList, ff)
#print("Wrote job list to binary file {}".format(JobListName))

#sys.exit()
#-----------------------------------------------------------------------------

print("Subtracting medians with " + str(Nproc) + " threads.")

pool = mp.Pool(processes=Nthred)
results = pool.map(run_subtractmedians, range(0,Njobs))

print("Done!")

