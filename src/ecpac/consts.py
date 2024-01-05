"""Constants."""

import os
import pathlib as pl

ID_PIPELINE_DEFAULT = "default"
FILENAME_JOB = "job.sh"
FOLDERNAME_OUTPUT = "output"

# Grab from $PROJECT, which is "/ocean/projects/{med000000p}/{username}"
ENV_PROJECT = os.environ.get("PROJECT", "")
PSC_PROJECT_USER = pl.Path(ENV_PROJECT)
PSC_OUTPUT_DEFAULT = PSC_PROJECT_USER / "ecpac_runs"
PSC_IMAGE_DEFAULT = PSC_PROJECT_USER / "images/cpac.sif"

CPAC_ANALYSIS_LEVELS = ("participant", "group", "test_config")
ANALYSIS_LEVEL_DEFAULT = "participant"
CPAC_PRECONFIGS = [
    "abcd-options",
    "abcd-prep",
    "anat-only",
    "benchmark-FNIRT",
    "blank",
    "ccs-options",
    "default",
    "default-deprecated",
    "fmriprep-options",
    "fx-options",
    "monkey",
    "ndmg",
    "nhp-macaque",
    "preproc",
    "rbc-options",
    "rodent",
]
