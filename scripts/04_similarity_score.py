# -*- coding: utf-8 -*-
"""
Created on Thu Aug 14 15:11:52 2025

@author: Schoeb-ID

# =========================
# REQUIREMENTS / USAGE
# =========================
# - Set "base_folder" to the main project folder.
# - The input folders must contain:
#     01_Cropped      -> cropped PM skull segmentations
#     02_Registered   -> AM skull segmentations registered to PM
# - PM files must follow the naming pattern:
#     [ID]_PM_skull_cro.nii.gz
# - Registered AM files must follow the naming pattern:
#     [AM_ID]_AM_skull_reg2_[PM_ID]_PM.nii.gz
# - Supported ID formats include:
#     23_123, 23-123, IMA_23_123, IMA-23-123
# - The script matches AM files to the PM case specified in the filename.
# - Registered AM masks are resampled to the voxel grid of the corresponding
#   PM image using nearest-neighbor interpolation.
# - The script calculates overlap by a similarity score (Precision) :
#     Precision = |AM ∩ PM| / |AM|
# - Results are saved automatically in "03_Results":
#     - One Excel file per PM case containing all matching AM cases.
#     - "Best_AM_per_PM.xlsx" containing the best AM match for each PM case.
# - Required Python packages:
#     nibabel, numpy, pandas, scipy, tqdm
"""

# %% Packages
import os
import re
import nibabel as nib
import numpy as np
import pandas as pd
from scipy.ndimage import affine_transform
from tqdm import tqdm  # Progress bar


# %% Functions
# === Config / Folders ===
base_folder = "insert_path_here"    # path to the main folder
pm_folder = os.path.join(base_folder, "01_Cropped")
am_folder = os.path.join(base_folder, "02_Registered")
results_folder = os.path.join(base_folder, "03_Results")
os.makedirs(results_folder, exist_ok=True)

# ---------- ID parsing & normalization ----------
# Supported formats:
#   "xx_yyyy", "xx-yyyy", "IMA_xx_yyyy", "IMA-xx-yyyy"
ID_RE = re.compile(r"^(?P<prefix>IMA_)?(?P<a>\d{2})[_-](?P<b>\d{3,5})$", re.IGNORECASE)

def parse_id(id_str: str):
    """
    Parse a case-id like 'xx_yyyy' or 'IMA_xx_yyyy' (also with '-').
    Returns a normalized tuple: (prefix: 'IMA_' or '', a:str, b:str) or None if not matched.
    """
    match = ID_RE.match(id_str)
    if not match:
        return None
    prefix = (match.group("prefix") or "").upper()  # '' or 'IMA_'
    a = match.group("a")
    b = match.group("b")
    return (prefix, a, b)

def normalize_id_for_compare(id_str: str):
    """
    Normalize any supported id string to a tuple for robust equality:
      ('IMA_', 'xx', 'yyyy') or ('', 'xx', 'yyyy')
    """
    parsed = parse_id(id_str)
    return parsed  # None if not matched

def format_id(prefix, a, b):
    """Return a canonical string form for display/filenames, e.g., 'IMA_xx_yyyy' or 'xx_yyyy'."""
    return f"{prefix}{a}_{b}"

# ---------- Filename patterns (more flexible; we grab the ID token and then normalize) ----------
PM_FILE_RE = re.compile(r"^(?P<pm_id>(?:IMA_)?\d{2}[_-]\d{3,5})_PM_skull_cro\.nii(\.gz)?$", re.IGNORECASE)
AM_FILE_RE = re.compile(
    r"^(?P<am_id>(?:IMA_)?\d{2}[_-]\d{3,5})_AM_skull_reg2_(?P<pm_id>(?:IMA_)?\d{2}[_-]\d{3,5})_PM\.nii(\.gz)?$",
    re.IGNORECASE
)

def extract_pm_id_from_filename(filename: str):
    match = PM_FILE_RE.match(filename)
    if not match:
        return None
    return match.group("pm_id")

def extract_am_ids_from_filename(filename: str):
    match = AM_FILE_RE.match(filename)
    if not match:
        return None, None
    return match.group("am_id"), match.group("pm_id")

