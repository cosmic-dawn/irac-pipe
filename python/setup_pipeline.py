#----------------------------------------------------------------------------
# module setup_pipeline.py (serial)
#----------------------------------------------------------------------------

import re, os,shutil
import numpy as np
from astropy.io import ascii
from astropy import units as u
from astropy.table import Table, Column, MaskedColumn
from astropy import wcs
from astropy.io import fits
import datetime
#import multiprocessing as mp
from supermopex import *

#get the PID for temp files
pid = os.getpid() #get the PID for temp files

#make the needed directories
if not(os.path.exists(TMPDIR)):
    os.mkdir(TMPDIR)
if not(os.path.exists(OutputDIR)):
    os.mkdir(OutputDIR)
if not(os.path.exists(AORoutput)):
    os.mkdir(AORoutput)

#find bcd files: find the fits files for parsing
#use UNC files because they are only generated if the BCD pipleine didn't fail
print('>> Finding BCD Files')
fileList = TMPDIR + '/' + str(pid) + ".files.lst"
cmd = "find " + str(RawDataDir) + " -name '*_bunc.fits' > " + fileList
os.system(cmd)

#read the list of files
files = ascii.read(fileList,format="no_header")
Nfiles = len(files)

print('>> Found {:} files; read the headers and create an inventory'.format(Nfiles))
os.system('rm -rf ' + fileList) #remove the temp file

LogOutput = list()
for file in range(0,Nfiles):
    
    #progress = "Reading file " + str(file+1) + " of " + str(Nfiles)
    #print(progress) #,end="\r")

    #setup this line of the logfile
    LogLine = list()
    
    BCDfilename=files['col1'][file]

    #Setup file suffixes re replace
    inputSuffix  = '_' + UncSuffix + '.fits'  #used in search
    outputSuffix = '_' + bcdSuffix + '.fits'
    BCDFile = re.sub(inputSuffix,outputSuffix,BCDfilename) #Make the filename for the log file
    
    LogLine.append(BCDFile)

    #read the fits file
    imageHDU = fits.open(BCDFile) #Read image

    for item in range(0,len(HeaderItems)):
        value = imageHDU[0].header.get(HeaderItems[item])
        #convert HDR mode to 1/0 from T/F
        if (item == 'HDRMODE'):
            if (value == 'T'):
                value = 1
            else:
                value = 0

        LogLine.append(value) #add the value to the log

    #Do some checking to see if the BCD header is good, reject frmae if it is not
    good=1
    if imageHDU[0].header.get('FRAMEDLY') <= 0:  #reject if frame delay is not positive
        good = 0
    if imageHDU[0].header.get('CHNLNUM') > 4:  #reject if channel number too high
        good = 0

    if good > 0:
        LogOutput.append(LogLine)  #Add line to log
    else:
        print("## Rejecting frame {:} because of bad header!".format(file))

print()  #line return for progress
print(">> Now process the inventory")

#write the log file
log = Table(rows=LogOutput,names=LogItems)
ascii.write(log, LogTable, format="ipac",overwrite=True)

#do some checking of the data
#Get lists of different file types
AORList = list(set(log['AOR']))#get a list of AORs
ObjectList = list(set(log['Object']))#get a list of Instruments
InstrumentList = list(set(log['Instrument']))#get a list of Instruments
ObservationList = list(set(log['ObsType']))#get a list of Observation Types
PIDList = list(set(log['PID']))#get a list of Observation Types

#numbers of files
Naor = len(AORList) #number of AORs
Nhdr = len(log['HDR'][(log['HDR']==1).nonzero()])  # get the number of HDR frames


#Determine what we should do for the mosaics

#This is where we will figure out the number of mosaics later
#Hard code to 1 for now
Nmosaics = 1

#Initialize some choices to No
IRACHDR=0
doirac=0
domips=0
NIracBands=0
NMipsBands=0

AORinfo=list()
for i in range(0,Naor):
    AORLog = log[:][(log['AOR']==AORList[i]).nonzero()] #get the log entries for this AOR

    #get some log info
    AORlogLine = list() #holder for this line
    AORlogLine.append(AORList[i])
    AORlogLine.append(AORLog['Object'][0])  #Object name
    AORlogLine.append(AORLog['Instrument'][0]) #Instrument
    AORlogLine.append(AORLog['PID'][0]) #PID
    AORlogLine.append(AORLog['ObsType'][0]) #Observation type
    
    #check for HDR mode or not.  HDR mode if all data is HDR
    HDRmode='True'
    for item in AORLog['HDR']:
        if re.match(str(item),'False'):
            HDRmode='False'
            break

    AORlogLine.append(HDRmode)

    #get the max number of channels
    Nch = np.max(AORLog['Channel'])
    AORlogLine.append(Nch) #Channel

    #add to log
    AORinfo.append(AORlogLine)

    #should we do IRAC?
    if (AORLog['Instrument'][0] == 'IRAC'):
        doirac=1
        #How many IRAC bands
        if (Nch > NIracBands):
            NIracBands=Nch

    #should we do MIPS?
    if (AORLog['Instrument'][0] == 'MIPS'):
        domips=1
        #How many MIPS bands
        if (Nch > NMipsBands):
                NMipsBands=Nch


#write the log file
AORlog = Table(rows=AORinfo,names=('AOR','Object','Instrument','PID','ObsType','HDR','NumChannel'))
ascii.write(AORlog, AORinfoTable, format="ipac", overwrite=True)

print("Your data consists of:")
print("- {:} AORs".format(Naor))
print("- labled with {:} object names".format(len(ObjectList)))
print("- Observed with {:} Program IDs".format(len(PIDList)))
print()
#print(AORlog)

#make the file lists
for Ch in range(1,NIracBands+1):
    #get the list of files for this instrument and band
    files = log['Filename'][((log['Instrument']=='IRAC') & (log['Channel']==Ch)).nonzero()]
    
    #loop over the types of files we will want
    for suffix in IRACsuffixList:
       OutputFileList = list() #holder for output list
       inputSuffix  = '_' + bcdSuffix + '.fits'  #bcd is the default ending
       outputSuffix = '_' + suffix + '.fits'

       for i in range(0,len(files)):  #loop over files in list
            #add file to list putting in apropriate suffix
            OutputFileList.append(re.sub(inputSuffix,outputSuffix,files[i]))          

       listname = OutputDIR + PIDname + '.irac.' + str(Ch) + '.' + suffix + '.lst' 
       np.savetxt(listname,OutputFileList,fmt='%s')

#make the FIF file list for IRAC
files = log['Filename'][(log['Instrument']=='IRAC').nonzero()]
OutputFileList = list() #holder for output list
inputSuffix  = '_' + bcdSuffix + '.fits'  #bcd is the default ending
outputSuffix = '_' + corDataSuffix + '.fits'

#save a list of all BCD data
listname = OutputDIR + PIDname + '.irac.FIF.' + bcdSuffix + '.lst' 
np.savetxt(listname,files,fmt='%s')

#now do corrected BCDs
OutputFileList = list() #holder for output list
for i in range(0,len(files)):  #loop over files in list
    OutputFileList.append(re.sub(inputSuffix,outputSuffix,files[i]))          
listname = OutputDIR + PIDname + '.irac.FIF.' + corDataSuffix + '.lst' 
np.savetxt(listname,OutputFileList,fmt='%s')

