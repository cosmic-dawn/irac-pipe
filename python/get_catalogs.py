#!/opt/local/bin/python

from supermopex import *
import numpy as np
from astropy.io import ascii
from astropy import units as u
from astropy.table import Table, Column, MaskedColumn,hstack
import re
import os,shutil
from astropy import wcs
from astropy.io import fits
import astropy.units as u
from astropy.coordinates import SkyCoord
from astroquery.irsa import Irsa
from astroquery.gaia import Gaia


#Read the log file
#log = ascii.read(LogFile,format="commented_header",header_start=-1)
log = ascii.read(LogTable,format="ipac")

#get the corners of the data, pad by just over and IRAC FOV to get stars on the edges
RAmax = np.max(log['RA'])+0.1
RAmin = np.min(log['RA'])-0.1
DECmax = np.max(log['DEC'])+0.1
DECmin = np.min(log['DEC'])-0.1

print("Getting catalogs in the data region")
print("RA in range "+str(RAmin) + ' to ' + str(RAmax))
print('DEC in range ' + str(DECmin) + ' to ' + str(DECmax))

#make a polygon to search this area
polygon=[SkyCoord(ra=RAmin, dec=DECmin, unit=(u.deg, u.deg), frame='icrs'),
SkyCoord(ra=RAmax, dec=DECmin, unit=(u.deg, u.deg), frame='icrs'),
SkyCoord(ra=RAmax, dec=DECmax, unit=(u.deg, u.deg), frame='icrs'),
SkyCoord(ra=RAmin, dec=DECmax, unit=(u.deg, u.deg), frame='icrs')]

#make square for GAIA query

RA=(RAmax+RAmin)/2.0
DEC = (DECmax+DECmin)/2.0
GAIAcoord = SkyCoord(ra=RA, dec=DEC, unit=(u.degree, u.degree), frame='icrs')
dRA = (RAmax-RAmin)*u.deg
dDEC = (DECmax-DECmin)*u.deg

#coord = SkyCoord(ra=150.1, dec=2.5, unit=(u.degree, u.degree), frame='icrs')
#width = u.Quantity(0.1, u.deg)
#height = u.Quantity(0.1, u.deg)
#r = Gaia.query_object_async(coordinate=coord, width=width, height=height)
#r.pprint()
#cat = Irsa.query_region(coord, catalog='allwise_p3as_psd', spatial='Box',width=2*u.deg)


#Check if we already have the WISE catalog
if os.path.exists(WiseTable):
    allwise_cat = ascii.read(WiseTable,format="ipac")
    print("Already have the ALLWISE catalog with " + str(len(allwise_cat)) + " sources.")
    print("To get a new one rename or remove " + WiseTable)
else:
    #Get the WISE catalog
    print("Querying the ALLWISE catalog ....")
    print("This will take a while for large areas.")
    Irsa.ROW_LIMIT = 999999999  #set to a very large value so we allways get all sources
    allwise_cat = Irsa.query_region(PIDname, catalog='allwise_p3as_psd', spatial="Polygon", polygon=polygon)

    print("Downloaded ALLWISE catalog with " + str(len(allwise_cat)) + ' sources')

    #Convert Convert allwise magnitudes to ABmag
    allwise_cat['w1ab']=allwise_cat['w1mpro']+2.699
    allwise_cat['w2ab']=allwise_cat['w2mpro']+3.339
    allwise_cat['w3ab']=allwise_cat['w3mpro']+5.174
    allwise_cat['w4ab']=allwise_cat['w4mpro']+6.620

    #Add fluxes in uJy
    allwise_cat['w1']=10**((allwise_cat['w1ab']-23.9)/-2.5)
    allwise_cat['w2']=10**((allwise_cat['w2ab']-23.9)/-2.5)
    allwise_cat['w3']=10**((allwise_cat['w3ab']-23.9)/-2.5)
    allwise_cat['w4']=10**((allwise_cat['w4ab']-23.9)/-2.5)

    #fix the number of decimal points in RA/DEC
    allwise_cat['ra'].format= "{:16.16f}"
    allwise_cat['dec'].format= "{:16.16f}"

    print("Writing ALLWISE catalog, this may take a while for large areas.")
    ascii.write(allwise_cat,WiseTable,format="ipac",overwrite=True)#save the catalog
    
    #fix a bug in the ipac table writer
    fixcmd = "sed -i -e \"s/'null'/ null /g\" " + WiseTable
    os.system(fixcmd)

#Check if we already have the Gaia catalog
if os.path.exists(GaiaTable):
    gaia_cat = ascii.read(GaiaTable,format="ipac")
    print("Already have a Gaia catalog with " + str(len(gaia_cat)) + " sources.")
    print("To get a new one rename or remove " + GaiaTable)
else:
    #Get the GAIA catalog
    #    Irsa.ROW_LIMIT = 999999999  #set to a very large value so we allways get all sources
    #gaia_cat = Irsa.query_region(PIDname, catalog='gaia_source_dr1', spatial="Polygon", polygon=polygon)
    print("Querying the GAIA DR1 catalog ....")
    gaia_cat = Gaia.query_object_async(coordinate=GAIAcoord, width=dRA, height=dDEC)
    
    #Add fluxes in uJy
    gaia_cat['g']=10**((gaia_cat['phot_g_mean_mag']-23.9)/-2.5)
    gaia_cat['bp']=10**((gaia_cat['phot_bp_mean_mag']-23.9)/-2.5)
    gaia_cat['rp']=10**((gaia_cat['phot_rp_mean_mag']-23.9)/-2.5)
    
    #fix the number of decimal points in RA/DEC
    #    gaia_cat['ra'].format= "{:16.16f}"
    #gaia_cat['dec'].format= "{:16.16f}"

    print("Writing GAIA catalog, this may take a while for large areas.")
    ascii.write(gaia_cat,GaiaTable,format="ipac",overwrite=True)#save the catalog
    print("Downloaded GAIA catalog with " + str(len(gaia_cat)) + ' sources')
    #fix a bug in the ipac table writer
    fixcmd = "sed -i -e \"s/'null'/ null /g\" " + GaiaTable
    os.system(fixcmd)

