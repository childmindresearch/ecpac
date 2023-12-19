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


BASH_TEMPLATE_JOB = """\
#!/usr/bin/bash
#SBATCH --job-name {job_name}
#SBATCH --output {stdout_file}
#SBATCH --nodes 1
#SBATCH --partition RM-shared
#SBATCH --time {duration_str}
#SBATCH --ntasks-per-node {threads}
#SBATCH --mem {memory_mb}

set -x

cd {wd}

singularity run \
--cleanenv \
{cpac_bin_opt} \
-B {path_input}:{path_input}:ro \
-B {path_output}:{path_output} \
{image} {path_input} {path_output} {analysis_level} \
--skip_bids_validator \
--n_cpus {cpac_threads} \
--mem_gb {cpac_memory_gb} \
--participant_label {subject} \
{pipeline} \
{extra_cpac_args}
"""

BASH_TEMPLATE_PIPELINE_PRECONFIG = "--preconfig {pipeline}"
BASH_TEMPLATE_PIPELINE_CONFIG_FILE = "--pipeline-file {pipeline}"


BASH_TEMPLATE_JOB_CPAC_BIN = """\
-B {cpac_bin}/CPAC:/code/CPAC \
-B {cpac_bin}/dev/docker_data/run.py:/code/run.py \
-B {cpac_bin}/dev/docker_data:/cpac_resources \
"""
