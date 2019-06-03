#!/opt/local/bin/python

import numpy as np
from astropy.io import ascii
from supermopex import *
from spitzer_pipeline_functions import *
import sys,os
import multiprocessing as mp

def run_findstars(JobNo):
    cmd = "cd " + RootDIR + "; " + pythonCMD + " find_stars_function.py " + str(JobNo)
    print(cmd)
    os.system(cmd)

#------------------------------------------------------------------
# Read the log file and extract the IRAC info
rawlog = ascii.read(LogTable,format="ipac")
log = rawlog[:][(rawlog['Instrument']=='IRAC').nonzero()]

# Read in the AOR properties log, generate a joblist and write it to file
AORlog = ascii.read(AORinfoTable,format="ipac")
JobList = make_joblist(log, AORlog)
JobListName = OutputDIR + PIDname + '.find_stars.jobs'
Njobs = len(JobList)
ascii.write(JobList, JobListName, format="ipac",overwrite=True)    
print("Built job list {} with {} jobs".format(JobListName, Njobs))

# Read in Stars from WISE and cut on brigt stars, then write out a table to use for fitting.
stars = ascii.read(StarTable,format="ipac")
BrightFlux = 10**((BrightStar-23.9)/-2.5)  #convert from mag to uJy
BrightStars = stars[:][((stars['w1'] > BrightFlux) + (stars['w2'] > BrightFlux)).nonzero()] #get only bright stars
ascii.write(BrightStars, BrightStarCat, format="ipac", overwrite=True)
print("Built list {} of bright stars from WISE catal.".format(BrightStarCat.split('/')[-1]))

print("- Launch find_stars_function with {} threads".format(Nproc))

pool = mp.Pool(processes=Nproc)
results = pool.map(run_findstars, range(0,Njobs))

print("- Done!")

#Nrows = log['Filename'].size
#for i in range(0,Nrows):
#findstar(5,log=log,Nrows=Nrows,BrightStars=BrightStars,AstrometryStars=AstrometryStars)
#        print str(i+1) + ' of ' + str(Nrows)