#Check if we already have the 2MASS catalog
if os.path.exists(TwomassTable):
    twomass_cat = ascii.read(TwomassTable,format="ipac")
    print("Already have a 2MASS catalog with " + str(len(twomass_cat)) + " sources.")
    print("To get a new one rename or remove " + TwomassTable)
else:
    #Get the 2MASS catalog
    Irsa.ROW_LIMIT = 999999999  #set to a very large value so we allways get all sources
    print("Querying the 2MASS point source catalog ....")
    twomass_cat = Irsa.query_region(PIDname, catalog='fp_psc', spatial="Polygon", polygon=polygon)
    
    #add AB mags
    twomass_cat['Jab']=twomass_cat['j_m']+0.894
    twomass_cat['Hab']=twomass_cat['h_m']+1.374
    twomass_cat['Kab']=twomass_cat['k_m']+1.840

    #Add fluxes in uJy
    twomass_cat['j']=10**((twomass_cat['Jab']-23.9)/-2.5)
    twomass_cat['h']=10**((twomass_cat['Hab']-23.9)/-2.5)
    twomass_cat['k']=10**((twomass_cat['Kab']-23.9)/-2.5)

    #fix the number of decimal points in RA/DEC
    twomass_cat['ra'].format= "{:16.16f}"
    twomass_cat['dec'].format= "{:16.16f}"

    print("Writing 2MASS catalog, this may take a while for large areas.")
    ascii.write(twomass_cat,TwomassTable,format="ipac",overwrite=True)#save the catalog
    print("Downloaded 2MASS catalog with " + str(len(twomass_cat)) + ' sources')
    #fix a bug in the ipac table writer
    fixcmd = "sed -i -e \"s/'null'/ null /g\" " + TwomassTable
    os.system(fixcmd)

#Merge the catalogs so we only have stars to subtract out
print("Merging GAIA and ALLWISE catalogs")

wiseMatch = SkyCoord(allwise_cat['ra'],allwise_cat['dec'])
GaiaMatch = SkyCoord(gaia_cat['ra'],gaia_cat['dec'])
idx,d2d,d3d=GaiaMatch.match_to_catalog_sky(wiseMatch) #do the match, gaia to wise

#Make a catalog matched to Gaia with wise info
GaiaWise=allwise_cat[:][idx]
GaiaWise = hstack([gaia_cat,GaiaWise],join_type='exact') #do the join
GaiaWise['MatchDistance']=d2d*u.arcsec

#rename some columns
GaiaWise.rename_column('source_id', 'gaia_id')
GaiaWise.rename_column('designation_2', 'wise_id')
GaiaWise.rename_column('ra_1', 'ra')
GaiaWise.rename_column('dec_1', 'dec')
GaiaWise.rename_column('pmra_1', 'pmra')
GaiaWise.rename_column('pmdec_1', 'pmdec')

#make a list of good stars
goodStars = GaiaWise[(GaiaWise['MatchDistance']<(1.0/3600))]['gaia_id','wise_id','ra','dec','ra_error','dec_error','pmra','pmra_error','pmdec','pmdec_error','g','bp','rp','w1','w2','w3','w4','MatchDistance']

print("Writing merged Gaia-WISE catalog")
ascii.write(goodStars,GaiaStarTable,format="ipac",overwrite=True)#save the catalog
#fix a bug in the ipac table writer
fixcmd = "sed -i -e \"s/'null'/ null /g\" " + GaiaStarTable
os.system(fixcmd)

#Merge the catalogs so we only have stars to subtract out
print("Merging 2MASS and ALLWISE catalogs")

wiseMatch = SkyCoord(allwise_cat['ra'],allwise_cat['dec'])
twomassMatch = SkyCoord(twomass_cat['ra'],twomass_cat['dec'])
idx,d2d,d3d=twomassMatch.match_to_catalog_sky(wiseMatch) #do the match, gaia to wise

#Make a catalog matched to Gaia with wise info
twomassWise=allwise_cat[:][idx]
twomassWise = hstack([twomass_cat,twomassWise],join_type='exact') #do the join
twomassWise['MatchDistance']=d2d*u.arcsec

#rename some columns
twomassWise.rename_column('designation_1', 'twomass_id')
twomassWise.rename_column('designation_2', 'wise_id')
twomassWise.rename_column('ra_2', 'ra')
twomassWise.rename_column('dec_2', 'dec')

#make a list of good stars
goodStars = twomassWise[(twomassWise['MatchDistance']<(1.0/3600))]['twomass_id','wise_id','ra','dec','j','h','k','w1','w2','w3','w4','MatchDistance']

print("Writing merged 2MASS-WISE catalog")
ascii.write(goodStars,TwomassStarTable,format="ipac",overwrite=True)#save the catalog
#fix a bug in the ipac table writer
fixcmd = "sed -i -e \"s/'null'/ null /g\" " + TwomassStarTable
os.system(fixcmd)

print('Done!')
