#!/opt/local/bin/python


from supermopex import *
from spitzer_pipeline_functions import *

import numpy as np

from astropy.io import ascii
from astropy import units as u
from astropy.coordinates import SkyCoord

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

#read in the log file
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

#Read the refined fluxes and postions
StarData = ascii.read(RefinedStarCat,format="ipac") #read the data
StarMatch = SkyCoord(StarData['ra']*u.deg,StarData['dec']*u.deg)


print("Starting star subtraction and correction with " + str(Nproc) + " threads.")

subtract_stars(JobNo,JobList=JobList,log=log,StarData=StarData,StarMatch=StarMatch)
