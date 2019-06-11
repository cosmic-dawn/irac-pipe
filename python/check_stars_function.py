#!/opt/local/bin/python

import numpy as np
from astropy.io import ascii

from supermopex import *
from spitzer_pipeline_functions import *

import sys
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

#Read the log fileand get IRAC info
rawlog = ascii.read(LogTable,format="ipac")
log = rawlog[:][(rawlog['Instrument']=='IRAC').nonzero()]

#Get the size of the array
Nrows = log['Filename'].size

#read in the AOR properties log
AORlog = ascii.read(AORinfoTable,format="ipac")

#genreate a joblist for parallelization
JobList = make_joblist(log,AORlog)
Njobs = len(JobList)

if (JobNo > Njobs):
    die("Requested job number greater than number of jobs available " + str(Njobs) + "!");

#Read in the table of Gaia stars for astrometry correction
AstrometryStars = ascii.read(GaiaTable,format="ipac") #read the data

#fill in zero proper motion for stars without measurementes
AstrometryStars['pmra'].fill_value=0.0
AstrometryStars['pmdec'].fill_value=0.0
AstrometryStars['parallax'].fill_value=1e-8

checkstar(JobNo,JobList,log=log,AstrometryStars=AstrometryStars)
