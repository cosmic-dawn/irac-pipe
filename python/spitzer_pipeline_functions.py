#---------------------------------------------------------------------------------------------------
# Spitzer / irac pipeline functions
#---------------------------------------------------------------------------------------------------

import numpy as np
import numpy.ma as ma
import sys, re, os, shutil

from scipy.interpolate import interp1d
import scipy.ndimage as ndimage
from statsmodels import robust

from astropy import wcs
from astropy import units as u
from astropy.io import fits
from astropy.io import ascii
from astropy.coordinates import SkyCoord
from astropy.table import Table, Column, MaskedColumn, hstack

import warnings
warnings.filterwarnings("ignore")

from supermopex import *


#---------------------------------------------------------------------------------------------------
# Select area for scratch directory
#---------------------------------------------------------------------------------------------------

def scratch_dir_prefix(cluster):

    if cluster == 'candide':
        locnode = os.uname().nodename
        if (locnode[0] == 'c'):
            print(" On login node ... quitting") ; sys.exit()

        locnode = os.uname().nodename.split('.')[0]  # name of process node

        if (locnode == 'n03') or (locnode == 'n04') or (locnode == 'n05') or (locnode == 'n06') or (locnode == 'n07') or (locnode == 'n08') or (locnode == 'n09'):
            processTMPDIRprefix = '/' + locnode + 'data/'
        else:
            processTMPDIRprefix = '/scratch{:}/'.format(locnode[1:3])
    else:
        processTMPDIRprefix = TMPDIR + '/'
    
    return(processTMPDIRprefix)


#---------------------------------------------------------------------------------------------------
# Make the list of jobs, one per AOR.chan, from the list of frames and the list of AORs
#---------------------------------------------------------------------------------------------------

def make_joblist(log, AORlog):

    #get a list of AORs
    AORlist = list(set(log['AOR']))
    Naor = len(AORlist)

    #make a list of channels and AORS
    JobList=list()
    for aorIDX in range(0,Naor):
        ChMax = AORlog['NumChannel'][aorIDX]   #np.max(log['Channel'][(log['AOR']==AORlist[aorIDX]).nonzero()])
        HDR = AORlog['HDR'][aorIDX]
        for Ch in range(1,ChMax+1):
            Nframes =len(log['Channel'][((log['AOR']==AORlist[aorIDX])&(log['Channel']==Ch)).nonzero()])
            if (Nframes > 0):
                JobList.append([AORlist[aorIDX],HDR,Ch,Nframes])

    JobList = Table(rows=JobList,names=['AOR','HDR','Channel','NumFrames'])

    return(JobList)


#---------------------------------------------------------------------------------------------------
# routine to apply proper motoins to GAIA catalog
#---------------------------------------------------------------------------------------------------

def applyGAIApm(MJD,StarData):

    PMtime = (MJD-51558.5)/365.25   #time since 2015.5 (GAIA DR2 epoch) for proper motion correction

    #offset and weight values for astrometry
    RAstar = list()
    DECstar = list()
    
    for i in range(0,len(StarData)):
        #start with DEC
        if ma.is_masked(StarData['pmdec_error'][i]):
            DECpm=0.0
        else:
            DECpm = StarData['pmdec'][i]*PMtime/(1000.0*3600.0)  #convert to degrees from Milli arcsec
        
        #Put pm corrected reference DEC and errror along with measurement in the array
        refDEC  = StarData['dec'][i]
        DECstar.append(refDEC+DECpm)
        
        #Now RA
        #correct for proper motion if its known
        #Gaia PM is in u*cos(dec)
        if ma.is_masked(StarData['pmra_error'][i]):
            RApm = 0.0
        else:
            RApm = StarData['pmra'][i]*PMtime/(1000.0*3600.0*np.cos(refDEC*0.017453293))

        #Put pm corrected reference RA and errror along with measurement in the array
        refRA  = StarData['ra'][i]
        RAstar.append(refRA+RApm)

    AstrometryData=np.asarray(list(zip(RAstar,DECstar)),dtype=np.double)
    return(AstrometryData)


#---------------------------------------------------------------------------------------------------
#
#---------------------------------------------------------------------------------------------------

def applyGAIApm_wError(MJD,StarData):
    
    PMtime = (MJD-51558.5)/365.25  #time since 2015.5 (GAIA DR2 epoch) for proper motion correction
    
    #offset and weight values for astrometry
    RAstar = list()
    RAstarErr = list()
    RApmCorr = list()

    DECstar = list()
    DECstarErr = list()
    DECpmCorr = list()

    for i in range(0,len(StarData)):
        #start with DEC
        if ma.is_masked(StarData['pmdec_error'][i]):
            DECpm=0.0
            DECpmError=0.0
        else:
            DECpm = StarData['pmdec'][i]*PMtime/(1000.0*3600.0)
            DECpmError = StarData['pmdec_error'][i]*PMtime/(1000.0*3600.0)
                
        #Put pm corrected reference DEC and errror along with measurement in the array
        refDEC  = StarData['dec'][i]
        refDECerr  = StarData['dec_error'][i]/(1000.0*3600.0) # convert from mas to deg
        DECstar.append(refDEC+DECpm)
        DECstarErr.append(np.sqrt(refDECerr*refDECerr+DECpmError*DECpmError))
        DECpmCorr.append(DECpm)
            
        #Now RA
        #correct for proper motion if its known
        if ma.is_masked(StarData['pmra_error'][i]):
            RApm = 0.0
            RApmError = 0.0
        else:
            RApm = StarData['pmra'][i]*PMtime/(1000.0*3600.0*np.cos(refDEC*0.017453293))
            RApmError = StarData['pmra_error'][i]*PMtime/(1000.0*3600.0*np.cos(refDEC*0.017453293))
                
        #Put pm corrected reference RA and errror along with measurement in the array
        refRA  = StarData['ra'][i]
        refRAerr  = StarData['ra_error'][i]/(1000.0*3600.0*np.cos(refDEC*0.017453293)) # convert from mas to deg
        RAstar.append(refRA+RApm)
        RAstarErr.append(np.sqrt(refRAerr*refRAerr+RApmError*RApmError))
        RApmCorr.append(RApm)

    AstrometryData=Table(rows=list(zip(RAstar,RAstarErr,RApmCorr,DECstar,DECstarErr,DECpmCorr)),names=['RA','dRA','RApm','DEC','dDEC','DECpm'])
    return(AstrometryData)


#---------------------------------------------------------------------------------------------------
# routine to find stars to find star
#---------------------------------------------------------------------------------------------------

def findstar(JobNo,JobList,log,BrightStars,AstrometryStars):
    
    AOR = JobList['AOR'][JobNo]
    Ch = JobList['Channel'][JobNo]
    Njobs = len(JobList)
    
    #make the list of files for this AOR and Channel
    LogIDX = ((log['Channel']==Ch) & (log['AOR']==AOR)).nonzero()  # get the indexes of files we should use
    files  = log['Filename'][LogIDX]
    MJDs   = log['MJD'][LogIDX]
    RAs    = log['RA'][LogIDX]
    DECs   = log['DEC'][LogIDX]
    
    #convert the catalogs to astropy sky-coord format
    BrightCoords=SkyCoord(BrightStars['ra'], BrightStars['dec'],pm_ra_cosdec=BrightStars['pmra'].filled(),pm_dec=BrightStars['pmdec'].filled(),distance=BrightStars['parallax'].filled(),obstime=GaiaEpoch,frame='icrs', unit="deg")
    AstrometryCoords=SkyCoord(AstrometryStars['ra'], AstrometryStars['dec'],pm_ra_cosdec=AstrometryStars['pmra'].filled(),pm_dec=AstrometryStars['pmdec'].filled(),distance=AstrometryStars['parallax'].filled(),obstime=GaiaEpoch,frame='icrs', unit="deg")

    Nframes = len(files)    
    print('## Begin find_stars job {:4d} on {:} - AOR {:8d} Ch {:}, {:3d} frames'.format(JobNo, os.uname().nodename, AOR, Ch, Nframes))
    
    for fileNo in range(0,Nframes):
        MJD      = MJDs[fileNo]
        frameRA  = RAs[fileNo]
        frameDEC = DECs[fileNo]
        filename = files[fileNo]
        
        #Get the image center for figuring out which objects to consider
        ImCenter = SkyCoord(frameRA,frameDEC, frame="fk5", unit="deg")

        #Setup file suffixes re replace
        inputSuffix  = '_' + bcdSuffix + '.fits'  #used in search
        basename = re.sub(inputSuffix,'',re.split('/',filename)[-1])
        
        outputSuffix = '_' + ffSuffix + '.fits'
        inputData =  re.sub(inputSuffix,outputSuffix,filename)  #use first frame corrected data as input
        
        outputSuffix = '_' + corUncSuffix + '.fits'
        inputSigma =  re.sub(inputSuffix,outputSuffix,filename) #sigma file input
        
        outputSuffix = '_' + maskSuffix + '.fits'
        inputMask =  re.sub(inputSuffix,outputSuffix,filename)  #masked pixel input
        
        outputSuffix = '_' + BrightStarInputTableSuffix
        inputCatBright = re.sub(inputSuffix,outputSuffix,filename)   #table of bright stars as input

        outputSuffix = '_' + BrightStarTableSuffix
        outputCatBright = re.sub(inputSuffix,outputSuffix,filename)  #table of bright stars in frame as output

        outputSuffix = '_' + StarInputTableSuffix
        inputCatAstro = re.sub(inputSuffix,outputSuffix,filename)   #table of astrometry stars as input

        outputSuffix = '_' + StarTableSuffix
        outputCatAstro = re.sub(inputSuffix,outputSuffix,filename)  #table of astrometry stars in frame as output
        
        #Check if we are in the Cryo mission
        if (MJD > WarmMJD):
            cryo = 0
        else:
            cryo = 1
    
        #temporary files
        pid = os.getpid() #get the PID for temp files
        processTMPDIR = scratch_dir_prefix(cluster) + 'tmpfiles' + str(pid) + '-' + str(fileNo) + '/'
        os.system('mkdir -p ' + processTMPDIR)
