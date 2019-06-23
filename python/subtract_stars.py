#!/opt/local/bin/python

import sys,os
import numpy as np
from astropy.io import ascii
from supermopex import *
from spitzer_pipeline_functions import *
import multiprocessing as mp

def run_subtractstars(JobNo):
    cmd = "cd " + RootDIR + "; " + pythonCMD + " subtract_stars_function.py " + str(JobNo)
    os.system(cmd)

#-----------------------------------------------------------------------------
#Read the log file and extract the IRAC info
rawlog = ascii.read(LogTable,format="ipac")
log = rawlog[:][(rawlog['Instrument']=='IRAC').nonzero()]

#read in the AOR properties log, generate a joblist and write it to file
JobListName = OutputDIR + 'jobs.sub_stars'
AORlog = ascii.read(AORinfoTable,format="ipac")
JobList = make_joblist(log, AORlog)
ascii.write(JobList, JobListName, format="ipac",overwrite=True)    

Njobs = len(JobList)
#Nthr  = int(Nproc*2/3)  # does not work for NEP on 48core nodes
Nthr  = 20

print("Built job list {} with {} jobs".format(JobListName, Njobs))

print("- Launch subtract_stars_function with {} threads".format(Nthr))

pool = mp.Pool(processes=Nthr)
results = pool.map(run_subtractstars, range(0,Njobs))

print("Done!")

#Nrows = log['Filename'].size
#for i in range(0,Nrows):
#findstar(5,log=log,Nrows=Nrows,BrightStars=BrightStars,AstrometryStars=AstrometryStars)
#        print str(i+1) + ' of ' + str(Nrows)
