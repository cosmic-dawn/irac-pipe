#------------------------------------------------
# nans.py
#------------------------------------------------
# replace 0.000 with nan in fits (SEF) image
#------------------------------------------------

import sys, os  #, re, math
import numpy as np
import astropy.io.fits as pyfits

ima  = sys.argv[1]
pima = pyfits.open(ima, mode="update")
n_ext = len(pima)
#print("Replace 0.0 with NaN in {} ".format(ima))

if n_ext == 1:
    data = pima[0].data
    data[data==0] = np.nan
    nn = np.isnan(pima[0].data).sum()
else:
    print("MEF handling Not implemented")

pima.close()
print("Replaced {} 0's with NaN in {} ".format(nn,ima))
