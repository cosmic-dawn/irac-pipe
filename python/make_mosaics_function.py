#!/opt/local/bin/python

import sys

import numpy as np
from astropy.io import ascii
from astropy.table import Table, Column, MaskedColumn

from supermopex import *
from spitzer_pipeline_functions import *
from optparse import OptionParser

#parse the arguments
usagestring ='%prog Job_Number'
parser = OptionParser()
parser = OptionParser(usage=usagestring)
(options, args) = parser.parse_args()

#fail if there aren't enough arguments
if len(args) < 1:
    parser.error("Incorrect number of arguments.")

#read job number
Ch = int(args[0])

build_mosaic(Ch)


