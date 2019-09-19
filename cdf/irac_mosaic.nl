compute_uncertainties_internally = 0
have_uncertainties = 1
run_fiducial_image_frame = 0
run_mosaic_geom = 0
run_medfilter = 0
run_detect_radhit = 0
run_mosaic_interp = 1
run_detect_outlier = 0
run_mosaic_proj = 0
run_mosaic_covg = 0
run_mosaic_dual_outlier = 0
run_level = 0
run_mosaic_outlier = 0
run_mosaic_box_outlier = 0
run_mosaic_rmask = 0
run_mosaic_reinterp = 0
run_fix_coverage = 0
run_mosaic_coadder = 1

#define output mosaics
run_absolute_minimum_mosaic = 0
run_mosaic_combiner = 1
run_mosaic_medfilter = 0
#run_median_mosaic = 1
create_rmask_mosaic = 0
#create_unc_mosaic = 1
#create_std_mosaic = 1
create_dual_outlier_mosaic = 0
create_outlier_mosaic = 0
make_array_corr_files = 0
make_array_corr_mosaic = 0

sigma_weighted_coadd = 0
keep_coadded_tiles = 1
overwrite_dmask = 0
delete_intermediate_files = 0


###### Multi-processing Parameters ######
do_multiprocess = 'manual'
# this should be the same as in make_tile.sh
ncpu_multiprocess = 24



USE_REFINED_POINTING = 0
MOSAIC_PIXEL_SIZE_X = -1.6667E-4
MOSAIC_PIXEL_SIZE_Y = 1.6667E-4

USE_DUAL_OUTLIER_FOR_RMASK = 1
USE_BOX_OUTLIER_FOR_RMASK = 1
USE_OUTLIER_FOR_RMASK = 1
DCE_Status_Mask_Radhit_Bit = 9
RMask_Fatal_BitPattern = 15
DCE_Status_Mask_Fatal_BitPattern = 32767
IMask_Fatal_BitPattern = 32767
PMask_Fatal_BitPattern = 32767

RMASK_MOSAIC_DIR = RmaskMosaic-mosaic
COMBINER_DIR = Combine-mosaic
DUAL_OUTLIER_DIR = DualOutlier-mosaic
REINTERP_DIR = Reinterp-mosaic
OUTLIER_DIR = Outlier-mosaic
INTERP_DIR = Interp-mosaic
MEDFILTER_DIR = Medfilter-mosaic
RMASK_DIR = Rmask-mosaic
SIGMA_DIR = Sigma-mosaic
COADDER_DIR = Coadd-mosaic
DETECT_DIR = Detect-mosaic
BOX_OUTLIER_DIR = BoxOutlier-mosaic


&SNESTIMATORIN
Read_Noise = 90.0,
Confusion_Sigma = 0.0,
Gain = 1290.0,
&END

&FIDUCIALIMAGEFRAMEIN
CROTA2 = 0.0,
Coordinate_System = 'J2000',
Projection_Type = 'TAN',
Edge_Padding = 0,
&END

&MOSAICGEOM
&END

&MEDFILTER
Window_Y = 45,
N_Outliers_Per_Window = 50,
Sbkg_Filt_Size_for_Med = 3,
Use_Sbkg_for_Med = 1,
Window_X = 45,
&END

&DETECT_RADHIT
Detection_Max_Area = 3,
Segmentation_Threshold = 3.0,
Radhit_Threshold = 6.0,
&END

&MOSAICINTIN
GRID_RATIO = 2,
DRIZ_FAC = 0.5,
INTERP_METHOD = 2,
ALPHA = -0.5,
FINERES = 0.0,
&END

&DETECT
Detection_Min_Area = 0,
Detection_Threshold = 4.0,
Detection_Max_Area = 100,
Threshold_Type = 'simple',
&END

&MOSAICPROJIN
&END

&MOSAICCOVGIN
TILEMAX_Y = 500,
TILEMAX_X = 500,
&END

&MOSAICDUALOUTLIERIN
TILE_YSIZ = 500,
MAX_OUTL_FRAC = 0.5,
MAX_OUTL_IMAGE = 1,
TILE_XSIZ = 500,
&END

&LEVEL
Threshold_Ratio = 0.5,
&END

&MOSAICOUTLIERIN
MIN_PIX_NUM = 3,
TILE_YSIZ = 500,
TOP_THRESHOLD = 3.0,
BOTTOM_THRESHOLD = 3.0,
THRESH_OPTION = 1,
TILE_XSIZ = 500,
&END

&MOSAICBOXOUTLIERIN
BOX_Y = 3,
TILE_YSIZ = 500,
BOX_X = 3,
TILE_XSIZ = 500,
BOX_MEDIAN_BIAS = 1,
&END

&MOSAICRMASKIN
BOX_MIN_COVERAGE = 1.0,
BOX_BOTTOM_THRESHOLD = 2.0,
BOX_TOP_THRESHOLD = 3.0,
REFINE_OUTLIER_THRESH = 1,
REFINE_OUTLIER = 0,
RM_THRESH = 0.5,
MIN_COVERAGE = 3,
MAX_COVERAGE = 100,
TOP_THRESHOLD = 3.0,
BOTTOM_THRESHOLD = 3.0,
&END

&MOSAICREINTIN
&END

&FIX_COVERAGE
Min_Block_Coverage = 0.83,
Min_Single_Coverage = 0.95,
&END

&MOSAICCOADDIN
USE_INT_TIME_KWD = 1,
INTEG_TIME_KWD = 'EXPTIME',
TILEMAX_Y = 500,
TILEMAX_X = 500,
&END

&MOSAICCOMBINER
&END

&MOSAIC_MEDFILTER
Window_Y = 45,
N_Outliers_Per_Window = 500,
Sbkg_Filt_Size_for_Med = 3,
Use_Sbkg_for_Med = 1,
Window_X = 45,
&END

&CREATERMASKMOSAIC
&END

#END


