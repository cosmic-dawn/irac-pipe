#!/opt/local/bin/python

import numpy as np
from astropy.io import ascii
from supermopex import *
from spitzer_pipeline_functions import *
import sys,os
import multiprocessing as mp

def run_subtractstars(JobNo):
    cmd = "cd " + RootDIR + "; " + pythonCMD + " subtract_stars_function.py " + str(JobNo)
    os.system(cmd)

#-----------------------------------------------------------------------------
#Read the log file and extract the IRAC info
rawlog = ascii.read(LogTable,format="ipac")
log = rawlog[:][(rawlog['Instrument']=='IRAC').nonzero()]

#read in the AOR properties log, generate a joblist and write it to file
AORlog = ascii.read(AORinfoTable,format="ipac")
JobList = make_joblist(log, AORlog)
JobListName = OutputDIR + PIDname + '.jobs_subtract_stars.tbl'
Njobs = len(JobList)
ascii.write(JobList, JobListName, format="ipac",overwrite=True)    
print("Built job list {} with {} jobs".format(JobListName, Njobs))

print("- Launch subtract_stars_function with {} threads".format(Nproc))

pool = mp.Pool(processes=Nproc)
results = pool.map(run_subtractstars, range(0,Njobs))

print("Done!")

#Nrows = log['Filename'].size
#for i in range(0,Nrows):
#findstar(5,log=log,Nrows=Nrows,BrightStars=BrightStars,AstrometryStars=AstrometryStars)
#        print str(i+1) + ' of ' + str(Nrows)
