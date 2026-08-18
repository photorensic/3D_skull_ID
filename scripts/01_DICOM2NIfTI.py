# -*- coding: utf-8 -*-
"""
Created on Fri Aug  8 14:32:46 2025

@author: Schoeb-ID

# =========================
# REQUIREMENTS / USAGE
# =========================
# - Set "wurzelpfad" to the main data folder.
# - Set "mapping_datei" to the Excel mapping file path.
# - Patient folders must be named YY-XXXX/YY-XXXXX (e.g. 23-0647)
#   or IMA_YY_XXX (e.g. IMA_23_123).
# - Supported structures:
#     MainFolder/PatientFolder
#     MainFolder/Set1|Set2|Set3/PatientFolder
# - DICOM folders: DICOM_AM and DICOM_PM
# - "dcm2niix" must be installed and available in PATH.
# - Mapping file columns: "Originalname" and "NeuerName". 
# - The file will be created automatically if it does not exist.
"""

import os
import re
import random
import pandas as pd
import subprocess

# =========================
# SETTINGS
# =========================
root_path = "insert_path_here"     # Path to main data folder
mapping_file = "insert_path_here"  # Path to Excel mapping sheet (existing or to be created)

# =========================
# FUNCTION: Load mapping
# =========================
def load_mapping(file_path):
    if os.path.exists(file_path):
        return pd.read_excel(file_path)
    else:
        return pd.DataFrame(columns=["Original_Name", "New_Name"])

# =========================
# FUNCTION: Generate new unique number
# =========================
def generate_new_number(year, existing_numbers):
    while True:
        new_number = random.randint(100, 999)
        if f"IMA_{year}_{new_number}" not in existing_numbers:
            return new_number

# =========================
# FUNCTION: DICOM → NIfTI conversion
# =========================
def convert_dicom_to_nifti(dicom_path, output_dir, output_name):
    os.makedirs(output_dir, exist_ok=True)
    output_file_path = os.path.join(output_dir, output_name + ".nii.gz")

    # Skip conversion if the NIfTI file already exists
    if os.path.exists(output_file_path):
        print(f"Skipping {output_name}, NIfTI already exists.")
        return

    command = [
        'dcm2niix', '-z', 'y',  # gzip compression (.nii.gz)
        '-ba', 'y',             # anonymize DICOM metadata
        '-f', output_name,
        '-o', output_dir,
        dicom_path
    ]
    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"NIfTI created: {output_name}")
    else:
        print(f"Error converting {output_name}")
        print(result.stderr)

# =========================
# MAIN ROUTINE
# =========================
mapping_df = load_mapping(mapping_file)
existing_new_names = set(mapping_df["New_Name"])

# Check whether Set folders exist
set_folders_exist = any(
    os.path.isdir(os.path.join(root_path, s)) for s in ["Set1", "Set2", "Set3"]
)

# If Set folders exist, search inside them;
# otherwise, search directly in the main folder
if set_folders_exist:
    search_paths = [os.path.join(root_path, s) for s in ["Set1", "Set2", "Set3"] if os.path.isdir(os.path.join(root_path, s))]
else:
    search_paths = [root_path]

for search_path in search_paths:
    for folder in os.listdir(search_path):
        old_path = os.path.join(search_path, folder)
        if not os.path.isdir(old_path):
            continue

        # -------------------------
        # Checking whether the folder name is already anonymized
        # -------------------------
        old_match = re.match(r"^(\d{2})-(\d{4,5})$", folder)    # e.g. 23-0647
        new_match = re.match(r"^IMA_(\d{2})_(\d{3})$", folder)  # e.g. IMA_23_123

        if old_match:
            year = old_match.group(1)

            # Check whether the original name is already in the mapping
            if folder in mapping_df["Original_Name"].values:
                new_name = mapping_df.loc[mapping_df["Original_Name"] == folder, "New_Name"].values[0]
            else:
                new_number = generate_new_number(year, existing_new_names)
                new_name = f"IMA_{year}_{new_number}"
                mapping_df = pd.concat([
                    mapping_df,
                    pd.DataFrame({"Original_Name": [folder], "New_Name": [new_name]})
                ], ignore_index=True)
                existing_new_names.add(new_name)

            new_path = os.path.join(search_path, new_name)
            if old_path != new_path:
                os.rename(old_path, new_path)
                print(f"Renamed: {folder} → {new_name}")
                mapping_df.to_excel(mapping_file, index=False)
                print(f"Mapping saved: {mapping_file}")

        elif new_match:
            year = new_match.group(1)
            new_name = folder
            new_path = old_path

        else:
            print(f"Skipping folder with unknown naming pattern: {folder}")
            continue

        # -------------------------
        # Check for DICOM folders and convert them
        # -------------------------
        dicom = os.path.join(new_path, "DICOM")
        dicom_am = os.path.join(new_path, "DICOM_AM")
        dicom_pm = os.path.join(new_path, "DICOM_PM")
        dicom_am_mri = os.path.join(new_path, "DICOM_AM_MRI")
        nifti_dir = os.path.join(new_path, "Nifti")

        if os.path.isdir(dicom):
            convert_dicom_to_nifti(dicom, nifti_dir, new_name + "_AM")
        if os.path.isdir(dicom_am):
            convert_dicom_to_nifti(dicom_am, nifti_dir, new_name + "_AM")
        if os.path.isdir(dicom_pm):
            convert_dicom_to_nifti(dicom_pm, nifti_dir, new_name + "_PM")
        if os.path.isdir(dicom_am_mri):
            convert_dicom_to_nifti(dicom_am_mri, nifti_dir, new_name + "_AM_MRI")


# =========================
# Save mapping
# =========================
mapping_df.to_excel(mapping_file, index=False)
print("Mapping saved:", mapping_file)
