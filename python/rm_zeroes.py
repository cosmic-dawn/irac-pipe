#!/opt/intel/intelpython3-2019.4-088/intelpython3/bin/python

#------------------------------------------------
# Replace 0's by nan's in file
# AMo - Mar.2020
#------------------------------------------------

import sys
import numpy as np
import astropy.io.fits as fits

if len(sys.argv) == 2:  
    fima = sys.argv[1]
else:
    print("SYNTAX: rm_zeroes.py file")
    sys.exit()

#-----------------------------------------------------------------------------

ima  = fits.open(fima, mode='update')
data = ima[0].data
hdr  = ima[0].header
shape = data.shape

data = data.flatten()
loc = np.where(data == 0.0)      ; data[loc] = np.nan
loc = np.where(data == -1e+30)   ; data[loc] = np.nan
loc = np.where(data == +1e+30)   ; data[loc] = np.nan

#print(" --  max = {:0.2f}".format(hmax))
data = np.reshape(data, shape)

hdr['history'] = 'Zeros replaced by NaNs; AMo apr.2020'
fits.writeto(fima, data, hdr, overwrite=True)
ima.close()   #this should save to updated data, but it does not
 
print("[rm_zeroes]  Done {:}".format(fima))

sys.exit()
