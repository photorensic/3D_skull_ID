"""
3D_ID_Project: Segmentations using TotalSegmentator

@author: D.Neuhaus and Schoeb-ID, adapted from A.Zirn


# =========================
# REQUIREMENTS / USAGE
# =========================
# - Set "input_folder" to the directory containing the NIfTI (.nii.gz) files that should be segmented.
# - Set "output_folder" to the directory where the segmentation results
#   should be stored. It will be created automatically if it does not exist.
# - Each NIfTI file in the input folder is processed individually.
# - Input files should be in .nii.gz format.
# - The script performs TotalSegmentator skull segmentation only.
# - TotalSegmentator must be installed and available in the Python environment.
# - Input and output folders can contain AM and PM data; the script does not
#   distinguish between them.

"""


import os
import torch.cuda
import numpy
from totalsegmentator.python_api import totalsegmentator


input_folder = "insert_path_here" # Define input directory
output_folder = "insert_path_here"     # AM and PM in same directory!


def segment_files_in_folder(in_folder, out_folder):
    if not os.path.exists(out_folder):
        os.makedirs(out_folder)

    files = os.listdir(in_folder)

    for file_name in files:
        input_file_path = os.path.join(in_folder, file_name)
        file_name = file_name.rstrip(".nii.gz")  # entfernt alle '.nii.gz' am Ende
        os.makedirs(os.path.join(out_folder, file_name))
        output_file_path = os.path.join(out_folder, file_name)
#        output_file_path = output_file_path.rstrip(".nii.gz")  # entfernt alle '.nii.gz' am Ende


        if os.path.isfile(input_file_path):
            skull = totalsegmentator(input=input_file_path, output=output_file_path, fast=False, task="total",
                                       roi_subset=["skull"], device="gpu")



if __name__ == "__main__":
    segment_files_in_folder(input_folder, output_folder)
