"""Functions for building bash scripts."""

import datetime
import shlex
from os import PathLike

from ecpac import utils

SCHEBANG = "#!/usr/bin/bash"


def _buf_pad_before_if_not_empty(buf: list[str], before: str = "") -> list[str]:
    """Pad a buffer with a string if the buffer is not empty."""
    if len(buf) > 0:
        return [before, *buf]
    return buf


def _buf_pad_after_if_not_empty(buf: list[str], after: str = "") -> list[str]:
    """Pad a buffer with a string if the buffer is not empty."""
    if len(buf) > 0:
        return [*buf, after]
    return buf


def _sbatch_header(**kwargs) -> list[str]:  # noqa: ANN003
    """Generate the header for a sbatch job script.

    _ in keywords are replaced with -.
    """
    return [f"#SBATCH --{k.replace('_', '-')} {v}" for k, v in kwargs.items()]


def job_template(  # noqa: PLR0913
    *,
    job_name: str,
    job_stdout_file: str,
    job_duration_limit: datetime.timedelta,
    job_threads: int,
    job_memory_gb: float,
    wd: str | PathLike,
    path_input: str | PathLike,
    path_output: str | PathLike,
    cpac_threads: int,
    cpac_memory_gb: float,
    path_image: str | PathLike,
    analysis_level: str,
    subject: str,
    pipeline: str,
    pipeline_is_preconfig: bool,
    cpac_sources: str | PathLike | None = None,
    extra_cpac_args: str | None = None,
    before_run: list[str] | None = None,
    after_run: list[str] | None = None,
) -> str:
    """Generate a bash script for running C-PAC with sbatch."""
    before_run = before_run if before_run is not None else []
    after_run = after_run if after_run is not None else []

    cpac_call = [
        "singularity",
        "run",
        "--cleanenv",
    ]

    # Patch C-PAC sources if available
    if cpac_sources:
        cpac_call.extend(
            [
                "-B",
                f"{cpac_sources}/CPAC:/code/CPAC",
                "-B",
                f"{cpac_sources}/dev/docker_data/run.py:/code/run.py",
                "-B",
                f"{cpac_sources}/dev/docker_data:/cpac_resources",
            ]
        )

    cpac_call.extend(
        [
            "-B",
            f"{path_input}:{path_input}:ro",
            "-B",
            f"{path_output}:{path_output}",
        ]
    )

    pipeline_args = ["--preconfig" if pipeline_is_preconfig else "--pipeline-file", str(pipeline)]

    cpac_call.extend(
        [
            str(path_image),
            str(path_input),
            str(path_output),
            analysis_level,
            "--skip_bids_validator",
            "--n_cpus",
            str(cpac_threads),
            "--mem_gb",
            str(cpac_memory_gb),
            "--participant_label",
            subject,
            *pipeline_args,
        ]
    )

    cpac_call_str = shlex.join(cpac_call)

    if extra_cpac_args:
        cpac_call_str += f" {extra_cpac_args}"

    buf = [
        SCHEBANG,
        *_sbatch_header(
            job_name=job_name,
            output=job_stdout_file,
            nodes=1,
            partition="RM-shared",
            time=utils.timedelta_to_hms(job_duration_limit),
            ntasks_per_node=job_threads,
            mem=utils.bridges_gb_to_mb(job_memory_gb),
        ),
        "",
        "set -x",
        "",
        shlex.join(["cd", str(wd)]) + " || exit",
        "",
        *_buf_pad_after_if_not_empty(before_run),
        cpac_call_str,
        *_buf_pad_before_if_not_empty(after_run),
        "",
    ]

    return "\n".join(buf)