#        print("   Process temp dir is", processTMPDIR)      # DEBUG

        #Cut Bright Star catalog to this frame
        #Transform GAIA catalog to current epoch
        #BrightPositions = applyGAIApm(MJD,BrightStars)
        BrightPositions = BrightCoords.apply_space_motion(Time(MJD,format='mjd'))

        #Cut catalog to this frame
        BrightSep = BrightPositions.separation(ImCenter)
        BrightInFrame = BrightPositions[np.where(BrightSep.deg < 0.123)]

        #write out catalog for bright stars
        BrightStarTable = inputCatBright
        ascii.write(Table([BrightInFrame.ra.deg,BrightInFrame.dec.deg],names=['ra','dec']),BrightStarTable,format="ipac",overwrite=True)
        
#        print(' - Frame {:3d}; {:}: find bright stars ...'.format(fileNo +1, inputData.split('/')[-1]), end=' ') # DEBUG
        
        # do the bright stars for star subtraction
        command = "apex_user_list_1frame.pl -n find_brightstars.nl  -p " + PRF[cryo][Ch-1] + " -u " + BrightStarTable + " -i " + inputData + " -s " + inputSigma + " -d " + inputMask + " -M " + IRACPixelMasks[Ch-1] + " -O " + processTMPDIR + ' > /dev/null 2>&1'
        os.system(command)
        
        #move the output to the final location
        FitTable = processTMPDIR + basename + "_ffcbcd_extract_raw.tbl"
#        print("### shutil mv ",FitTable,outputCatBright)      # DEBUG
        shutil.move(FitTable,outputCatBright)

        #Transform GAIA catalog to current epoch
        #AstrometryPositions = applyGAIApm(MJD,AstrometryStars)
        AstrometryPositions = AstrometryCoords.apply_space_motion(Time(MJD,format='mjd'))

        #Cut catalog to this frame
        #AstrometryPositionsCoord = SkyCoord(AstrometryPositions, frame="fk5", unit="deg")
        AstroSep = AstrometryPositions.separation(ImCenter)
        AstroInFrame = AstrometryPositions[np.where(AstroSep.deg < 0.0675)]

        #write out catalog for Astrometry stars
        FitStarTable = inputCatAstro
        ascii.write(Table([AstroInFrame.ra.deg,AstroInFrame.dec.deg],names=['ra','dec']),FitStarTable,format="ipac",overwrite=True)

        #print(' find astrometry stars')
        #now do the stars for astrometry
        command = "apex_user_list_1frame.pl -n find_astrostars.nl -m " + PRFmap[cryo][Ch-1] + " -u " + FitStarTable + " -i " + inputData + " -s " + inputSigma + " -d " + inputMask + " -M " + IRACPixelMasks[Ch-1] + " -O " + processTMPDIR + ' > /dev/null 2>&1'
        os.system(command)
        
        #move the output to the final location
        FitTable = processTMPDIR + basename + "_ffcbcd_extract_raw.tbl"
        shutil.move(FitTable,outputCatAstro)
        
        #clean up
        cleanupCMD = 'rm -rf ' + processTMPDIR
        os.system(cleanupCMD)
        
    print('## Finished job {:4d}: AOR {:8d} Ch {:}'.format(JobNo, AOR, Ch))


#---------------------------------------------------------------------------------------------------
# routine to find stars in order to check the astrometry solution
#---------------------------------------------------------------------------------------------------

def checkstar(JobNo,JobList,log,AstrometryStars):
    
    AOR = JobList['AOR'][JobNo]
    Ch = JobList['Channel'][JobNo]
    Njobs = len(JobList)
    
    #make the list of files for this AOR and Channel
    LogIDX = ((log['Channel']==Ch) & (log['AOR']==AOR)).nonzero()  # get the indexes of files we should use
    files = log['Filename'][LogIDX]
    MJDs = log['MJD'][LogIDX]
    RAs  = log['RA'][LogIDX]
    DECs = log['DEC'][LogIDX]
    
    Nframes = len(files)

    print('## Begin check_stars job {:4d} - AOR {:8d} Ch {:}, {:3d} frames'.format(JobNo, AOR, Ch, Nframes))
 
    for fileNo in range(0,Nframes):
        MJD = MJDs[fileNo]
        frameRA = RAs[fileNo]
        frameDEC= DECs[fileNo]
        filename = files[fileNo]

        #Setup file suffixes re replace
        inputSuffix  = '_' + bcdSuffix + '.fits'  #used in search
        basename = re.sub(inputSuffix,'',re.split('/',filename)[-1])
        
        outputSuffix = '_' +  SubtractedSuffix + '.fits'
        inputData =  re.sub(inputSuffix,outputSuffix,filename)  #use first frame corrected data as input
        
        outputSuffix = '_' + ScaledUncSuffix + '.fits'
        inputSigma =  re.sub(inputSuffix,outputSuffix,filename) #sigma file input
        
        outputSuffix = '_' + starMaskSuffix + '.fits'
        inputMask =  re.sub(inputSuffix,outputSuffix,filename)  #masked pixel input
        
        outputSuffix = '_' + StarInputTableSuffix
        inputCatAstro = re.sub(inputSuffix,outputSuffix,filename)  #table of astrometry stars as output
        
        outputSuffix = '_' + AstrocheckTableSuffix
        outputCatAstro = re.sub(inputSuffix,outputSuffix,filename)  #table of astrometry stars as output
        
        #Check if we are in the Cryo mission
        if (MJD > WarmMJD):
            cryo = 0
        else:
            cryo = 1

        #temporary files
        pid = os.getpid() #get the PID for temp files
        processTMPDIR = scratch_dir_prefix(cluster) + 'tmpfiles' + str(pid) + '-' + str(fileNo) + '/'
        os.system('mkdir -p ' + processTMPDIR)
        
        #write out catalog for Astrometry stars
        FitStarTable = inputCatAstro

###        print('Find astrometry stars in frame  {:3d}; {:}'.format(fileNo +1, inputData.split('/')[-1]))
        #now do the stars for astrometry
        command = "apex_user_list_1frame.pl -n find_astrostars.nl -m " + PRFmap[cryo][Ch-1] + " -u " + FitStarTable + " -i " + inputData + " -s " + inputSigma + " -d " + inputMask + " -M " + IRACPixelMasks[Ch-1] + " -O " + processTMPDIR + ' > /dev/null 2>&1'
        os.system(command)
        
        #move the output to the final location
        FitTable = processTMPDIR + basename + "_sub_extract_raw.tbl"
        shutil.move(FitTable,outputCatAstro)
        
        #clean up
        cleanupCMD = 'rm -rf ' + processTMPDIR
        os.system(cleanupCMD)

    print('## Finished job {:4d}: AOR {:8d} Ch {:}'.format(JobNo, AOR, Ch))
    

#---------------------------------------------------------------------------------------------------
#
#---------------------------------------------------------------------------------------------------

