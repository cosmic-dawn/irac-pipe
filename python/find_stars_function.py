#----------------------------------------------------------------------------
# module find_stars_function.py                                                       
#----------------------------------------------------------------------------

import sys
import numpy as np
from astropy.io import ascii

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

#print("-- Read the log file and get the IRAC info")   ##DEUG
rawlog = ascii.read(LogTable,format="ipac")
log = rawlog[:][(rawlog['Instrument']=='IRAC').nonzero()]

# Joblist is generated in find_stars.py
#print("-- Read job list written find_stars")  ##DEUG
JobListName = OutputDIR + 'jobs.find_stars.tbl'
JobList = ascii.read(JobListName, format="ipac")
Njobs = len(JobList)

if (JobNo > Njobs):
    die("Requested job number greater than number of jobs available " + str(Njobs) + "!");

# AMo: moved the writing of this bright star catal to find_stars.py; here just read the table
#print("-- Read bright star table")   ##DEBUG
BrightStars = ascii.read(BrightStarCat, format="ipac")

#fill in zero proper motion for stars without measurementes
BrightStars['pmra'].fill_value=0.0
BrightStars['pmdec'].fill_value=0.0
BrightStars['parallax'].fill_value=1e-8

# Read in the table of Gaia stars for astrometry correction
AstrometryStars = ascii.read(GaiaTable,format="ipac") #read the data

#fill in zero proper motion for stars without measurementes
AstrometryStars['pmra'].fill_value=0.0
AstrometryStars['pmdec'].fill_value=0.0
AstrometryStars['parallax'].fill_value=1e-8

#print("-- Launch findstar(JobNo, JobList, etc)".format(JobNo))  ##DEBUG
findstar(JobNo, JobList, log=log, BrightStars=BrightStars, AstrometryStars=AstrometryStars)
