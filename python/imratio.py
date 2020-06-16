#!/opt/intel/intelpython3-2019.4-088/intelpython3/bin/python

#-----------------------------------------------------------------------------
# ratio of 2 images: compute im1/1m2 where im2 != 0 and is finite 
# output will have same headers as first image.
# AMo - apr.2020
#-----------------------------------------------------------------------------

import sys, os
import numpy as np
import astropy.io.fits as pyfits

if len(sys.argv) == 4:
    out = sys.argv[3]
elif len(sys.argv) == 3:
    out = "ratio.fits"
else:
    print("[imratio.py] Error: SYNTAX: imratio.py numerator.fits denominator.fits {ratio.fits} ")
    sys.exit(3)

num = sys.argv[1]  # numerator
den = sys.argv[2]  # denominator 

print(">> [imratio.py] compute  {:} / {:} = {:}".format(num, den, out))

#-----------------------------------------------------------------------------

err=0
if not os.path.isfile(num):
    print("[imratio.py] ERROR:  {:} not found".format(num))
    err = 1
if not os.path.isfile(den):
    print("[imratio.py] ERROR:  {:} not found".format(den))
    err = 1

if err == 1:    
    sys.exit(3)

#-----------------------------------------------------------------------------

# prepare copy: im1 to im3 = output
os.system('cp ' + num + ' ' + out)

pnum = pyfits.open(out, mode="update")
pden = pyfits.open(den)
nn = len(pnum)     # num extensions

# do the subraction
for n in range(0, nn):
    if nn == 1: # is SEF
        e = n
    else:       # is MEF
        e = n+1
    # now the real work
    num = pnum[0].data    # numerator
    den = pden[0].data    # denominator
    # do division where where denominator is non-zero and finite
    loc = np.logical_and( den != 0 , np.isfinite(den) )
    num[loc] = num[loc] / den[loc]
    # set to nan where denominator is zero
    loc = np.where(den == 0.0) ; num[loc] = np.nan
    
print("[imratio.py] Done - built {:}".format(out))

pnum.close()
pden.close()