def fix_astrometry(JobNo,log,Nrows,JobList,AstrometryStars):
    
    ChMax =  JobList['ChannelMax'][JobNo]
    ID    =  JobList['ExposureID'][JobNo]
    AOR   =  JobList['AOR'][JobNo]
    MJD   = np.average(log['MJD'][((log['AOR']==AOR)&(log['ExposureID']==ID)).nonzero()])
    
    FrameEpoch = Time(MJD,format='mjd')
    

    #convert to astropy coords format
    StarCoords=SkyCoord(AstrometryStars['ra'], AstrometryStars['dec'],pm_ra_cosdec=AstrometryStars['pmra'].filled(),pm_dec=AstrometryStars['pmdec'].filled(),distance=AstrometryStars['parallax'].filled(),obstime=GaiaEpoch,frame='icrs', unit="deg")
    #make a local copy of the table
    StarData = AstrometryStars
    
    PMtime = (FrameEpoch.mjd-GaiaEpoch.mjd)/365.25  #time to GAIA in years for proper motion correction
    
    #do the proper motion correction to the MJD
    StarMatch = StarCoords.apply_space_motion(Time(MJD,format='mjd'))

    #Add in the proper motion errors to the astrometry
    StarData['dec_error'] = np.sqrt(StarData['dec_error']**2 + (StarData['pmdec_error'].filled()*PMtime)**2)
    StarData['ra_error'] = np.sqrt(StarData['ra_error']**2 + (StarData['pmra_error'].filled()*PMtime)**2)
    
    files = log['Filename'][((log['AOR']==AOR)&(log['ExposureID']==ID)).nonzero()]
    DCElist = log['DCE'][((log['AOR']==AOR)&(log['ExposureID']==ID)).nonzero()]
    
    #offset and weight values for astrometry
    RAstar = list()
    RAstarErr = list()
    DECstar = list()
    DECstarErr = list()
    
    RAmeas = list()
    RAmeasErr = list()
    DECmeas = list()
    DECmeasErr = list()
    
    DECpmCorr = list()
    RApmCorr = list()
    
    #merge the master star catalog with the measured values to get offsets
    for BCDfilename in files:
        
        #set up the file name for the input star catalog
        inputSuffix  = '_' + bcdSuffix + '.fits'
        outputSuffix = '_' + StarTableSuffix
        FrameCatFile = re.sub(inputSuffix,outputSuffix,BCDfilename) #Make the filename for the star catalogs
        
        #read in the star data for this frame
        #print(FrameCatFile)
        FrameStars = ascii.read(FrameCatFile,format="ipac") #read the data for the single frame catalog
        
        #match the frame to the refined
        FrameMatch = SkyCoord(FrameStars['RA']*u.deg,FrameStars['Dec']*u.deg) #put the catalog into the matching format
        idx,d2d,d3d=FrameMatch.match_to_catalog_sky(StarMatch) #do the match
        
        #loop over matches and calculate the offsets
        for i in range(0,len(idx)):
            if ((FrameStars['status'][i]!=0)&(d2d[i].arcsec <= AstroMergeRad)):
                
                #Put pm corrected reference DEC and error along with measurement in the array
                DECstar.append(StarData['dec'][idx[i]])
                DECstarErr.append(StarData['dec_error'][idx[i]]/(1000.0*3600.0))  #convert to degrees
                DECpmCorr.append(StarData['pmdec'].filled()[idx[i]]*PMtime/(1000.0*3600.0))#convert to degrees and multiply by time

                DECmeas.append(FrameStars['Dec'][i])
                DECmeasErr.append(FrameStars['delta_Dec'][i])
                
                #Put pm corrected reference RA and errror along with measurement in the array
                RAstar.append(StarData['ra'][idx[i]])
                RAstarErr.append(StarData['ra_error'][idx[i]]/(1000.0*3600.0*np.cos(StarData['ra'][idx[i]]*0.017453293)))  #convert to degrees
                RApmCorr.append(StarData['pmra'].filled()[idx[i]]*PMtime/(1000.0*3600.0*np.cos(StarData['ra'][idx[i]]*0.017453293)))#convert to degrees and multiply by time

                RAmeas.append(FrameStars['RA'][i])
                RAmeasErr.append(FrameStars['delta_RA'][i])

    #put the offests and errors into a masked array so we can do some outlier clipping and then estimate a weighted average offset

    dRA = ma.array([RAstar],dtype=np.double)-ma.array([RAmeas],dtype=np.double)
    dDEC = ma.array([DECstar],dtype=np.double)-ma.array([DECmeas],dtype=np.double)
    
    #variances for weighting
    RAvar = ma.array([RAmeasErr],dtype=np.double)*ma.array([RAmeasErr],dtype=np.double)+ma.array([RAstarErr],dtype=np.double)*ma.array([RAstarErr],dtype=np.double)
    DECvar = ma.array([DECmeasErr],dtype=np.double)*ma.array([DECmeasErr],dtype=np.double)+ma.array([DECstarErr],dtype=np.double)*ma.array([DECstarErr],dtype=np.double)
    
    #proper motions for masking
    RApmCorr = np.array([RApmCorr],dtype=np.double)
    DECpmCorr = np.array([DECpmCorr],dtype=np.double)
    
    
    #mask objects with large seperations and high-proper motion objects
    mask = np.zeros([dRA.size],dtype=np.bool)
    
    #calculate medians and robust errors for clipping
    med_dRA = ma.median(dRA)
    med_dDEC = ma.median(dDEC)
    sig_RA = ma.std(dRA)  #numpy mad converts to std automatically
    sig_DEC = ma.std(dDEC)
    
    #mask outliers
    Rout = ma.sqrt((dRA-med_dRA)*(dRA-med_dRA)+(dDEC-med_dDEC)*(dDEC-med_dDEC)).reshape(dRA.size) #radius of outlier
    Rlimit = ma.sqrt((sig_RA*sig_RA+sig_DEC*sig_DEC)) #sigma limit
    mask[(Rout >= Rlimit*3.0).nonzero()]=1

    #mask outliers
    dRA.mask +=mask
    dDEC.mask+=mask
    RAvar.mask +=mask
    DECvar.mask+=mask
    
    #calculate outlier value
    #corrRA=ma.average(dRA,weights=1.0/RAvar)
    #corrDEC=ma.average(dDEC,weights=1.0/DECvar)
    corrRA=ma.median(dRA)
    corrDEC=ma.median(dDEC)

    #re-calculate sig after clipping
    sig_RA = ma.std(dRA)
    sig_DEC = ma.std(dDEC)
    
    #count the number of stars left
    GoodStars=ma.count(dRA)
    
    print('Process frame {:5d} using {:3d} stars.  Offset is dRA = {:4.2f} +/- {:4.2f}; dDEC = {:5.2f} +/- {:4.2f}'.format(JobNo+1, GoodStars, corrRA*3600, 3600*sig_RA/np.sqrt(GoodStars), corrDEC*3600, 3600*sig_DEC/np.sqrt(GoodStars) ))
    
    astrofix = np.array([JobNo,corrRA,corrDEC,sig_RA/np.sqrt(GoodStars),sig_DEC/np.sqrt(GoodStars),GoodStars],dtype=np.double)
    return(astrofix)


#---------------------------------------------------------------------------------------------------
#
#---------------------------------------------------------------------------------------------------

def check_astrometry(JobNo,log,Nrows,JobList,AstrometryStars):
    
    ChMax =  JobList['ChannelMax'][JobNo]
    ID    =  JobList['ExposureID'][JobNo]
    AOR   =  JobList['AOR'][JobNo]
    MJD   = np.average(log['MJD'][((log['AOR']==AOR)&(log['ExposureID']==ID)).nonzero()])
    
    PMtime = (MJD-51543.0)/365.2422  #time since J2000 for proper motion correction
    
    #convert the catalogs to astropy sky-coord format
    AstrometryCoords=SkyCoord(AstrometryStars['ra'], AstrometryStars['dec'],pm_ra_cosdec=AstrometryStars['pmra'].filled(),pm_dec=AstrometryStars['pmdec'].filled(),distance=AstrometryStars['parallax'].filled(),obstime=GaiaEpoch,frame='icrs', unit="deg")
    

    #do the proper motion correction to the MJD
    StarMatch = AstrometryCoords.apply_space_motion(Time(MJD,format='mjd'))
    #StarMatch = SkyCoord(AstrometryPositions['RA'],AstrometryPositions['DEC'],frame="fk5", unit="deg")
    
    files = log['Filename'][((log['AOR']==AOR)&(log['ExposureID']==ID)).nonzero()]
    DCElist = log['DCE'][((log['AOR']==AOR)&(log['ExposureID']==ID)).nonzero()]
    
    #offset and weight values for astrometry
    RAstar = list()
    RAstarErr = list()
    DECstar = list()
    DECstarErr = list()
    
    RAmeas = list()
    RAmeasErr = list()
    DECmeas = list()
    DECmeasErr = list()
    
    DECpmCorr = list()
    RApmCorr = list()
    
    #merge the master star catalog with the measured values to get offsets
    for BCDfilename in files:
        
        #set up the file name for the input star catalog
        inputSuffix  = '_' + bcdSuffix + '.fits'
        outputSuffix = '_' + AstrocheckTableSuffix
        FrameCatFile = re.sub(inputSuffix,outputSuffix,BCDfilename) #Make the filename for the star catalogs
        
        #read in the star data for this frame
        #print(FrameCatFile)
        FrameStars = ascii.read(FrameCatFile,format="ipac") #read the data for the single frame catalog
        
        #match the frame to the refined
        FrameMatch = SkyCoord(FrameStars['RA']*u.deg,FrameStars['Dec']*u.deg) #put the catalog into the matching format
        idx,d2d,d3d=FrameMatch.match_to_catalog_sky(StarMatch) #do the match
        
        #loop over matches and calculate the offsets
        for i in range(0,len(idx)):
            if ((FrameStars['status'][i]!=0)&(d2d[i].arcsec <= AstroMergeRad)):
                #Put pm corrected reference DEC and error along with measurement in the array
                DECstar.append(AstrometryStars['dec'][idx[i]])
                DECstarErr.append(AstrometryStars['dec_error'][idx[i]]/(1000.0*3600.0))  #convert to degrees
                DECpmCorr.append(AstrometryStars['pmdec'].filled()[idx[i]]*PMtime/(1000.0*3600.0))#convert to degrees and multiply by time
                
                DECmeas.append(FrameStars['Dec'][i])
                DECmeasErr.append(FrameStars['delta_Dec'][i])
                
                #Put pm corrected reference RA and errror along with measurement in the array
                RAstar.append(AstrometryStars['ra'][idx[i]])
                RAstarErr.append(AstrometryStars['ra_error'][idx[i]]/(1000.0*3600.0*np.cos(AstrometryStars['ra'][idx[i]]*0.017453293)))  #convert to degrees
                RApmCorr.append(AstrometryStars['pmra'].filled()[idx[i]]*PMtime/(1000.0*3600.0*np.cos(AstrometryStars['ra'][idx[i]]*0.017453293)))#convert to degrees and multiply by time
                
                RAmeas.append(FrameStars['RA'][i])
                RAmeasErr.append(FrameStars['delta_RA'][i])
                

    #put the offests and errors into a masked array so we can do some outlier clipping and then estimate a weighted average offset

    dRA = ma.array([RAstar],dtype=np.double)-ma.array([RAmeas],dtype=np.double)
    dDEC = ma.array([DECstar],dtype=np.double)-ma.array([DECmeas],dtype=np.double)
    
    #variances for weighting
    RAvar = ma.array([RAmeasErr],dtype=np.double)*ma.array([RAmeasErr],dtype=np.double)+ma.array([RAstarErr],dtype=np.double)*ma.array([RAstarErr],dtype=np.double)
    DECvar = ma.array([DECmeasErr],dtype=np.double)*ma.array([DECmeasErr],dtype=np.double)+ma.array([DECstarErr],dtype=np.double)*ma.array([DECstarErr],dtype=np.double)
    
    #proper motions for masking
    RApmCorr = np.array([RApmCorr],dtype=np.double)
    DECpmCorr = np.array([DECpmCorr],dtype=np.double)

    #mask objects with large seperations and high-proper motion objects
    mask = np.zeros([dRA.size],dtype=np.bool)
    
    #calculate medians and robust errors for clipping
    med_dRA = ma.median(dRA)
    med_dDEC = ma.median(dDEC)
    sig_RA = ma.std(dRA)  #numpy mad converts to std automatically
    sig_DEC = ma.std(dDEC)
    
    #mask outliers
    Rout = ma.sqrt((dRA-med_dRA)*(dRA-med_dRA)+(dDEC-med_dDEC)*(dDEC-med_dDEC)).reshape(dRA.size) #radius of outlier
    Rlimit = ma.sqrt((sig_RA*sig_RA+sig_DEC*sig_DEC)) #sigma limit
    mask[(Rout >= Rlimit*3.0).nonzero()]=1
    
    #mask outliers
    dRA.mask +=mask
    dDEC.mask+=mask
    RAvar.mask +=mask
    DECvar.mask+=mask
    
    #calculate outlier value
    #corrRA=ma.average(dRA,weights=1.0/RAvar)
    #corrDEC=ma.average(dDEC,weights=1.0/DECvar)
    corrRA=ma.median(dRA)
    corrDEC=ma.median(dDEC)

    #re-calculate sig after clipping
    sig_RA = ma.std(dRA)
    sig_DEC = ma.std(dDEC)
    
    #count the number of stars left
    GoodStars=ma.count(dRA)
    
    print('Process frame {:5d} using {:3d} stars.  Offset is dRA = {:4.2f} +/- {:4.2f}; dDEC = {:5.2f} +/- {:4.2f}'.format(JobNo+1, GoodStars, corrRA*3600, 3600*sig_RA/np.sqrt(GoodStars), corrDEC*3600, 3600*sig_DEC/np.sqrt(GoodStars) ))

    astrofix = np.array([JobNo,corrRA,corrDEC,sig_RA/np.sqrt(GoodStars),sig_DEC/np.sqrt(GoodStars),GoodStars],dtype=np.double)
    return(astrofix)


