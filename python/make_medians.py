#!/opt/local/bin/python

import numpy as np
from astropy.io import ascii
from supermopex import *
from spitzer_pipeline_functions import *
import os
import multiprocessing as mp

def run_makemedians(JobNo):
    cmd = "cd " + RootDIR + "; " + pythonCMD + " make_medians_function.py " + str(JobNo)
    os.system(cmd)

# Read the log file andget just IRAC info
rawlog = ascii.read(LogTable,format="ipac")
log = rawlog[:][(rawlog['Instrument']=='IRAC').nonzero()]

#Get the size of the array
Nrows = log['Filename'].size

#read in the AOR properties log
AORlog = ascii.read(AORinfoTable,format="ipac")

#genreate a joblist for parallelization
JobList = make_joblist(log,AORlog)
Njobs = len(JobList)

print("- Launch making_medians_function with {} threads.".format(Nproc))

pool = mp.Pool(processes=Nproc)
results = pool.map(run_makemedians, range(0,Njobs))

print("- Done!")

#for i in range(0,Nrows):
#findstar(5,log=log,Nrows=Nrows,BrightStars=BrightStars,AstrometryStars=AstrometryStars)
#        print str(i+1) + ' of ' + str(Nrows)
