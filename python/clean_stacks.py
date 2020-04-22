#!/opt/intel/intelpython3-2019.4-088/intelpython3/bin/python
#-----------------------------------------------------------------------------
# syntzx:  clean_stacks.py chan
# rm zeros from cover and exptm stacks, replacing them with nans;
# zeros to remove are where image is nan
#-----------------------------------------------------------------------------

import sys, os
import numpy as np
import astropy.io.fits as fits

if len(sys.argv) == 2:
    ch = sys.argv[1]
else:
    print("## ERROR: SYNTAX: clean_stacks.py chan# ")
    sys.exit(3)
#-----------------------------------------------------------------------------

def cleanit(fname):
    if os.path.exists(fname):
        ima = fits.open(fname, mode="update"); ima[0].data[loc] = np.nan
        print(">> - {:} cleaned of spurious zeroes".format(fname))
        ima.close()
    else:
        print("ERROR: {:} not found".format(fname))


field = os.environ['WRK']
field = field.split('/')[2]   #; print(field); sys.exit()

# reference image
fname = "{:}.irac.{:}.stack_image.fits".format(field,ch)
if os.path.exists(fname):
    ref = fits.open(fname) #; print(np.size(sgm))
    loc = np.isnan(ref[0].data)
    print(">> Reference file {:}: found {:} NaNs".format(fname, np.size(loc)))
else:
    print("ERROR: {:} not found".format(fname))
    sys.exit(20)

ref.close()

cleanit("{:}.irac.{:}.stack_cover.fits".format(field,ch))
cleanit("{:}.irac.{:}.stack_covtm.fits".format(field,ch))

sys.exit(0)
#-----------------------------------------------------------------------------