#---------------------------------------------------------------------------------------------------
#
#---------------------------------------------------------------------------------------------------

def subtract_stars(JobNo,JobList,log,StarData,StarMatch):
    
    AOR = JobList['AOR'][JobNo]
    Ch = JobList['Channel'][JobNo]
    Njobs = len(JobList)
    
    #make the list of files for this AOR and Channel
    LogIDX = ((log['Channel']==Ch) & (log['AOR']==AOR)).nonzero()  # get the indexes of files we should use
    files = log['Filename'][LogIDX]
    MJDs = log['MJD'][LogIDX]
    RAs  = log['RA'][LogIDX]
    DECs = log['DEC'][LogIDX]
    
    Nframes = len(files)
    
    print('## Begin sub_stars job {:4d} - AOR {:8d} Ch {:}, {:3d} frames'.format(JobNo, AOR, Ch, Nframes))

    for fileNo in range(0,Nframes):
#    for fileNo in range(5,6):
        MJD = MJDs[fileNo]
        frameRA = RAs[fileNo]
        frameDEC= DECs[fileNo]
        BCDfilename = files[fileNo]

        #Get the image center for figuring out which objects to consider
        ImCenter = SkyCoord(frameRA,frameDEC, frame="fk5", unit="deg")

        if (MJD > WarmMJD):
            cryo = 0
        else:
            cryo = 1

        #setup  some file names
        #Setup file suffixes re replace
        inputSuffix  = '_' + bcdSuffix + '.fits'  #used in search
        basename = re.sub(inputSuffix,'',re.split('/',BCDfilename)[-1]) #get the base of the filename

        outputSuffix = '_' + BrightStarTableSuffix
        FrameCatFile = re.sub(inputSuffix,outputSuffix,BCDfilename)   # Make the filename for the star catalogs (bright.tbl)
        
        outputSuffix = '_' + ffSuffix + '.fits'
        ImageFile    = re.sub(inputSuffix,outputSuffix,BCDfilename)   # image file
        
        outputSuffix = '_' + corUncSuffix + '.fits'
        SigmaFile    = re.sub(inputSuffix,outputSuffix,BCDfilename)   # unc file
        
        outputSuffix = '_' + maskSuffix + '.fits'
        MaskFile     = re.sub(inputSuffix,outputSuffix,BCDfilename)   # mask file
        
        outputSuffix = '_' + starsubSuffix + '.fits'
        SubtractedFile = re.sub(inputSuffix,outputSuffix,BCDfilename) # star subtracted image file (stbcd.fits)
        
        outputSuffix = '_' + starMaskSuffix + '.fits'
        SubtractedMask = re.sub(inputSuffix,outputSuffix,BCDfilename) # star subtracted mask file (stmsk.fits)
        
        #remove output files
        rmCMD = 'rm -rf ' + SubtractedFile + ' ' + SubtractedMask
        os.system(rmCMD)
        
        #wait for file to be deleted
        while os.path.exists(SubtractedMask):
            wait = 1
        while os.path.exists(SubtractedFile):
            wait = 1
        
        #temporary files
        pid = os.getpid() #get the PID for temp files
        processTMPDIR = scratch_dir_prefix(cluster) + 'tmpfiles' + str(pid) + '-' + str(fileNo) + '/'
        os.system('mkdir -p ' + processTMPDIR)
#        print(" DEBUG: processTMPDIR is ",processTMPDIR)

        # build some filenames
        tmpStars = processTMPDIR + str(pid) + ".stars.tbl"
        residualImage = processTMPDIR + "Mosaic/residual_" + basename + '_' + ffSuffix + '.fits'  # actually the star-subtracted image
        bandcorrImage = processTMPDIR + "Mosaic/bandcorr_" + basename + '_' + ffSuffix + '.fits'

        #split the bandcorrImage into directory and file so the corrector doesn't truncate the file name if the name is too long
        bandcorrDIR = processTMPDIR + "Mosaic/"
        bandcorrFILE = "bandcorr_" + basename + '_' + ffSuffix + '.fits'
        
        #read in the star data for this frame (frame_bright.tbl)
        FrameStars = ascii.read(FrameCatFile,format="ipac") #read the data for the single frame catalog
#        print(" DEBUG:  length frame_bright.tbl: ",len(FrameStars))
#        print(" DEBUG:  length stars.refined.tbl: ",len(StarMatch))
        
        #match the frame to the refined
        FrameMatch = SkyCoord(FrameStars['RA']*u.deg,FrameStars['Dec']*u.deg) #put the catalog into the matching format

        BrightSep = StarMatch.separation(ImCenter)                      # Find stars near the frame
        BrightInFrameMatch = StarMatch[np.where(BrightSep.deg < 0.123)] # Keep only stars near the frame ??? how could you have anything outside the frame???
        BrightInFrameData = StarData[np.where(BrightSep.deg < 0.123)]   # Keep data from only stars near the frame from refined.tbl
        idx,d2d,d3d=FrameMatch.match_to_catalog_sky(BrightInFrameMatch) # do the match

        #make a copy of the data
        chlabel = 'ch' + str(Ch)
        if (SubtractBrightStars == False):  # set flux to near 0 in order to subtract a non-star
            BrightInFrameData[chlabel] = 0.0
        SubtractData = Table([BrightInFrameData['ID'],BrightInFrameData['ra'],BrightInFrameData['dec'],BrightInFrameData[chlabel]],names=('ID','RA','Dec','flux'))

        #put in the positions from this frame
        if (len(idx)>0):
            SubtractData['RA'][idx]=FrameStars['RA']
            SubtractData['Dec'][idx]=FrameStars['Dec']

        # Save the table - with only the bright stars included
        ascii.write(SubtractData[idx],tmpStars,format="ipac",overwrite=True)
        fixunits =  "sed -i -e 's/double/ float/g' " + tmpStars
        os.system(fixunits)

        ### And now for the actual star subtraction: call the star-subtracted image the "residual" image
        if (len(idx) > 0):
            print(">> File {:}: subtract {:} bright stars".format(fileNo, len(idx)))
#            subtractCMD='apex_qa.pl -n subtract_stars.nl  -T ' + ImageFile + ' -E ' + tmpStars + ' -P ' + PRF[cryo][Ch-1] + ' -O ' + processTMPDIR + ' > /dev/null 2>&1'
            # or, with logfile:
#            logfile = "{:}substar_{:}-{:}.log".format(TMPDIR, JobNo, fileNo)          # in local temp dir
            logfile = "{:}substar_{:}-{:}.log".format(processTMPDIR, JobNo, fileNo)    # in tmpfile dir
            subtractCMD='apex_qa.pl -n subtract_stars.nl  -T ' +ImageFile+ ' -E ' +tmpStars+ ' -P ' +PRF[cryo][Ch-1]+ ' -O ' +processTMPDIR+ ' > '+logfile+' 2>&1'
            os.system(subtractCMD)
