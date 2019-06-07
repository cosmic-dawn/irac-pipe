
###### Define which modules to run ######

run_MOSAIC_POINTSOURCEIMAGE = 1


create_residual_mosaic = 1
create_pointsource_mosaic = 0

###### Input file lists ######

MOSAIC_FILE_NAME =
EXTRACTION_TABLE = 

FIF_FILE_NAME = 

###### Output Dir and Files ######

OUTPUT_DIR = 

###### Mask Bit Parameter ######


###### Other Parameters ######

delete_intermediate_files = 0
MOSAIC_DIR = Mosaic
MOSAIC_PRF_file_name = 
USE_REFINED_POINTING = 0


###### Modules ######

&MOSAIC_POINTSOURCEIMAGE
PRF_ResampleX_Factor = 5,
PRF_ResampleY_Factor = 5,
Flux_Column_Name = flux,
X_Column_Name = ra,
Y_Column_Name = dec,
Input_RA_Dec = 1,
Normalization_Radius = 100,
&END

#END


