#!/opt/local/bin/python

import numpy as np
from astropy.io import ascii
from supermopex import *
from spitzer_pipeline_functions import *
import os
import multiprocessing as mp

#Read the log file
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

print(JobList)
print("There are " + str(Njobs) + " jobs.")