#            # for DEBUG purposes: link original file to tempfiles dir
#            os.system("ln -s "+ ImageFile +" "+ bandcorrDIR)
        else: 
            # Nothing to subtract; copy input image to residual image for later work
            print("#### File {:}: No stars to subtract - copy input image".format(fileNo))
            os.system("mkdir " + bandcorrDIR)
            os.system("cp "+ ImageFile +" "+ residualImage)

        if (not os.path.isfile(residualImage)):
            print("#### ERROR ### {:} not found".format(residualImage))
            sys.exit()    # Maybe a bit brutal ....
        
        if(Ch <= 2):
            #read in the star star-subtracted (residual) image, if built, or the original
            subtractedHDU = fits.open(residualImage)
            subtractedWCS = wcs.WCS(subtractedHDU[0].header)  #read the WCS
            # read corrected bright star data
            SubtractData = ascii.read(tmpStars, format="ipac")  #; print(SubtractData)
            
            # If subtracting bright stars, then put flux values into image at subtracted star positions so bandcorr will work;
            # otherwise let the band corrector work on the flux of the stars
            Xpos,Ypos = subtractedWCS.wcs_world2pix(SubtractData['RA'],SubtractData['Dec'],1) #get x,y from wcs
            if (SubtractBrightStars == True):
                for starIDX in range(0,len(Xpos)):
                    for dx in range(-1,2):
                        for dy in range(-3,4):
                            ypix = int(round(Xpos[starIDX]+dx))
                            xpix = int(round(Ypos[starIDX]+dy))
                            if((xpix>=0) and (xpix<=255) and (ypix>=0) and (ypix<=255)):
                                subtractedHDU[0].data[xpix,ypix]+=SubtractData['flux'][starIDX]
                            
            #write out the image for the warm band corrector and do the banding correction
            subtractedHDU.writeto(bandcorrImage,overwrite='True')
            subtractedHDU.close()
            bandCorrCMD='cd ' + bandcorrDIR + '; bandcor_warm -f -t 20.0 -b 1 256 1 256 ' + bandcorrFILE + ' > /dev/null 2>&1'
            os.system(bandCorrCMD)
        
            bandcorrHDU = fits.open(bandcorrImage)
            # If subtracting bright stars, read back in the bandcorrected image, remove the inserted flux
            if (SubtractBrightStars == True):
                for starIDX in range(0,len(Xpos)):
                    for dx in range(-1,2):
                        for dy in range(-3,4):
                            ypix = int(round(Xpos[starIDX]+dx))
                            xpix = int(round(Ypos[starIDX]+dy))
                            if((xpix>=0) and (xpix<=255) and (ypix>=0) and (ypix<=255)):
                                bandcorrHDU[0].data[xpix,ypix]-=SubtractData['flux'][starIDX]
            
            if (not os.path.isfile(bandcorrImage)):
                print("#### ERROR ### {:} not found".format(bandcorrImage))
                sys.exit()

            #Mask the ghost from the bright star
            starMaskHDU = fits.open(MaskFile)
            StarIndex=np.indices([255,255]) #make an index vector for mask
            for starIDX in range(0,len(Xpos)):
                if((Xpos[starIDX]>=-1*PRFghostR[cryo][Ch-1]) and (Xpos[starIDX]<=(255+1*PRFghostR[cryo][Ch-1])) and (Ypos[starIDX]>=-1*PRFghostR[cryo][Ch-1]) and (Ypos[starIDX]<=(255+1*PRFghostR[cryo][Ch-1]))):
                    gx = Xpos[starIDX] + PRFghostDx[cryo][Ch-1]
                    gy = Ypos[starIDX] + PRFghostDy[cryo][Ch-1]
                    GhostMask =np.sqrt(((StarIndex[1]-gx)**2) + ((StarIndex[0]-gy)**2))
                    starMaskHDU[0].data[(GhostMask<=PRFghostR[cryo][Ch-1]).nonzero()]=32767
        
            bandcorrHDU.writeto(SubtractedFile,overwrite='True')  #write out the final star subtracted image
            bandcorrHDU.close()
            starMaskHDU.writeto(SubtractedMask,overwrite='True')  #write out the modified star mask
            starMaskHDU.close()
            # and build bandcorr.fits (difference image with correction only)
#            comm=("/home/moneti/softs/python/imsub.py {:} {:} {:}bandcorr.fits".format(bandcorrImage, residualImage, bandcorrDIR)); print(comm)
#            os.system(comm)
        else:
            shutil.move(residualImage,SubtractedFile)
            shutil.copy(MaskFile,SubtractedMask)

#        print(' DEBUG: Wrote star_subtracted frame {:3d}: {:}'.format(fileNo, SubtractedFile.split('/')[-1]))
#        os.system("rm " + logfile )
        error = False

        # clean up
        #wait for file to be in place
        while os.path.exists(SubtractedMask) == 'False' :
            wait = 1
        while os.path.exists(SubtractedFile) == 'False':
            wait = 1

        if (error == False):
            cleanupCMD = 'rm -rf ' + processTMPDIR
            os.system(cleanupCMD)

    print('## Finished job {:4d}: AOR {:8d} Ch {:}'.format(JobNo, AOR, Ch))


#---------------------------------------------------------------------------------------------------
#
#---------------------------------------------------------------------------------------------------

def subtract_median(JobNo,JobList,log,AstroFix):
    
    AOR = JobList['AOR'][JobNo]
    Ch = JobList['Channel'][JobNo]
    
    #read the list of images we should subtract
    AORsubtractFile = AORoutput + 'files.' + str(AOR) + '.ch.' + str(Ch) + '.tbl'
    AORinfo = ascii.read(AORsubtractFile,format="ipac") #read the data
    
    #make a list of images to subtract
    repList = list(set(AORinfo['RepName']))
    Nreps = len(repList)
    medianData=np.zeros([Nreps,256,256],dtype=np.double)
    for repIDX in range(0,Nreps):
        medFile = AORoutput + BackgroundType +'.' + str(AOR) + '.' + repeats[repIDX] + '.ch.' + str(Ch) + '.fits'
        medHDU = fits.open(medFile)
        medianData[repIDX]=medHDU[0].data
    
    #make the list of files for this AOR and Channel
    LogIDX = ((log['Channel']==Ch) & (log['AOR']==AOR)).nonzero()  # get the indexes of files we should use
    files = log['Filename'][LogIDX]
    DCElist = log['DCE'][LogIDX]
    Nframes = len(files)

    print('## Begin subtr_median job {:4d} - AOR {:8d} Ch {:}, {:3d} frames'.format(JobNo, AOR, Ch, Nframes))

    for frame in range(0,Nframes):
        BCDfilename = files[frame] 
        DCE = DCElist[frame]

        #get the offset in RA/DEC
        dRA = np.double(AstroFix['dRA'][(AstroFix['DCE']==DCE).nonzero()])
        dDEC = np.double(AstroFix['dDEC'][(AstroFix['DCE']==DCE).nonzero()])
        
        #Setup file suffixes re replace
        inputSuffix  = '_' + bcdSuffix + '.fits'  #used
        
        #set up the file names
        outputSuffix = '_' + starsubSuffix + '.fits'
        ImageFile       = re.sub(inputSuffix,outputSuffix,BCDfilename) #Star Subtracted File
        
        outputSuffix = '_' + SubtractedSuffix + '.fits'
        SubtractedFile  = re.sub(inputSuffix,outputSuffix,BCDfilename) #Background subtracted File
        
        outputSuffix = '_' + corUncSuffix + '.fits'
        NoiseFile  = re.sub(inputSuffix,outputSuffix,BCDfilename) #Uncertanty File
        
        outputSuffix = '_' + ScaledUncSuffix + '.fits'
        ScaledNoiseFile = re.sub(inputSuffix,outputSuffix,BCDfilename) #Uncertanty File
        
        outputSuffix = '_' + starMaskSuffix + '.fits'
        MaskFile   = re.sub(inputSuffix,outputSuffix,BCDfilename) #mask File
        
        #figure out the frame to subtract, if not found subtract the first one
        repIDX = AORinfo['RepIndex'][(AORinfo['DCE']==DCE).nonzero()]
        if not(repIDX):  #test if the value was not found and set it to the first median for HDR frames
            repIDX=0
        else:
            repIDX=int(repIDX)
        
        #Read image in, subtract median
#        print("DEBUG: open image file {:} ".format(ImageFile))   #DEBUG
        imageHDU = fits.open(ImageFile) #Read image
        imageData = ma.masked_invalid(imageHDU[0].data)
        imageData= imageData - medianData[repIDX] #Subtract median image
        
        #Read the mask
        maskHDU = fits.open(MaskFile)
        maskImage=maskHDU[0].data
        imageData.mask += maskImage.astype(bool)
        
        #do some masking to figure out background to subtract
        #measure stats to clip object
        goodData = ma.MaskedArray.compressed(imageData)  #kudge to get rid of lower case nans
        median = ma.median(goodData[np.logical_not(np.isnan(goodData))])
        rms = robust.mad(goodData[np.logical_not(np.isnan(goodData))])
        
        #mask objects to get background
        maxval = median + 3.0*rms  #Clip at + 3 sigma
        minval = median - 3.0*rms  #clip at - 3 sigma
        
        #object masking
        objmask = np.zeros([256,256],dtype=np.bool)  #set up a holding variable for the object mask
        objmask[(imageData >= maxval).nonzero()]=1  #mask bright objects
        objmask[(imageData <= minval).nonzero()]=1  #mask negative holes
        objmask = ndimage.binary_dilation(objmask) #grow the mask
        objmask = ndimage.binary_dilation(objmask) #grow the mask a second time
        objmask = ndimage.binary_dilation(objmask) #grow the mask a third time
        imageData.mask += objmask #add it to bad pixel mask
        
        #do some masking to figure out background to subtract
        #re-measure stats after masking objects
        goodData = ma.MaskedArray.compressed(imageData)  #kudge to get rid of lower case nans
        median = ma.median(goodData[np.logical_not(np.isnan(goodData))])
        rms = robust.mad(goodData[np.logical_not(np.isnan(goodData))])
        
        imageHDU[0].data= imageHDU[0].data - medianData[repIDX] #Subtract the background image
        imageHDU[0].data-=median #subtract the median background level
        imageHDU[0].header['CRVAL1']+=dRA #fix the astrometry
        imageHDU[0].header['CRVAL2']+=dDEC
        goodRA = imageHDU[0].header['CRVAL1']
        goodDE = imageHDU[0].header['CRVAL2']
        imageHDU.writeto(SubtractedFile,overwrite='True') #write output image
