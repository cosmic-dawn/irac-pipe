#!/opt/local/bin/python

import numpy as np
from astropy.io import ascii
from supermopex import *
from spitzer_pipeline_functions import *
import os
import multiprocessing as mp

def run_firstframe(JobNo):
    cmd = "cd " + RootDIR + "; " + pythonCMD + " first_frame_corr_function.py " + str(JobNo)
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
#Nthr  = int(Nproc*2/3)
Nthr  = 24

print("Running first frame correction with " + str(Nthr) + " threads.")

pool = mp.Pool(processes=Nthr)
results = pool.map(run_firstframe, range(0,Njobs))

print("Done!")

#for i in range(0,Nrows):
#findstar(5,log=log,Nrows=Nrows,BrightStars=BrightStars,AstrometryStars=AstrometryStars)
#        print str(i+1) + ' of ' + str(Nrows)
