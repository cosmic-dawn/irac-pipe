
#!/bin/sh
# misc. commands and other notes
#-----------------------------------------------------------------------------
# build list of dirs and list of files
cd $WRK/{datadir}
ls -d r*/ch?/bcd > list_dirs
find . -name *.fits -print | grep -v ffcbcd > list_files
#wc $WRK/list_dirs ; wc $WRK/list_files
##     3249 list_dirs
##  1932751 list_files

# given FileCount_xxx.txt, get number of warm AORs
grep ' 0    0 ' FileCount_NEP-new.txt | wc
for f in FileCount*.txt; do echo " $(wc -l $f)  $(cat $f | grep  ' 0    0 ' | wc -l) " ; done

# check the raw data files; for each root name, expect to find 5 files
cd $WRK/COSMOS_ORIG
types="_bcd _bimsk _bunc _cbcd _cbunc"
for e in $types; do echo "Num $e files: $(grep $e list_files > list$e )"; done
for e in $types; do echo "Num $e files: $(grep $e list_files | cut -d\_ -f2-6 | sort > list$e )"; done
# ==> list_bismk is short ...
comm -23 list_bcd list_bimsk  > list_missing
cut -d\_ -f2 list_missing | sort -u
# ==> 3 incomplete AORs
mkdir incomplete; mv r15536896 r15543808 r15548160 incomplete

# given list_files, get number of frames in each AOR
chs="1 2 3 4"
for f in $(head list_dirs); do for c in $chs; do echo "$f: $(ls $f/ch)"; done
for f in $(head list_dirs); do echo "$f: $(ls $f/ch?/bcd/*_bds.fits | wc)"; done

# to save products:
sdir=run_$(date "+%y-%h-%d") ; echo $sdir
mkdir $sdir; mv *.sh *.py *.out *.qall $odir $sdir

# to clean up:
rm *.sh *.py *.out *.qall
rm -rf temp $odir __pycache__

#---------------------------------------------------------------------------
# get coords of first frame in ch1 of each AOR
dfits r*/ch1/bcd/*0000_0000_1_bcd.fits | fitsort crval1 crval2 > ~/RaDec_.dat

# does every dir have a 0000_0000*_bcd files??
for f in r15*/ch?/bcd; do if [ ! -e $f/SP*0000_0000_*_bcd.fits ]; then echo "Not in $f"; ls -1 $f/*0000_?_bcd.fits; fi; done
for c in 1 2 3 4; do \
for f in r*/ch$c/bcd; do if [ ! -e $f/SP*_0000_0000_*_bcd.fits ]; then echo "Not in $f";  fi; done; done

#-----------------------------------------------------------------------------
tar cvzf scripts_v15x.tgz *.?[h,y]

# Coordinates table from Frames_xx.tbl:
grep SPITZER Products/Frames_cosmctr.tbl | tr -s ' ' | cut -d\  -f2,14,15 | cut -d\/ -f8 |\
  awk '{printf "%-33s %15.10f %15.10f \n", $1,$2,$3 }' | sort -k2 -u > Coords.tbl


awk '{if ($2 > 150.0 && $2 < 150.2 && $3 > 2.17 && $3 < 2.56) print $0 }' Coords.tbl |cut -d\/ -f2 | sort > list
cut -d\_ -f3 list | sort -u |awk '{printf "r%s\n", $0}'

#-----------------------------------------------------------------------------
grep -e Pipeline -e ing\ time xx.out | cut -d\  -f3-9 | awk '{printf "%-33s",$0; getline; print $0}'

grep "^/softs/mopex/18.5.0/bin/" build_mosaic_ch1.out | cut -c1-59 | uniq
/softs/mopex/18.5.0/bin/mosaic_covg  -n cdf/mosaic_FF.nl -o
/softs/mopex/18.5.0/bin/mosaic_dual_outlier  -n cdf/mosaic_
/softs/mopex/18.5.0/bin/mosaic_outlier  -n cdf/mosaic_FF.nl
/softs/mopex/18.5.0/bin/fix_coverage  -n cdf/mosaic_FF.nl -
/softs/mopex/18.5.0/bin/mosaic_coadd  -n cdf/mosaic_FF.nl -
/softs/mopex/18.5.0/bin/mosaic_combine  -g /n09data/XMM/tem
/softs/mopex/18.5.0/bin/mosaic_outlier  -n cdf/mosaic_FF.nl
/softs/mopex/18.5.0/bin/mosaic_combine  -g /n09data/XMM/tem