#        print("DEBUG: wrote sub file  {:} ".format(SubtractedFile))   # DEBUG
        
        #scale the RMS to the correct value due to the incorrect bias pedistle
        #we want the variance of the background and the noise image to match in an additive fassion
        #The incorrect scaling is due to an additive factor in the vairance that is incorrect
        
        #read the rms data and mask it
        rmsHDU = fits.open(NoiseFile) #read the noise file
        #print("DEBUG: open noise file {:} ".format(NoiseFile))
        rmsImage = ma.masked_invalid(rmsHDU[0].data) #mask bad values
        rmsImage.mask += imageData.mask #apply same mask as used to measure RMS in image, this removes objects and gets rms of the background
        
        #measre the average variance in the noise image ad scale
        goodRMS = ma.MaskedArray.compressed(rmsImage)  #kudge to get rid of lower case nans
        var = ma.average(np.power(goodRMS,2)) #calcualte the average variance
        scaleLevel = var-rms*rms #determine the pedistle level
        #print("DEBUG: Pedestal level: {:}".format(scaleLevel))

        rmsHDU[0].data = np.sqrt(rmsHDU[0].data*rmsHDU[0].data-scaleLevel) #subtract the pedistle
        rmsHDU[0].header['CRVAL1'] = goodRA  #+=dRA #fix the astrometry
        rmsHDU[0].header['CRVAL2'] = goodDE  #+=dDEC
        rmsHDU.writeto(ScaledNoiseFile,overwrite='True') #write output scaled noise
        #print("DEBUG: wrote scaled noise {:} ".format(ScaledNoiseFile))
        #print("DEBUG: =======  Finished with frame {:}  ========".format(frame))

    print('## Finished job {:4d}: AOR {:8d} Ch {:}'.format(JobNo, AOR, Ch))


#---------------------------------------------------------------------------------------------------
#
#---------------------------------------------------------------------------------------------------

def make_median_image(JobNo, JobList, log, AORlog, debug):
    
    if (debug == 1):
        print("### ACTIVATED DEBUG MODE ###")

    AOR = JobList['AOR'][JobNo]
    Ch  = JobList['Channel'][JobNo]
    HDR = JobList['HDR'][JobNo]

    #make the list of files for this AOR and Channel
    if HDR == 'True':
        #in HDR mode grab all files
        LogIDX = ((log['Channel']==Ch) & (log['AOR']==AOR)).nonzero()  # get the indexes of files we should use
        hdrm = "mode HDR"
    else:
        #in standar mode just drop first few exposures that have shorter exposure time
        ExptimeNormal = np.max(log['ExpTime'][((log['Channel']==Ch) & (log['AOR']==AOR) & (log['HDR']=='False')).nonzero()])
        LogIDX = ((log['Channel']==Ch) & (log['AOR']==AOR) & (log['ExpTime']==ExptimeNormal)).nonzero()  # get the indexes of files we should use with normal exposure times
        hdrm = "mode STD"
    
    files = log['Filename'][LogIDX]
    DCElist = log['DCE'][LogIDX]
    Nframes = len(files)
    
    print('## Begin make_medians job {:4d} - AOR {:8d} Ch {:}, {:3d} frames, {:}'.format(JobNo, AOR, Ch, Nframes, hdrm))

    #read in the files
    imageData  = ma.zeros([Nframes,256,256],dtype=np.double) #data images
    ivarImages = np.zeros([Nframes,256,256],dtype=np.double) #inverse variance images
    maskImages = np.zeros([Nframes,256,256],dtype=np.int) #image masks
    DelayTimes = np.zeros([Nframes],dtype=np.double) # list of frame delay times

    # AMo: For each obs, there are Nreps frames obtained at each of Npos positions. The Nreps have
    # increasing exp times; we assume that the first and shortest is the same for all positions.
    # There are cases of missing frames; these are solved by hand, by commenting all the frames at
    # that position.
    # Figure out the number of repeat observations
    if HDR == 'True':
        #If HDR mode just look for different exposure times ... fails when these are all the same
        #Exptimes = list(set(log['ExpTime'][LogIDX]))
        #Nreps = len(Exptimes)
        # ... rather find num occurrences of minimum time, gives num pos
        Alltimes = log['ExpTime'][LogIDX]
        Tmin  = Alltimes.min()  # assume always same for each series of repeats
        Nposn = list(Alltimes).count(Tmin)  # Number of positions
        Nreps = int(len(Alltimes)/Nposn)     # Number of repeats
    else:
        #In normal mode just find the frames with long frame delays, repeats typically have ~2s delays.
        LongDelays =  np.where(log['FrameDelay'][LogIDX] > 6)  #Find the long delays
        NumLongDelay = len(log['FrameDelay'][LongDelays]) #Count them
        Nreps = int(Nframes/NumLongDelay) #calculate the number of repeats

    NrepFrames = int(Nframes/Nreps) #Calculate the number of repeated frames

    if HDR == 'True':
        print(' - AOR {:} Ch {:} in HDR mode; has {:} obs at each position'.format(AOR, Ch, Nreps))
        if debug == 1: print("   exp times are: {:}".format(Exptimes))
    else:
        print('## AOR {:} Ch {:} in STD mode; has {:} obs at each position,'.format(AOR, Ch, Nreps), end=' ')
        if Nreps > 1:
            print('has {:} frames, {:} per repeat.'.format(Nframes, NrepFrames))
        else:
            print('has {:} frames.'.format(Nframes))

    #lets do some error checking
    if (Nframes == NrepFrames*Nreps):
        if (debug == 1): print('DEBUG: Found expected number of frames .... continue')
    else:
        print('WARNING: Total number of frames {:}, number of repeats {:}, and repeats per frame {:} disagree!'.format(Nframes, NrepFrames, Nreps))
        print('         Found {:} frames, expected {:} '.format(Nframes, NrepFrames*Nreps))


    for frame in range(0,Nframes):
        BCDfilename = files[frame]
        
        #Setup file suffixes re replace
        inputSuffix  = '_' + bcdSuffix + '.fits'  #used
        
        outputSuffix = '_' + starsubSuffix + '.fits'
        ImageFile  = re.sub(inputSuffix,outputSuffix,BCDfilename) #Star Subtracted File
        
        outputSuffix = '_' + corUncSuffix + '.fits'
        NoiseFile  = re.sub(inputSuffix,outputSuffix,BCDfilename) #Uncertanty File
        
        outputSuffix = '_' + starMaskSuffix + '.fits'
        MaskFile   = re.sub(inputSuffix,outputSuffix,BCDfilename) #mask File
        
        #Read image
        imageHDU = fits.open(ImageFile)
        imageData[frame]=ma.masked_invalid(imageHDU[0].data)  #create masked array with NaN's masked
        DelayTimes[frame]=imageHDU[0].header['FRAMEDLY'] #get the frame delays to figure out repeats
        
        imageHDU = fits.open(NoiseFile)
        ivarImages[frame]=np.power(imageHDU[0].data,-2)
        
        imageHDU = fits.open(MaskFile)
        maskImages[frame]=imageHDU[0].data
        
        #measure stats
        median = ma.median(np.nan_to_num(imageData[frame]))
        rms = robust.mad(np.nan_to_num(imageData[frame].reshape(256*256)))
        
        #mask outside of background
        maxval = median + ClipSigmaPos*rms  #Clip at + 3 sigma
        minval = median - ClipSigmaNeg*rms  #clip at - 3 sigma
        
        #object masking
        objmask = np.zeros([256,256],dtype=np.bool)  #set up a holding variable for the object mask
        objmask[(imageData[frame] >= maxval).nonzero()]=1  #mask bright objects
        objmask[(imageData[frame] <= minval).nonzero()]=1  #mask negative holes
        
        #grow the mask Ndilation times
        if Ndilation > 0:
            for dilate in range(0,Ndilation):
                objmask = ndimage.binary_dilation(objmask)
    
        imageData[frame].mask += objmask #add it to bad pixel mask
        
        #add pixel mask
        imageData[frame].mask += maskImages[frame].astype(bool)
    
        #subtract the median from the image to make next phase of clipping better
        imageData[frame] -= ma.median(np.nan_to_num(imageData[frame]))

        #print 'Read ' + str(frame+1) + ' of ' + str(Nframes)


    #make a list of files for subtraction
    repNameList=list()
    frameIDX = 0
    for imIDX in range(0,NrepFrames):
        for repIDX in range(0,Nreps):
            repNameList.append([files[frameIDX],DCElist[frameIDX],AOR,Ch,repeats[repIDX],repIDX])
            frameIDX +=1
    AORsubtractTable=Table(rows=repNameList,names=['Filename','DCE','AOR','Channel','RepName','RepIndex'])
    AORsubtractFile = AORoutput + 'files.' + str(AOR) + '.ch.' + str(Ch) + '.tbl'
    ascii.write(AORsubtractTable,AORsubtractFile,format="ipac",overwrite=True)

    if (Nreps > 1):
        #reorder data into repeates
        
        #Declare new arrays with correct shapes
        ReorgImageData  = ma.zeros([Nreps, NrepFrames, 256, 256],dtype=np.double) #data images
        ReorgIvarImages = np.zeros([Nreps, NrepFrames, 256, 256],dtype=np.double) #inverse variance images
        ReorgMaskImages = np.zeros([Nreps, NrepFrames, 256, 256],dtype=np.int) #image masks
        
        #reorganize the data
        repIDX=0
        imIDX=0
        for frame in range(0,Nframes):
            ReorgImageData[repIDX,imIDX] = imageData[frame]
            ReorgIvarImages[repIDX,imIDX] = ivarImages[frame]
            ReorgMaskImages[repIDX,imIDX] = maskImages[frame]
            
            #index rep counter and check if its greater than Nreps
            repIDX+=1
            if (repIDX >= Nreps):
                imIDX+=1  #increase frame index counter
                repIDX=0
    
        #loop over repeates to clip outliers then make median image
        for repIDX in range(0,Nreps):
            #calculate median images and stdev
            median_image = ma.median(ReorgImageData[repIDX],axis=0)
            stdev_image  = robust.mad(np.nan_to_num(ReorgImageData[repIDX]),axis=0)
            maximage = median_image +ClipSigmaPos*stdev_image
            minimage = median_image -ClipSigmaNeg*stdev_image
            
            #clip the pixels in each images
            for imIDX in range(0,NrepFrames):
                pixmask = np.zeros([256,256],dtype=np.bool)  #set up a holding variable for pixel mask
                pixmask[(ReorgImageData[repIDX,imIDX] >= maximage).nonzero()]=1  #fill it with object mask
                pixmask[(ReorgImageData[repIDX,imIDX] <= minimage).nonzero()]=1
                ReorgImageData[repIDX,imIDX].mask+=pixmask
        
            #make the output background
            output_image=ma.average(ReorgImageData[repIDX],axis=0,weights=ReorgIvarImages[repIDX])
            output_data=ma.filled(output_image,fill_value=0)
            
            #write the output file
            outputFile = AORoutput + 'average.' + str(AOR) + '.' + repeats[repIDX] + '.ch.' + str(Ch) + '.fits'
            print(' . Writing ' + outputFile, end=' ... ')
            fits.writeto(outputFile,output_data,overwrite='True')
            
            #make the output background
            output_image=ma.median(ReorgImageData[repIDX],axis=0) #median works better for outliers
            output_data=ma.filled(output_image,fill_value=0)
            
            #write the output file
            outputFile = AORoutput + 'median.' + str(AOR) + '.' + repeats[repIDX] + '.ch.' + str(Ch) + '.fits'
            print(outputFile.split('/')[-1])
            fits.writeto(outputFile,output_data,overwrite='True')
    else:
        repIDX=0
        #calculate median images and stdev
        median_image = ma.median(imageData,axis=0)
        stdev_image  = robust.mad(np.nan_to_num(imageData),axis=0)
        maximage = median_image +ClipSigmaPos*stdev_image
        minimage = median_image -ClipSigmaNeg*stdev_image
        
        #clip the pixels in each images
        for imIDX in range(0,NrepFrames):
            pixmask = np.zeros([256,256],dtype=np.bool)  #set up a holding variable for pixel mask
            pixmask[(imageData[imIDX] >= maximage).nonzero()]=1  #fill it with object mask
            pixmask[(imageData[imIDX] <= minimage).nonzero()]=1
            imageData[imIDX].mask+=pixmask

        #make the output background
        output_image=ma.average(imageData,axis=0,weights=ivarImages)
        output_data=ma.filled(output_image,fill_value=0)
        
        #write the output file
        outputAve = AORoutput + 'average.' + str(AOR) + '.' + repeats[repIDX] + '.ch.' + str(Ch) + '.fits'
        fits.writeto(outputAve,output_data,overwrite='True')
        
        #make the output background
        output_image=ma.median(imageData,axis=0) #median works better
        output_data=ma.filled(output_image,fill_value=0)
        
        #write the output file
        outputMedi = AORoutput + 'median.' + str(AOR) + '.' + repeats[repIDX] + '.ch.' + str(Ch) + '.fits'
        fits.writeto(outputMedi,output_data,overwrite='True')
        print('==> Wrote {:} and {:} '.format(outputAve, outputMedi.split('/')[-1]))

    print('## Finished job {:4d}: AOR {:8d} Ch {:}'.format(JobNo, AOR, Ch))


