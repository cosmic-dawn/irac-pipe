###### Define which modules to run ######

compute_uncertainties_internally = 0
have_uncertainties = 1
run_detect_medfilter = 0
run_gaussnoise = 0
run_extract_medfilter = 0
run_sourcestimate = 1
run_aperture = 0
run_select = 0


###### Input file lists ######

INPUT_FILE_NAME = 
SIGMA_FILE_NAME = 
DCE_STATUS_MASK = 
PMASK_FILE_NAME = 
PRF_file_name = 
COVERAGE_MAP = 
INPUT_USER_LIST =


###### Output Dir and Files ######

OUTPUT_DIR = 

###### Mask Bit Parameter ######

DCE_Status_Mask_Fatal_BitPattern = 32732
PMask_Fatal_BitPattern = 32732
RMask_Fatal_BitPattern = 32732


###### Global Parameters ######


###### Other Parameters ######

use_background_subtracted_image_for_aperture = 0
use_background_subtracted_image_for_fitting = 0
use_data_unc_for_fitted_SNR = 1
use_extract_table_for_aperture = 1
delete_intermediate_files = 0
use_refined_pointing = 0
use_input_list_type = 1
select_detect_columns = 
select_detect_conditions = 
aponly_fixed = 0
PRFMAP_FILE_NAME = 
IMAGELIST_FILE_NAME = ImageList.txt
SIGMALIST_FILE_NAME = SigmaList.txt
RMASK_FILE_NAME = 


###### Modules ######

&SNESTIMATORIN
Gain = 1290.0,
Read_Noise = 90.0,
Confusion_Sigma = 0.0,
&END

&DETECT_MEDFILTER
Window_X = 25,
Window_Y = 25,
N_Outliers_Per_Window = 100,
Min_Good_Pixels_In_Window = 9,
Min_GoodNeighbors_Number = 4,
Max_Bad_Pixels_OutputImage = 1.0,
Use_Sbkg_for_Med = 1,
Sbkg_Filt_Size_for_Med = 1,
&END

&GAUSSNOISE
Window_X = 25,
Window_Y = 25,
N_Outliers_Per_Window = 100,
Min_Good_Pixels_In_Window = 9,
Min_GoodNeighbors_Number = 4,
Max_BadPixels_OutputImage = 1.0,
&END

&EXTRACT_MEDFILTER
Window_X = 45,
Window_Y = 45,
N_Outliers_Per_Window = 500,
Min_Good_Pixels_In_Window = 9,
Min_GoodNeighbors_Number = 4,
Max_Bad_Pixels_OutputImage = 1.0,
Use_Sbkg_for_Med = 1,
Sbkg_Filt_Size_for_Med = 1,
&END

&SOURCESTIMATE
InputType = 'image_list',
Fitting_Area_X = 6,
Fitting_Area_Y = 6,
Max_Number_PS = 1,
Chi_Threshold = 6.0,
N_Edge = 4,
Max_N_Iteration = 100000,
Max_N_Success_Iteration = 100,
MinimizeFtol = 1.0E-4,
MinimizeFtolSuccess = 1.0E-5,
DitherPixelFraction = 0.1,
DitherFluxFraction = 0.8,
DeblendDitherPixelFraction = 1.0,
Background_Fit = 1,
Random_Fit = 0,
Chi2_Improvement = 1.0,
PRF_ResampleX_Factor = 100,
PRF_ResampleY_Factor = 100,
Normalization_Radius = 1000.0,
MaxShift_X = 5.0,
MaxShift_Y = 5.0,
Angular_Distance = 6.0,
Use_Photerr_for_SNR = 1,
Gain_for_SNR = 1.0,
&END

&APERTURE
N_Apertures = 3,
Aperture_Radius_1 = 2.0,
Aperture_Radius_2 = 3.0,
Aperture_Radius_3 = 5.0,
Aperture_Radius_4 = 7.0,
Aperture_Radius_5 = 7.0,
Use_Annulus = 1,
Min_Number_Pixels = 10,
Annulus_Compute_Type = 'mode',
Inner_Radius = 12.0,
Outer_Radius = 20.0,
X_Column_Name = x ,
Y_Column_Name = y,
HighPrecision = 1,
&END

&SELECT
&END

#END


