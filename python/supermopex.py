#-----------------------------------------------------------------------------
# supermopex.py @INFO@
#
# This is the template supermopex.py. Items like @XXXX@ are replaced 
# by the pipeline script with local values, and the result is written
# into the local working directory (RootDIR) for use by the python scripts.
#
# This is, in practice, a kind of parameter file; it is read by the python
# scripts via the line 
#    from supermopex import *
# to import the variables in initiates.  
#
# For use outside of the pipeline context, replace the @XXX@ fields with the local
# values; anything beyond  the 'END PARAMETERS' line is probably best left alone.
#
# AMo, 05.apr.19
#-----------------------------------------------------------------------------

import numpy as np
from astropy.time import Time

RootNode   = '@NODE@'                 # node on which to work (not used by python)
RootDIR    = '@ROOTDIR@/'             # root directory
RawDataDir = RootDIR + 'Data/'        # raw data directory
OutputDIR  = RootDIR + 'Products/'    # Products directory (lists, tbls, fits files)

TMPDIR     = RootDIR + 'temp/'        # directory for temporary files
AORoutput  = RootDIR + 'medians/'     # output dir for AOR median images

Nproc      = @NPROC@                  # Number of Processes
Nthred     = @NTHRED@                 # Number of threads for python scripts to use
PIDname    = '@PID@'                  # PID name 
cluster    = '@CLUSTER@'              # cluster name for setting temp files.  Currently only supports candide or none

#--------------------- OTHER PARAMETERS ---------------------

LogFile    = OutputDIR + 'Frames.log'     # ex test.log / .tbl
LogTable   = OutputDIR + 'Frames.tbl'     # the log file containing frame info
RMaskDir   = RawDataDir + 'Rmasks/'       # output dir for RMASK files
AORinfoTable = OutputDIR + 'AORs.tbl'

pythonCMD  = "python"                      # python command

#---------------------- END PARAMETERS ----------------------

# Mosaic tile size in input pixels for parallelizing mosaic making
MosaicTileSize = 1024     # 512
MosaicEdge     = 12       # number of pixels to add to edge of overall mosaic
TileListFile   = OutputDIR + PIDname + '.mosaic_tile_list.tbl'

# Input Star Catalogs
WiseTable = OutputDIR + 'wise.tbl'
GaiaTable = OutputDIR + 'gaia.tbl'
TwomassTable = OutputDIR + '2mass.tbl'
GaiaStarTable = OutputDIR + 'gaia-wise.tbl'
TwomassStarTable = OutputDIR + '2mass-wise.tbl'

#Epoch for astrometry
GaiaEpoch = Time(2015.5,format='decimalyear')  #GAIA DR2 epoch
AstrometryEpoch = Time(2015.5,format='decimalyear') #Desired epoch for astrometry, setting to Gaia since that is what Ultra-Vista is set to

#Column to use for starID
StarIDcol = 'wise_id'

#cuts on catalogs
BrightStar = 16              # clip at brighter than this mag in wise 1,2,3
BrightStarCat = OutputDIR + 'bright_stars.tbl'  # used for star subtraction
StarTable = GaiaStarTable                         # use this for astrometry

# Mosaic configuration files - for building tiles
IRACMosaicGeomConfig = 'mosaic_geom.nl'
IRACOutlierConfig    = 'irac_flag_outliers.nl'
IRACMosaicConfig     = 'irac_mosaic.nl'
# and for "old style" version
#IRACMosaicConfig = 'mosaic_FF.nl'   

# Tile Configuration file - adapted from above
IRACTileGeomConfig = 'tile_geom.nl'
IRACTileConfig     = 'tile_par.nl'

#Catalog of refined star positions and fluxes from mergestars
RefinedStarCat = OutputDIR + 'stars.refined.tbl'

# Table Suffixes
StarInputTableSuffix = 'input_stars.tbl'        # list of gaia stars
BrightStarInputTableSuffix = 'input_bright.tbl' # list of bright stars
StarTableSuffix = 'stars.tbl'                   # list of gaia stars
BrightStarTableSuffix = 'bright.tbl'            # list of bright stars
AstrocheckTableSuffix = 'check.tbl'             # list of stars to check astrometry

# File with Astrometry Corrections
AstrometryFixFile = OutputDIR + 'astrometry-offsets.tbl'
AstrometryCheckFile = OutputDIR + 'astrometry-check.tbl'

#Cut on merge radius for astrometry objects in arcsec, used for clipping in catalog
AstroMergeRad = 5.0