#-----------------------------------------------------------------------------
# see what mosaicing steps have been done:
#-----------------------------------------------------------------------------
file=build_mosaic_ch3.out
grep -e Pipeline -e "^/softs/mopex/18.5.0/bin/" $file | tr -s \  | cut -d\  -f1-3 | uniq

##### BEGIN #####
Pipeline Module MOSAIC_INT Version
Pipeline Module MOSAIC_PROJ Version
/softs/mopex/18.5.0/bin/mosaic_covg  -n cdf/mosaic_FF.nl
Pipeline Module MOSAIC_COVG Version
/softs/mopex/18.5.0/bin/mosaic_dual_outlier  -n cdf/mosaic_FF.nl
Pipeline Module MOSAIC_DUAL_OUTLIER Version
/softs/mopex/18.5.0/bin/mosaic_outlier  -n cdf/mosaic_FF.nl
Pipeline Module MOSAIC_OUTLIER Version
/softs/mopex/18.5.0/bin/mosaic_outlier  -n cdf/mosaic_FF.nl
Pipeline Module MOSAIC_OUTLIER Version

##### FINISH #####
Pipeline Module MOSAIC_RMASK Version
Pipeline Module MOSAIC_INT Version
/softs/mopex/18.5.0/bin/fix_coverage  -n cdf/mosaic_FF.nl
/softs/mopex/18.5.0/bin/mosaic_coadd  -n cdf/mosaic_FF.nl
Pipeline Module MOSAIC_COADD Version
/softs/mopex/18.5.0/bin/mosaic_combine  -g /n08data/HDFN/temp/1/Coadd-mosaic/coadd_Tiles_List
Pipeline Module MOSAIC_COMBINE Version
/softs/mopex/18.5.0/bin/mosaic_combine  -g /n08data/HDFN/temp/1/Coadd-mosaic/coadd_Sigma_Tiles_List
Pipeline Module MOSAIC_COMBINE Version
/softs/mopex/18.5.0/bin/mosaic_combine  -g /n08data/HDFN/temp/1/Coadd-mosaic/coadd_Std_Tiles_List
Pipeline Module MOSAIC_COMBINE Version
/softs/mopex/18.5.0/bin/mosaic_combine  -g /n08data/HDFN/temp/1/Coadd-mosaic/coadd_Cov_Tiles_List
Pipeline Module MOSAIC_COMBINE Version
/softs/mopex/18.5.0/bin/mosaic_outlier  -n cdf/mosaic_FF.nl
Pipeline Module MOSAIC_OUTLIER Version
/softs/mopex/18.5.0/bin/mosaic_combine  -g /n08data/HDFN/temp/1/Coadd-mosaic/coadd_median_tiles.tbl
Pipeline Module MOSAIC_COMBINE Version
/softs/mopex/18.5.0/bin/mosaic_combine  -g /n08data/HDFN/temp/1/Coadd-mosaic/coadd_coadd_Tiles_Unc_List
Pipeline Module MOSAIC_COMBINE Version


grep -e Pipeline -e "^/softs/mop" ~/j1 | cut -d\  -f1-4 | uniq

#-----------------------------------------------------------------------------
# find AORs near high cov. region for ch1: 10.00.25 +02.23 ==> 150.10 +02.38
# find AORs near high cov. region for ch3: 10.00.18 +02.37 ==> 150.08 +02.62

