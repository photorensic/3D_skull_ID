# -*- coding: utf-8 -*-
"""
@author: Schoeb-ID, adapted from D. Neuhaus

# =========================
# REQUIREMENTS / USAGE
# =========================
# - Set "base_in_dir" to the folder containing the AM/PM skull segmentation folders.
# - Each AM/PM folder must contain a NIfTI file named "skull.nii.gz".
# - Folder names must contain "_AM" or "_PM" (e.g. "123_AM", "123_PM").
# - Set "base_out_dir" to the desired output directory.
# - The script creates two subfolders automatically:
#     01_Cropped     -> cropped skull masks
#     02_Registered  -> AM-to-PM registered images and FLIRT matrices
# - The skull masks are cropped with a 50-voxel margin.
# - Each AM image is registered to each available PM image using FSL FLIRT.
# - FSL/FLIRT must be installed and available in the system PATH.
# - Required Python packages: nibabel, numpy.
"""

# %% Packages
import nibabel as nib
import numpy as np
import SimpleITK as sitk
import os
# import shutil
import subprocess


# %% Functions
# def clear_directory_of_files(directory):
#     for filename in os.listdir(directory):
#         file_path = os.path.join(directory, filename)
#         try:
#             if os.path.isfile(file_path) or os.path.islink(file_path):
#                 os.unlink(file_path)
#             elif os.path.isdir(file_path):  # If you decide to also remove directories, uncomment the following line
#                 # shutil.rmtree(file_path)
#                 pass  # Currently, we're just passing if it's a directory
#         except Exception as e:
#             print(f'Failed to delete {file_path}. Reason: {e}')



def crop_nifti_file_with_margin(input_filepath, output_filepath, margin):
    """
    Crop the NIfTI file around the non-zero region with an additional margin.

    Parameters:
    - input_filepath: Path to the input NIfTI file.
    - output_filepath: Path where the cropped NIfTI file will be saved.
    - margin: Number of pixels to add as a margin around the bounding box (default is 10).
    """
    # Load the NIfTI file
    nifti_img = nib.load(input_filepath)
    img_data = nifti_img.get_fdata()

    # Find the bounding box of the non-zero region
    nonzero = np.nonzero(img_data)
    min_dims = [np.max([0, np.min(nonzero[i]) - margin]) for i in range(3)]  # Ensure min_dims are not negative
    max_dims = [np.min([img_data.shape[i] - 1, np.max(nonzero[i]) + margin]) for i in range(3)]  # Ensure max_dims do not exceed image dimensions

    # Crop the image data
    cropped_img_data = img_data[min_dims[0]:max_dims[0]+1, min_dims[1]:max_dims[1]+1, min_dims[2]:max_dims[2]+1]

    # Create a new NIfTI image from the cropped data
    cropped_nifti_img = nib.Nifti1Image(cropped_img_data, affine=nifti_img.affine)
        
    # Save the cropped image
    nib.save(cropped_nifti_img, output_filepath)
    
    print("Cropping completed. The cropped image is saved as:", output_filepath)