#---------------------------------------------------------------------------------------------------
#
#---------------------------------------------------------------------------------------------------
def run_mosaic_geometry(JobNo,JobList):
    
    Ch = JobList['Channel'][JobNo]
    Tile = JobList['TileNumber'][JobNo]
    
    #temporary files
#    pid = os.getpid() #get the PID for temp files
    processTMPDIR = scratch_dir_prefix(cluster) + 'tmpdir_{:}_geom_{:}/'.format(PIDname, JobNo)
    os.system('mkdir -p ' + processTMPDIR)
    
    #input list
    imagelist = OutputDIR + PIDname + '.irac.' + str(Ch) + '.' + SubtractedSuffix + '.lst'
    
    #output list
    geomlist = processTMPDIR + 'geom_' + PIDname + '.irac.' + str(Ch) + '.' + SubtractedSuffix + '.lst'
    
    #Run mosaic.pl
    logfile = '{:}mosaic_geom_{:}.log'.format(processTMPDIR, JobNo)  
    cmd = 'mosaic.pl -n ' +IRACTileGeomConfig+ ' -I ' +imagelist+ ' -F' +JobList['FIF'][JobNo]+ ' -O ' +processTMPDIR+ ' > '+logfile+' 2>&1'
    #print(cmd)   ## DEBUG
    os.system(cmd)
    
    ### NB if above fails, the following is not done, including 
    #count the number of files in mosaic geometry
    num_files = sum(1 for line in open(geomlist))
    print("Using input list {:} with {:} entries".format(imagelist, num_files))

    # AMo: copy geomlist to OutputDIR
    outName = '{:}{:}.irac.tile.{:}.{:}.{:}.lst'.format(OutputDIR, PIDname, Tile, Ch, SubtractedSuffix)
    shutil.copy(geomlist, outName)

    # AMo: copy logfile to tempDIR [, prepend command]
    outname = '{:}mosaic_geom_{:}.log'.format(TMPDIR, JobNo)
#    os.system("echo {:} > ${:}; echo '=================' >> {:}".format(cmd, logfile, logfile)
    shutil.copy(logfile, outname)

    print("## Finished job {:}; found {:} files in tile {:} ch{:}".format(JobNo, num_files, Tile, Ch))
    cleanupCMD = 'rm -rf ' + processTMPDIR
#    print(cleanupCMD)    ## DEBUG
    os.system(cleanupCMD)
    
    return(num_files)


#---------------------------------------------------------------------------------------------------
#
#---------------------------------------------------------------------------------------------------

def find_outlier_tile(JobNo, JobList, debug):

    if (debug == 1):
        print("### ACTIVATED DEBUG MODE ###")

    Ch = JobList['Channel'][JobNo]
    Tile = JobList['TileNumber'][JobNo]
    Nframes = JobList['NumFrames'][JobNo]
    
    # temporary files: use local scratch area on process node, if large, to avoid heavy network usage
    processTMPDIR = "{:}tmpdir_{:}_tile_j{:d}".format(scratch_dir_prefix(cluster), PIDname, JobNo)    
    shutil.rmtree(processTMPDIR, ignore_errors=True)    # delete it already existing
    os.system('mkdir -p ' + processTMPDIR)              # and create a fresh one

    if os.path.dirname(processTMPDIR):
        if debug == 1: print("DEBUG: Clean temp dir {:} created".format(processTMPDIR))
    else:
        print("## ERROR: could not create temp dir {:} .... quitting".format(processTMPDIR))
        sys.exit(3)
    
    print("## Begin find_outliers job {:} for tile {:}, chan {:}, {:} frames ; tmpdir is {:}".format(JobNo, Tile, Ch, Nframes,  processTMPDIR))

    #input lists
    imagelist = OutputDIR + PIDname + '.irac.' + str(Ch) + '.' + SubtractedSuffix + '.lst'
    masklist  = OutputDIR + PIDname + '.irac.' + str(Ch) + '.' + starMaskSuffix + '.lst'
    unclist   = OutputDIR + PIDname + '.irac.' + str(Ch) + '.' + ScaledUncSuffix + '.lst'
    
    #Run Mosaic
    logfile = 'outliers_{:d}.log'.format(JobNo)
    if debug == 1: print("DEBUG: logfile is {:}".format(logfile))
    cmd = 'mosaic.pl -n ' + IRACOutlierConfig + ' -I ' + imagelist + ' -S ' + unclist + ' -d ' + masklist + ' -F' + JobList['FIF'][JobNo] + ' -M ' + IRACPixelMasks[Ch-1] + ' -O ' +processTMPDIR+ ' > '+ logfile+' 2>&1 '
#    cmd = 'mosaic.pl -n ' + IRACTileConfig + ' -I ' + imagelist + ' -S ' + unclist + ' -d ' + masklist + ' -F' + JobList['FIF'][JobNo] + ' -M ' + IRACPixelMasks[Ch-1] + ' -O ' +processTMPDIR
    print(">> command line is:")
    print("   "+cmd)
    os.system(cmd)
    
    #-----------------------------------------------------------------------------
    # mopex work done, now copy the files to their proper places in the $WRK
    #-----------------------------------------------------------------------------
    basename = "{:}{:}.irac.tile.{:}.{:}".format(OutputDIR, PIDname, Tile, Ch)
    print(">> Products root name: {:}".format(basename))
    cperrs = 0  # to keep track of errors

    inf = processTMPDIR + '/Combine-mosaic/mosaic.fits'; 
    out = basename + '.mosaic.fits'
    if os.path.isfile(inf):  
        shutil.copy(inf, out)
    else:
        print("## ERROR: {:} not found".format(inf)); cperrs += 1
    
    inf = processTMPDIR + '/Combine-mosaic/mosaic_unc.fits'
    out = basename + '.mosaic_unc.fits'
    if os.path.isfile(inf):  
        shutil.copy(inf, out)
    else:
        print("## ERROR: {:} not found".format(inf)); cperrs += 1

    inf = processTMPDIR + '/Combine-mosaic/mosaic_cov.fits'
    out = basename + '.mosaic_cov.fits'
    if os.path.isfile(inf):  
        shutil.copy(inf, out)
    else:
        print("## ERROR: {:} not found".format(inf)); cperrs += 1
    
    inf = processTMPDIR + '/Combine-mosaic/mosaic_std.fits'
    out = basename + '.mosaic_std.fits'
    if os.path.isfile(inf):  
        shutil.copy(inf, out)
    else:
        print("## ERROR: {:} not found".format(inf)); cperrs += 1


    #-----------------------------------------------------------------------------
    # move the output rmasks to RMaskDir when they can be combined; 
    # must do in loop as may be too many for unix wildcard; use copy, not move, as
    # latter fails when working across filesystems
    #-----------------------------------------------------------------------------
    RMaskOutdir = RMaskDir + 'tile_{:}/'.format(Tile)
    os.system('mkdir -p ' + RMaskOutdir)

    print('>> Look for Rmask files to move')
    RMaskImages = processTMPDIR + '/Rmask-mosaic/'
    fileList = TMPDIR + "rmasks_to_move_job_{:}.lst".format(JobNo)
    findCmd  = "find {:} -name '*_rmask.fits' > {:}".format(RMaskImages, fileList)
    if debug == 1: print("DEBUG: {:}".format(findCmd))
    os.system(findCmd)
    nmoved = 0
    with open(fileList, 'r') as file:
        for line in file:
            fin = line.strip('\n')
            fout = fin.split('/')[-1]
            if debug == 1: print("DEBUG: shutil.copy({:}, {:})".format(fin, RMaskOutdir+fout))
            shutil.copy(fin, RMaskOutdir + fout)
            nmoved += 1
    if (nmoved == 0):
        print("## ERROR: Found no rmask files for tile {:}, chan {:}".format(Tile, Ch))
        cperrs += 1
    else:
        print(">> Copied {:} rmask files from {:} to {:}".format(nmoved, RMaskImages, RMaskOutdir))
    os.system("rm " + fileList) 

    #-----------------------------------------------------------------------------
    # cp the median_mosaic products to the output dir
    #-----------------------------------------------------------------------------

    inf = processTMPDIR + '/Combine-mosaic/median_mosaic.fits'
    out = medmosaic = basename  + '.median_mosaic.fits'
    if os.path.isfile(inf):  
        shutil.copy(inf, out)
    else:
        print("## ERROR: {:} not found".format(inf)); cperrs += 1

    inf = processTMPDIR + '/Combine-mosaic/median_mosaic_unc.fits'
    out = medmosaicunc = basename + '.median_mosaic_unc.fits'
    if os.path.isfile(inf):  
        shutil.copy(inf, out)
    else:
        print("## ERROR: {:} not found".format(inf)); cperrs += 1
    
    #-----------------------------------------------------------------------------
    # clean up:  done in shell script if all products found
    #-----------------------------------------------------------------------------
    if cperrs > 0:
        print("## Found {:} ERRORs in find_outliers job {:} ... see {:} for details.".format(cperrs, JobNo, logfile))
        print("## tempdir {:} NOT deleted".format(processTMPDIR))
        sys.exit(3)
    else:
        print(">> Copied  {:}.median_mosaic*.fits to {:}".format(basename, OutputDIR))
        print("## Finished job {:} succesfully; delete its tempdir.".format(JobNo))
        cleanupCMD = 'rm -rf ' + processTMPDIR  #; print(cleanupCMD)
        os.system(cleanupCMD)