grep ch3 Coords_COSMOS.tbl | awk '{if ($2 > 150.0 && $2 < 150.2) print $0 } ' | sort -nk3 |awk '{if ($3 > 2.5 && $3 < 2.6) print $0 } ' |cut -d\/ -f2 | sort > ch3list
awk '{if ($2 > 150.0 && $2 < 150.2) print $0 } ' Coords_COSMOS.tbl | sort -nk3 |awk '{if ($3 > 2.5 && $3 < 2.7) print $0 } ' |cut -d\/ -f2 | sort -u > ch3list

ds9w Cosmos_19-01/cosmos.irac.1.mosaic.fits Cosmos_splash/all.irac.1.mosaic.fits Cosmos_19-01/cosmos.irac.1.mosaic_cov.fits Cosmos_splash/all.irac.1.mosaic_cov.fits

# count HDR frames in each channel
tab=Frames.tbl
for c in 1 2 3 4; do echo " ch$c: $(grep ch$c $tab | grep True|wc -l)  $(grep ch$c $tab | grep False|wc -l)"; done

# list HDR frames from Frames.tbl:
#grepi 7379456 Products/Frames_NEP.tbl | cut -c2-79,138-145
cut -c2-79,138-145 Frames_NEP.tbl > HDR.tbl
grep True HDR.tbl | wc ; grep False HDR.tbl | wc

for c in 1 2 3 4; do echo "ch$c $(grep True HDR.tbl | grep ch$c | wc -l )  $(grep False HDR.tbl | grep ch$c | wc -l) "; done

#-----------------------------------------------------------------------------
# reshape errors ...
#-----------------------------------------------------------------------------

n08: 23:06> Traceback (most recent call last):
  File "make_medians.py", line 128, in make_median_image
    imageData     = imageData.reshape([Nrepeats,int(len(files)/Nrepeats),256,256])
  File "/opt/intel/intelpython3/lib/python3.6/site-packages/numpy/ma/core.py", line 4587, in reshape
    result = self._data.reshape(*s, **kwargs).view(type(self))
ValueError: cannot reshape array of size 3342336 into shape (2,25,256,256)

n08: 23:14> tail serial.log 
### BEGIN JobNo 5632: AOR 65762304 ch2 with 51 valid frames

awk '{if ($3 != $4) print $0}' countFiles.dat | tr -d r | cut -d\  -f2,8 

# aors giving rehape error:
65762304  cannot reshape array of size 3342336 into shape (2,25,256,256)
62854656  cannot reshape array of size 327680 into shape (2,2,256,256)
62865152  idem  (Nframes = 5)
62849792  idem


#-----------------------------------------------------------------------------
# count retained and rejected AORs and frames
# cols of retained.dat are # 3,4,5,6
for c in 3 4 5 6; do cat retained.dat | tr -s \  | cut -d\  -f $c | grep -v ^0 | \
	echo " Ch$(($c-2))  $(awk '{tot+=$1; nl+=1}END{print nl,tot}')" | \
	awk '{printf " >> %3s retained AORs: %4i;  files: %7i\n", $1,$2,$3}' ; done

#-----------------------------------------------------------------------------
# look for unused nodes to 
avail=$(cnodes | grep free | grep -v \# | tr -d \[\] | tr -s ' ' |sort -nk 6 -r | cut -d\  -f2 | head -4)

n09: 16:07> for f in *sex.log; do echo "$f $(tail -14 $f | grep sextracted | strings | tail -1)"; done
cosmos155.irac.1.mosaic_sex.log [1A      Objects: detected 830      / sextracted 830             
cosmos155.irac.2.mosaic_sex.log [1A      Objects: detected 393      / sextracted 392             
cosmos155.irac.3.mosaic_sex.log [1A      Objects: detected 101      / sextracted 100             
cosmos155.irac.4.mosaic_sex.log [1A      Objects: detected 446      / sextracted 443             
n09: 16:07> for f in *scamp.log; do echo "$f $(grep detections\ load $f)"; done
cosmos155.irac.1.mosaic_scamp.log ----- 131 detections loaded
cosmos155.irac.2.mosaic_scamp.log ----- 10 detections loaded
cosmos155.irac.3.mosaic_scamp.log ----- 19 detections loaded
cosmos155.irac.4.mosaic_scamp.log ----- 156 detections loaded
