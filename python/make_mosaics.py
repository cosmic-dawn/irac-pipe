#!/opt/local/bin/python

import numpy as np
from astropy.io import ascii
from supermopex import *
from spitzer_pipeline_functions import *
import os
import multiprocessing as mp

def run_make_mosaics(JobNo):
    cmd = "cd " + RootDIR + "; " + pythonCMD + " make_mosaics_function.py " + str(JobNo)
    os.system(cmd)


#read in the log file
log = ascii.read(LogTable,format="ipac")
#determine list of channels
IracChannels = set(log['Channel'][(log['Instrument']=='IRAC')])


print("Making mosaics with " + str(Nproc) + " threads.")

pool = mp.Pool(processes=Nproc)
results = pool.map(run_make_mosaics, IracChannels)

print("Done!")

#for i in range(0,Nrows):
#findstar(5,log=log,Nrows=Nrows,BrightStars=BrightStars,AstrometryStars=AstrometryStars)
#        print str(i+1) + ' of ' + str(Nrows)
