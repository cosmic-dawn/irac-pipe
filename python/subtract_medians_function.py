#!/opt/local/bin/python

from supermopex import *
from spitzer_pipeline_functions import *

import numpy as np
from astropy.io import ascii
from astropy.table import Table, Column, MaskedColumn

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

#read the astrometry corrections
AstroFix = ascii.read(AstrometryFixFile,format="ipac")

#Get the size of the array
Nrows = log['Filename'].size

#make output directory
cmd = 'mkdir -p ' + AORoutput
os.system(cmd)

#read in the AOR properties log
AORlog = ascii.read(AORinfoTable,format="ipac")

#genreate a joblist for parallelization
JobList = make_joblist(log,AORlog)
Njobs = len(JobList)

if (JobNo > Njobs):
    die("Requested job number greater than number of jobs available " + str(Njobs) + "!");

subtract_median(JobNo,JobList=JobList,log=log,AstroFix=AstroFix)
