#!/opt/local/bin/python

import numpy as np
from astropy.io import ascii
from supermopex import *
from spitzer_pipeline_functions import *
import os
import multiprocessing as mp

def run_checkstars(JobNo):
    cmd = "cd " + RootDIR + "; " + pythonCMD + " check_stars_function.py " + str(JobNo)
    os.system(cmd)

#Read the log file and get IRAC info
rawlog = ascii.read(LogTable,format="ipac")
log = rawlog[:][(rawlog['Instrument']=='IRAC').nonzero()]

#read in the AOR properties log
AORlog = ascii.read(AORinfoTable,format="ipac")

#genreate a joblist for parallelization
JobList = make_joblist(log,AORlog)
Njobs = len(JobList)

Nthred = int(Nthred/2)
print("Starting check_stars: {:} jobs with {:} threads.".format(Njobs, Nthred))

pool = mp.Pool(processes=Nthred)
results = pool.map(run_checkstars, range(0,Njobs))

print("Done!")

#Get the size of the array
#Nrows = log['Filename'].size
#for i in range(0,Nrows):
#findstar(5,log=log,Nrows=Nrows,BrightStars=BrightStars,AstrometryStars=AstrometryStars)
#        print str(i+1) + ' of ' + str(Nrows)
