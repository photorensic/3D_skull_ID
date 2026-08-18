# Cranial 3D Computed Tomography for Computer-Aided Identification of Deceased

This repository contains four custom-made Python scripts for the identification
of deceased individuals based on cranial antemortem and postmortem CT scans.

The scripts form a sequential pipeline and must be executed in the correct order.
A short introduction describing the functionality of each script is provided
at the beginning of the respective script.

## Content

### Script 1 — `01_DICOM2NIfTI.py`

This script converts all antemortem and postmortem DICOM files into NIfTI files
to reduce storage requirements and improve pipeline performance. Additionally,
all files are anonymized, including filenames and metadata.

### Script 2 — `02_skull_segmentation.py`

With the help of TotalSegmentator, all NIfTI files are segmented and binary
masks of the skull are created.

### Script 3 — `03_AM_PM_registration.py`

All antemortem segmentations are registered to the corresponding postmortem
skull segmentation(s) and stored as separate NIfTI files.

### Script 4 — `04_similarity_score.py`

A similarity score is calculated to quantify the overlap between the antemortem
and postmortem data.

$$
\text{Similarity Score} = \frac{|A \cap B|}{|B|}
$$

> [!IMPORTANT]
> This similarity score assumes that all postmortem scans contain the complete
> skull, including the mandible. The antemortem scans, however, may contain
> only a partial cranial scan.

## Authors

TBD