def run_flirt(input_image, reference_image, path_out_img, path_out_aff_mat, additional_options=None):
    """
    Runs FSL FLIRT on the specified input and reference images.
    
    Parameters:
    - input_image: Path to the input image.
    - reference_image: Path to the reference image.
    - path_out_img: Path to save the registered output image.
    - path_out_aff_mat: Path to save the output affine matrix.
    - additional_options: A list of additional command-line options for FLIRT.
    """
    
    # Set the FSLOUTPUTTYPE environment variable
    os.environ['FSLOUTPUTTYPE'] = 'NIFTI_GZ'
    
    # Base FLIRT command
    flirt_command = [
        'flirt',
        '-in', input_image,
        '-ref', reference_image,
        '-out', path_out_img,
        '-omat', path_out_aff_mat,
    ]
    
    # Append any additional options
    if additional_options:
        flirt_command.extend(additional_options)
    
    # Execute the FLIRT command
    result = subprocess.run(flirt_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Check the result
    if result.returncode == 0:
        print("A successful FLIRT! The registered image is saved as:", path_out_img)
        return True
    else:
        print(f"FLIRT registration failed for {input_image}")
        print(result.stderr.decode())
        return False




def load_nifti_file_as_binary_array(filepath):
    # Load the NIfTI file
    nifti_img = nib.load(filepath)
    img_data = nifti_img.get_fdata()
    
    binary_array = np.where(img_data > 0, 1, 0)

    
    return binary_array


def process_antemortem_files(anatomy, base_in_dir, crop_out_dir, reg_out_dir):
    

    def extract_numeric_part(filename):
        """
        Extracts the leading numeric part of a filename for sorting purposes.
        """
        return filename.split('_')[0]


    # List all files in the directory
    all_dirs = [f for f in os.listdir(base_in_dir) if os.path.isdir(os.path.join(base_in_dir, f))]
    
    # Sort directories numerically before filtering
    all_dirs_sorted = sorted(all_dirs, key=extract_numeric_part)

    # Filter PM and AM files
    pm_dirs = [f for f in all_dirs_sorted if "_PM" in f]
    am_dirs = [f for f in all_dirs_sorted if "_AM" in f]
    
    First_run = True

    for pm_dir in pm_dirs:
        pm_short_name = pm_dir.split("_")[0] + "_PM"
        pm_file_path = os.path.join(base_in_dir, pm_dir, f"{anatomy}.nii.gz")
        if os.path.exists(pm_file_path):  
            print(f"Processing {pm_short_name} -----------------------------------")
            # Clear the directory with registered files before new PM processing
            # clear_directory_of_files(path_OutDir_reg)
            
            pm_cropped_out = os.path.join(crop_out_dir, f"{pm_short_name}_{anatomy}_cro.nii.gz")
            pm_image_cropped = crop_nifti_file_with_margin(pm_file_path, pm_cropped_out, margin=50)


           
            
            for am_dir in am_dirs:
                am_short_name = am_dir.split("_")[0] + "_AM"
                am_file_path = os.path.join(base_in_dir, am_dir, f"{anatomy}.nii.gz")
                if os.path.exists(am_file_path):
                    
                    # Cropping output dir
                    am_cropped_out = os.path.join(crop_out_dir, f"{am_short_name}_{anatomy}_cro.nii.gz")
                    
                    # if not am_files_cropped:
                    if First_run:
                        am_image_cropped = crop_nifti_file_with_margin(am_file_path, am_cropped_out, margin=50)
                    
                    
                    # Registration AMcro to PMcro
                    pm_image_cropped = pm_cropped_out
                    am_image_cropped = am_cropped_out
                    am_reg_out = os.path.join(reg_out_dir, f"{am_short_name}_{anatomy}_reg2_{pm_short_name}.nii.gz")
                    matrix_reg_out = os.path.join(reg_out_dir, f"{am_short_name}_{anatomy}_reg2_{pm_short_name}.txt")
                    # success = run_flirt(am_image_cropped, pm_image_cropped, am_reg_out, matrix_reg_out)
                    run_flirt(am_image_cropped, pm_image_cropped, am_reg_out, matrix_reg_out)                    
                    
                                               
                           
            First_run = False
             
                
   


# %% Kick-start
# Define files
anatomy="skull"

base_in_dir="" #insert input path here

base_out_dir="" #insert output path here




# automatisch angepasst...
path_OutDir_crop=os.path.join(base_out_dir, "01_Cropped")
path_OutDir_reg=os.path.join(base_out_dir, "02_Registered")

# create output dirs if they do not yet exist
os.makedirs(path_OutDir_crop, exist_ok=True)
os.makedirs(path_OutDir_reg, exist_ok=True)



# ---------------------------
# Start Process
process_antemortem_files(anatomy, base_in_dir, path_OutDir_crop, path_OutDir_reg)