# File Suffixes for IRAC
bcdSuffix =        'bcd'    # Basic Calibrated Data
UncSuffix =        'bunc'   # corrected uncertanty data
corDataSuffix =    'cbcd'   # corrected basic calibrated data
corUncSuffix =     'cbunc'  # corrected uncertanty data
maskSuffix =       'bimsk'  # pixel masks
ffSuffix =         'ffcbcd' # First Frame corrected files
starsubSuffix =    'stbcd'  # Star subtracted and corrected image
starMaskSuffix =   'stmsk'  # Star subtracted and corrected image
SubtractedSuffix = 'sub'    # Star subtracted and corrected image
ScaledUncSuffix =  'sbunc'  # corrected uncertanty data
rmaskSuffix =      'rmask'  # Rmask suffix

# File Suffixes for MIPS
MipsMaskSuffix =   'bmsk' # corrected uncertanty data
flatFeildSuffix =  'fbcd' # corrected uncertanty data

#File suffix lists
IRACsuffixList = [bcdSuffix,UncSuffix,corDataSuffix,corUncSuffix,ffSuffix,starsubSuffix,starMaskSuffix,SubtractedSuffix,ScaledUncSuffix,rmaskSuffix]
MIPSsuffixList = [bcdSuffix,UncSuffix,MipsMaskSuffix,flatFeildSuffix]

#first frame delay files
FrameDelayFile = './cal/frame-delay.txt'

#Flat data
#0 = warm, 1 = cryo
flatFiles = np.array([['./cal/flat.1.fits','./cal/flat.2.fits','',''],
                      ['','','','']])

#Pixel masks
IRACPixelMasks = ['./cal/chan1_ormask_bcd.fits','./cal/chan2_ormask_bcd.fits','./cal/chan3_ormask_bcd.fits','./cal/chan4_ormask_bcd.fits']

#Date Warm Mission Started
WarmMJD = 54967

#set up PRF info
#0 = warm, 1 = cryo
PRF = np.array([['./cal/I1_hdr_warm_psf.fits','./cal/I2_hdr_warm_psf.fits','',''],
                ['./cal/IRAC.1.EXTPRF.5X.070704.fits','./cal/IRAC.2.EXTPRF.5X.070704.fits','./cal/IRAC.3.EXTPRF.5X.070704.fits','./cal/IRAC.4.EXTPRF.5X.070704.fits']])

PRFmap = np.array([['./cal/ch1_prfmap_warm.tbl','./cal/ch2_prfmap_warm.tbl','',''],
                  ['./cal/ch1_prfmap.tbl','./cal/ch2_prfmap.tbl','./cal/ch3_prfmap.tbl','./cal/ch4_prfmap.tbl']])

PRFghostDx = np.array([[-7.8,8.6,0,0],
                       [-7.8,8,0,0]])
PRFghostDy = np.array([[7,7,0,0],
                       [7,6.8,0,0]])
PRFghostR  = np.array([[9,8,0,0],
                       [9,8,0,0]])

#Make a set of names for repeated observations for median subtraction.
repeats=["a","b","c","d","e","f","g","h","i","j","l","m","n","o","p","q","r","s","t","u","v","w","x","y","z"]

#clip setting for making median background
ClipSigmaPos=3.0
ClipSigmaNeg=5.0

#number of dilations around objects
Ndilation = 2

#Use median or average image for background subtraction
#BackgroundType = "median"
BackgroundType = "average"

#Grab these key words from the BCD headers and record them in the log files
HeaderItems=("INSTRUME","CHNLNUM","AORKEY","DCEID","DCENUM","AOT_TYPE","HDRMODE","PROGID","MJD_OBS","EXPTIME","OBJECT","CRVAL1","CRVAL2","PA","FLUXCONV","GAIN","ZODY_EST","ISM_EST","FOVID","EXPID","FRAMEDLY")

#Give the header key words these names in the log files
LogItems=("Filename","Instrument","Channel","AOR","DCE","FrameNumber","ObsType","HDR","PID","MJD","ExpTime","Object","RA","DEC","PA","FluxConv","Gain","Zody_Bkg_Est","ISM_Bkg_Est","FOVID","ExposureID","FrameDelay")

# Wise magnitude offsets for checking in star merging
WISEchannel=["w1","w2","w2","w2"]
WISEratio=[0.8924,1.075,0.7832,0.4884]
WISEratioCut=5  # cut stars with ratios bellow and +1 above this
