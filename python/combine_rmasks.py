#!/opt/local/bin/python

import re,os,shutil
import numpy as np
from astropy import wcs
from astropy.io import ascii
from astropy import units as u
from astropy.table import Table, Column, MaskedColumn
from astropy import wcs
from functools import partial
import multiprocessing as mp

from supermopex import *
from spitzer_pipeline_functions import *

print("----- Begin combine_rmasks.py -----")

#get the PID for temp files
pid = os.getpid() #get the PID for temp files

#read in the log file
log = ascii.read(LogTable,format="ipac")
Nrows = len(log)

#find all the rmask files and collect DCEs
print('# Finding Rmask Files')
fileList = TMPDIR + '/' + str(pid) + ".rmasks.lst"
cmd = "find " + str(RMaskDir) + " -name '*_rmask.fits' > " + fileList
os.system(cmd)

#read the list of files
RmaskFiles = ascii.read(fileList,format="no_header")
RmaskFiles.rename_column('col1','Filename')
Nfiles = len(RmaskFiles)

print("# Reading DCE numbers from " + str(Nfiles) + " RMasks on " + str(Nproc) + " threads.")
#get_rmask_dce(0,RmaskFileList=RmaskFiles)
pool = mp.Pool(processes=Nproc)
RmaskDCEresults = pool.map(partial(get_rmask_dce, RmaskFileList=RmaskFiles), range(0,Nfiles))
pool.close()

#make the RMASK table
print("# Making list of Rmask files with DCEs")
OutputRmaskList=list()
for i in range(0,Nfiles):
    OutputRmaskList.append([RmaskFiles['Filename'][i],RmaskDCEresults[i]])

#add in some columns from the log first, then make table with astrometry
OutputRmaskTable = Table(rows=OutputRmaskList,names=['Filename','DCE'])
ascii.write(OutputRmaskTable, "OutputRmasks.tbl", format="ipac",overwrite=True) 

#Nproc=1   #for testing
print("# Combining RMask files using {:} threads".format(Nproc))

#combine_rmasks(5,RmaskFileList=OutputRmaskTable,log=log)
pool = mp.Pool(processes=Nproc)
results = pool.map(partial(combine_rmasks, RmaskFileList=OutputRmaskTable, log=log), range(0, Nrows))
pool.close()

#make the rmask lists in the same way we did it in setup_pipeline
IracChannels = set(log['Channel'][(log['Instrument']=='IRAC')])
for Ch in IracChannels:
    #get the list of files for this instrument and band
    files = log['Filename'][((log['Instrument']=='IRAC') & (log['Channel']==Ch)).nonzero()]
    
    inputSuffix  = '_' + bcdSuffix + '.fits'  #bcd is the default ending
    outputSuffix = '_rmask.fits'
    OutputFileList = list()

    for i in range(0,len(files)):  #loop over files in list
        OutputFileList.append(re.sub(inputSuffix,outputSuffix,files[i]))
    listname = OutputDIR + PIDname + '.irac.' + str(Ch) + '.rmask.lst'
    np.savetxt(listname,OutputFileList,fmt='%s')
    print("Wrote list of rmask frames to " + listname)

os.system("rm " + fileList)