#---------------------------------------------------------------------------------------------------
#used to flag rmask files in multiple outlier rejection tiles above
#---------------------------------------------------------------------------------------------------

def get_rmask_dce(FileNo, RmaskFileList):

    RmaskFile = RmaskFileList['Filename'][FileNo] #get the file name
    
    imageHDU = fits.open(RmaskFile) #Read image
    DCEnumber = imageHDU[0].header.get('DCEID') #Read the DCE number
    imageHDU.close()
    return(DCEnumber)


#---------------------------------------------------------------------------------------------------
# used to combine the rmaks together into single files and copy them back to the data directory
#---------------------------------------------------------------------------------------------------

def combine_rmasks(JobNo, RmaskFileList, log):

    DCE =  log['DCE'][JobNo]
    Ch = log['Channel'][JobNo]
    basefilename = log['Filename'][JobNo]
    RMaskFiles = list(set(RmaskFileList['Filename'][(RmaskFileList['DCE']==DCE).nonzero()]))
    Nfiles = len(RMaskFiles)
#    print("## Begin job {:} with {:} files".format(JobNo, Nfiles))
    
    if ( Nfiles == 0 ):
        print("## ERROR job {:} DCE {:} has no rmask files ... ".format(JobNo, DCE))
    else:
        #setup the output file
        inputSuffix  = '_' + bcdSuffix + '.fits'
        outputSuffix = '_' + rmaskSuffix + '.fits'
        outputRMask = re.sub(inputSuffix, outputSuffix, basefilename)
        
        Rmask_data = np.zeros([256,256], dtype=np.uint8)
        for rmask in RMaskFiles: # here we do the actual combination
            imageHDU = fits.open(rmask)
            Rmask_data = Rmask_data | imageHDU[0].data #copy over the mask data in the overlapping area, set rest to 0

        imageHDU[0].data = Rmask_data
        imageHDU.writeto(outputRMask,overwrite='True')
        imageHDU.close()
        # check that array is not null everywhere
        if (Rmask_data.max() == 0):
            print("PROBLEM: max is null for frame {:}".format(Rmask_data))
        print("## Finished job {:} with {:} tiles - wrote combined Rmask to {:}".format(JobNo, Nfiles, outputRMask))

#---------------------------------------------------------------------------------------------------
#
#---------------------------------------------------------------------------------------------------

def build_mosaic(Ch):
    
    # temporary files:
    # use local scratch area on process node, if large, to avoid heavy network usage
    processTMPDIR =  scratch_dir_prefix(cluster) + 'BuildMosaicDir_' + PIDname + '_Ch' + str(Ch) + '/'
    shutil.rmtree(processTMPDIR, ignore_errors=True)    # delete it already existing
    os.system('mkdir -p ' + processTMPDIR)              # and create a fresh one
    
    if os.path.dirname(processTMPDIR):
        print(">> Clean temp dir {:} created".format(processTMPDIR))
    else:
        print("## ERROR: could not create temp dir .... quitting")
        sys.exit(3)

    print("## Begin build_mosaic ch {:}; tmpdir is {:}".format(Ch, processTMPDIR))

    #input lists
    imagelist = OutputDIR + PIDname + '.irac.' + str(Ch) + '.' + SubtractedSuffix + '.lst'
    masklist  = OutputDIR + PIDname + '.irac.' + str(Ch) + '.' + starMaskSuffix  + '.lst'
    unclist   = OutputDIR + PIDname + '.irac.' + str(Ch) + '.' + ScaledUncSuffix + '.lst'
    rmasklist = OutputDIR + PIDname + '.irac.' + str(Ch) + '.rmask.lst'

    #input FIF
    iracFIF   = OutputDIR + PIDname + '.irac.FIF.tbl'

    #Run Mosaic
    logfile = 'build_mosaic_ch{:}.log'.format(Ch)
    print(">> logfile is {:}".format(logfile))
    cmd = 'mosaic.pl -n ' + IRACMosaicConfig + ' -I ' + imagelist + ' -S ' + unclist + ' -d ' + masklist + ' -R ' + rmasklist + ' -F ' + iracFIF + ' -M ' + IRACPixelMasks[Ch-1] + ' -O ' +processTMPDIR+ ' > '+ logfile+' 2>&1 '
    print(">> command line is:")
    print("   "+cmd)
    os.system(cmd)
    
    # check if it finshed properly
    errfile="build_mosaic_ch{:}.err".format(Ch)
    os.system("grep Error {:} > {:}".format(logfile, errfile))
    Nlines = sum(1 for l in open(errfile, 'r'))
    if (Nlines == 0):
        os.system("rm "+ errfile)
    else:
        print("## ATTN: found errors in mopex logfile {:} ".format(logfile))

    #-----------------------------------------------------------------------------
    # Finished with mopex ... move the files to the Outputs directory
    #-----------------------------------------------------------------------------
    basename = OutputDIR + PIDname + '.irac.' + str(Ch)
    print(">> Products root name: {:}".format(basename))
    cperrs = 0

    inf = processTMPDIR + 'Combine-mosaic/mosaic.fits'
    out = basename + '.mosaic.fits'
    if os.path.isfile(inf):  
        shutil.copy(inf, out)
    else:
        print("## ERROR: {:} not found".format(inf)); cperrs = 1

    inf = processTMPDIR + 'Combine-mosaic/mosaic_unc.fits'
    out = basename + '.mosaic_unc.fits'
    if os.path.isfile(inf):  
        shutil.copy(inf, out)
    else:
        print("## ERROR: {:} not found".format(inf)); cperrs = 1

    inf = processTMPDIR + 'Combine-mosaic/mosaic_cov.fits'
    out = basename + '.mosaic_cov.fits'
    if os.path.isfile(inf):  
        shutil.copy(inf, out)
    else:
        print("## ERROR: {:} not found".format(inf)); cperrs = 1

    inf = processTMPDIR + 'Combine-mosaic/mosaic_std.fits'
    out = basename + '.mosaic_std.fits'
    if os.path.isfile(inf):  
        shutil.copy(inf, out)
    else:
        print("## ERROR: {:} not found".format(inf)); cperrs = 1

    # these are optional; don't declare error if not found
    inf = processTMPDIR + 'Combine-mosaic/median_mosaic.fits'
    out = basename + '.median_mosaic.fits'
    if os.path.isfile(inf):
        shutil.copy(inf, out)
    else:
        print("## WARNING: optional {:} not found.".format(inf))  #; cperrs = 1

    inf = processTMPDIR + 'Combine-mosaic/median_mosaic_unc.fits'
    out = basename + '.median_mosaic_unc.fits'
    if os.path.isfile(inf):
        shutil.copy(inf, out)
    else:
        print("## WARNING: optional {:} not found.".format(inf))  #; cperrs = 1
    
    #-----------------------------------------------------------------------------
    # Finish / clean up ... or not
    # Do not telete temp dirs ... there are other things to do there
    #-----------------------------------------------------------------------------

    ## DEBUG: don't delete TMPDIR
#   print("##### DEBUG ##### Found {:} errors".format(cperrs));   cperrs = 1
    print("## DONE ... {:} - not deleted".format(processTMPDIR))
#
#   if cperrs == 1:
#       print("## Quitting ... check products in {:} - not deleted".format(processTMPDIR))
#       sys.exit(3)
#   else:
#       # clean up:  done in shell script if all products found
#       cleanupCMD = 'rm -rf ' + processTMPDIR
#       os.system(cleanupCMD)
#---------------------------------------------------------------------------------------------------
