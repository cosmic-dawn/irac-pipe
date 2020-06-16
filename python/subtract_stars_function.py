#!/opt/local/bin/python

import sys
import numpy as np
from astropy.io import ascii
#from astropy import units as u
#from astropy.coordinates import SkyCoord

from supermopex import *
from spitzer_pipeline_functions import *

from optparse import OptionParser

#parse the arguments
usagestring ='%prog Job_Number'
parser = OptionParser()
parser = OptionParser(usage=usagestring)
(options, args) = parser.parse_args()

#fail if there aren't enough arguments
if len(args) < 1:
    parser.error("Incorrect number of arguments.")

#read job number
JobNo=int(args[0])

#print("-- Read the log file and get the IRAC info")  ##DEUG
rawlog = ascii.read(LogTable,format="ipac")
log = rawlog[:][(rawlog['Instrument']=='IRAC').nonzero()]

# Joblist is generated in find_stars.py
#print("-- Read job list written find_stars")  ##DEUG
JobListName = OutputDIR + 'jobs.sub_stars.tbl'
JobList = ascii.read(JobListName, format="ipac")
Njobs = len(JobList)

if (JobNo > Njobs):
    die("Requested job number greater than number of jobs available " + str(Njobs) + "!");

# Read the refined fluxes and postions
StarData = ascii.read(RefinedStarCat, format="ipac") #read the data
StarMatch = SkyCoord(StarData['ra']*u.deg, StarData['dec']*u.deg)


subtract_stars(JobNo, JobList=JobList, log=log, StarData=StarData, StarMatch=StarMatch)
