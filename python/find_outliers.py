#!/opt/local/bin/python

import numpy as np
from astropy.io import ascii
from supermopex import *
from spitzer_pipeline_functions import *
import os
import multiprocessing as mp

def run_find_outliers(JobNo):
    cmd = "cd " + RootDIR + "; " + pythonCMD + " find_outliers_function.py " + str(JobNo)
    os.system(cmd)

#WRead in the list of tiles
JobList = ascii.read(TileListFile,format="ipac")
Njobs = len(JobList)

print("Making mosaics with " + str(Nproc) + " threads.")

pool = mp.Pool(processes=Nproc)
results = pool.map(run_find_outliers, range(0,Njobs))

print("Done!")

#for i in range(0,Nrows):
#findstar(5,log=log,Nrows=Nrows,BrightStars=BrightStars,AstrometryStars=AstrometryStars)
#        print str(i+1) + ' of ' + str(Nrows)
