#----------------------------------------------------------------------------
# module subtract_stars.py                                                       
#----------------------------------------------------------------------------

import sys,os
import numpy as np
from astropy.io import ascii
from supermopex import *
from spitzer_pipeline_functions import *
import multiprocessing as mp

def run_subtractstars(JobNo):
    cmd = "cd " + RootDIR + "; " + pythonCMD + " subtract_stars_function.py " + str(JobNo)
    os.system(cmd)

#------------------------------------------------------------------

if (SubtractBrightStars == False):
    print("#### ---------------------------------------- ####")
    print("#### ATTN: Bright stars subtraction DISPABLED ####")
    print("#### ---------------------------------------- ####")
else:
    print("Bright star limit is mag", BrightStar)

#-----------------------------------------------------------------------------
#Read the log file and extract the IRAC info
rawlog = ascii.read(LogTable,format="ipac")
log = rawlog[:][(rawlog['Instrument']=='IRAC').nonzero()]

#read in the AOR properties log, generate a joblist and write it to file
JobListName = OutputDIR + 'jobs.sub_stars.tbl'
AORlog = ascii.read(AORinfoTable,format="ipac")
JobList = make_joblist(log, AORlog)
ascii.write(JobList, JobListName, format="ipac",overwrite=True)    

Njobs = len(JobList)
Nthred  = Nproc  #fails for COSMOS on ppn=48 machines - TBC; use Nproc/2 or so

print("Built job list {:} with {:} jobs".format(JobListName, Njobs))
print("- Launch subtract_stars_function with {:} threads".format(Nthred))

pool = mp.Pool(processes=Nthred)
results = pool.map(run_subtractstars, range(0,Njobs))

print("Done!")
