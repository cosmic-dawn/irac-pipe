#-----------------------------------------------------------------------------
# module find_stars.py (par)
#-----------------------------------------------------------------------------

import sys,os
import numpy as np
from astropy.io import ascii
from supermopex import *
from spitzer_pipeline_functions import *
import multiprocessing as mp

def run_findstars(JobNo):
    cmd = "cd " + RootDIR + "; " + pythonCMD + " find_stars_function.py " + str(JobNo)
    #print(cmd)
    os.system(cmd)

#------------------------------------------------------------------
# Read the log file and extract the IRAC info
rawlog = ascii.read(LogTable,format="ipac")
log = rawlog[:][(rawlog['Instrument']=='IRAC').nonzero()]

# Read in the AOR properties log, generate a joblist and write it to file
# if JobList not present, then build new one, else read it ... in order to use alternate list; 
JobListName = OutputDIR + 'jobs.find_stars.tbl'
if not os.path.exists(JobListName):
    AORlog = ascii.read(AORinfoTable,format="ipac")
    JobList = make_joblist(log, AORlog)
    ascii.write(JobList, JobListName, format="ipac",overwrite=True)    
    print(">> Built job list {:} with {:} jobs".format(JobListName.split('/')[-1], len(JobList)))
else:
    JobList = ascii.read(JobListName, format="ipac")
    print(">> Using available job list {:} with {:} jobs".format(JobListName.split('/')[-1], len(JobList)))

Njobs = len(JobList)

# Read in Stars from WISE and cut on bright stars, then write out a table to use for fitting.
stars = ascii.read(StarTable,format="ipac")           # here gaia-wise tbl
BrightFlux = 10**((BrightStar-23.9)/-2.5)             # convert from mag to uJy 
BrightStars = stars[:][((stars['w1'] > BrightFlux) + (stars['w2'] > BrightFlux)).nonzero()] # select bright stars (w1 _or_ w2 > BrightFlux)
ascii.write(BrightStars, BrightStarCat, format="ipac", overwrite=True)   # write to bright_stars.tbl; same format as gaia-wise.tbl
lenbs = len(BrightStars)
print(">> Built {:} of stars brighter than {:} mag from WISE catal, with {:} objects.".format(BrightStarCat.split('/')[-1], BrightStar, lenbs))

# Prepare to lauch
Nthred  = 24
print(">> Now launch find_stars_function JobNo for each job, with {:} threads".format(Nthred))

# run using run_findstars(JobNo) function defined above
pool = mp.Pool(processes=Nthred)
results = pool.map(run_findstars, range(0, Njobs))

print("- Done!")
