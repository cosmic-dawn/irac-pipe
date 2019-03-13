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

#Read the log file
#rawlog = ascii.read(LogFile,format="commented_header",header_start=-1)
rawlog = ascii.read(LogTable,format="ipac")
#get just IRAC info
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

#Read in Stars from WISE and cut on brigt stars, then write out a table to use for fitting.
stars = ascii.read(StarTable,format="ipac")
BrightFlux = 10**((BrightStar-23.9)/-2.5)#convert from mag to uJy
BrightStars = stars[:][((stars['w1'] > BrightFlux) + (stars['w2'] > BrightFlux)).nonzero()] #get only bright stars
ascii.write(BrightStars,BrightStarCat,format="ipac",overwrite=True)

#Read in the table of Gaia stars for astrometry correction
AstrometryStars = ascii.read(GaiaTable,format="ipac") #read the data

findstar(JobNo,JobList,log=log,BrightStars=BrightStars,AstrometryStars=AstrometryStars)
