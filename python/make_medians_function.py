#-----------------------------------------------------------------------------
# module make_medians_function.py (par)
#-----------------------------------------------------------------------------

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

# check if debug mode
if len(args) > 1:
    debug = 1
else:
    debug = 0

# Read in the log file and extract the IRAC info
rawlog = ascii.read(LogTable,format="ipac")
log = rawlog[:][(rawlog['Instrument']=='IRAC').nonzero()]

#Get the size of the array
Nrows = log['Filename'].size

#read in the AOR properties log
AORlog = ascii.read(AORinfoTable,format="ipac")

#genreate a joblist for parallelization
JobList = make_joblist(log,AORlog)
#JobListName = OutputDIR + 'jobs.medians.tbl'
#JobList = ascii.read(JobListName, format="ipac")
Njobs = len(JobList)

if (JobNo > Njobs):
    die("Requested job number greater than number of jobs available " + str(Njobs) + "!");

#make output directory
cmd = 'mkdir -p ' + AORoutput
os.system(cmd)

make_median_image(JobNo, JobList=JobList, log=log, AORlog=AORlog, debug=debug)