# ---------- Core ops (same math as your working script) ----------
def resample_to_reference(moving_img, reference_img):
    """
    Resample moving_img to the voxel grid of reference_img using nearest neighbor.
    transform = inv(mov_affine) @ ref_affine
    """
    ref_affine = reference_img.affine
    mov_affine = moving_img.affine
    mov_data = moving_img.get_fdata()
    transform = np.linalg.inv(mov_affine) @ ref_affine
    ref_shape = reference_img.shape
    resampled = affine_transform(
        mov_data,
        matrix=transform[:3, :3],
        offset=transform[:3, 3],
        output_shape=ref_shape,
        order=0
    )
    return resampled.astype(np.uint8)

def overlap_precision(reference, candidate):
    """
    Precision = |AM ∩ PM| / |AM|
    Both arrays expected as binary (0/1).
    """
    intersection = np.sum((reference == 1) & (candidate == 1))
    predicted = np.sum(candidate == 1)
    if predicted == 0:
        return 0.0
    return intersection / predicted

# ---------- Collect PM files ----------
pm_files = [
    f for f in os.listdir(pm_folder)
    if f.endswith(".nii") or f.endswith(".nii.gz")
]
# Keep only those that match the PM filename pattern
pm_files = [f for f in pm_files if extract_pm_id_from_filename(f) is not None]

summary_results = []

# ---------- Loop over PM cases ----------
for pm_file in tqdm(pm_files, desc="Overall PM case progress"):
    pm_id_raw = extract_pm_id_from_filename(pm_file)
    if pm_id_raw is None:
        continue

    # Normalize the PM id for comparison
    pm_id_norm = normalize_id_for_compare(pm_id_raw)
    if pm_id_norm is None:
        # Should not happen if regex matched, but be safe
        continue

    pm_id_display = format_id(*pm_id_norm)  # canonical display form

    print(f"\nStarting processing of PM case {pm_id_display} ({pm_file})...")

    pm_path = os.path.join(pm_folder, pm_file)
    pm_nii = nib.load(pm_path)
    pm_bin = (pm_nii.get_fdata() > 0).astype(np.uint8)

    pm_results = []

    # Find matching AM files for THIS PM (both schemes; both separators)
    for am_file in os.listdir(am_folder):
        if not (am_file.endswith(".nii") or am_file.endswith(".nii.gz")):
            continue

        am_id_raw, pm_ref_raw = extract_am_ids_from_filename(am_file)
        if am_id_raw is None:
            continue

        am_id_norm = normalize_id_for_compare(am_id_raw)
        pm_ref_norm = normalize_id_for_compare(pm_ref_raw)
        if am_id_norm is None or pm_ref_norm is None:
            continue

        # Compare normalized tuples (prefix, a, b)
        if pm_ref_norm != pm_id_norm:
            continue

        am_path = os.path.join(am_folder, am_file)
        am_nii = nib.load(am_path)

        # Resample AM to PM grid (nearest neighbor), then binarize
        am_resampled = resample_to_reference(am_nii, pm_nii)
        am_bin = (am_resampled > 0).astype(np.uint8)

        precision = overlap_precision(pm_bin, am_bin)

        am_id_display = format_id(*am_id_norm)
        pm_results.append((am_id_display, am_file, precision))
        print(f"   ➜ AM case {am_id_display} compared (Precision: {precision:.4f})")

    if not pm_results:
        print(f"No matching AM cases found for {pm_id_display}.")
        continue

    # Save per-PM results (sorted)
    df_pm = pd.DataFrame(pm_results, columns=["AM_Case_ID", "Filename", "Precision"])
    df_pm_sorted = df_pm.sort_values(by="Precision", ascending=False)
    excel_path = os.path.join(results_folder, f"{pm_id_display}_results.xlsx")
    df_pm_sorted.to_excel(excel_path, index=False)

    best_am = df_pm_sorted.iloc[0]
    summary_results.append((pm_id_display, best_am["AM_Case_ID"], best_am["Filename"], best_am["Precision"]))

    print(f"Finished PM case {pm_id_display}. Best Precision: {best_am['Precision']:.4f}")

# ---------- Overall summary ----------
df_summary = pd.DataFrame(summary_results, columns=["PM_Case_ID", "Best_AM_Case_ID", "Filename", "Precision"])
df_summary_sorted = df_summary.sort_values(by="Precision", ascending=False)
df_summary_sorted.to_excel(os.path.join(results_folder, "Best_AM_per_PM.xlsx"), index=False)

print("\nComparison completed. Results saved in the 'Results' folder.")














