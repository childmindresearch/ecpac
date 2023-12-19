import dataclasses
import itertools
import os
import pathlib as pl
import re
import stat
import subprocess
from datetime import datetime, timedelta
from typing import List, Optional, Union

import click

from ecpac import icons

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


@dataclasses.dataclass
class FsPlan:
    """Planned file system change"""

    path: pl.Path
    is_file: bool = False
    contents_text: Optional[str] = None
    make_executable: bool = False

    def apply(self) -> None:
        if self.is_file:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            txt = "" if self.contents_text is None else self.contents_text
            with open(self.path, "w", encoding="utf-8") as handle:
                handle.write(txt)

            if self.make_executable:
                self.path.chmod(self.path.stat().st_mode | stat.S_IEXEC)
        else:
            self.path.mkdir(parents=True, exist_ok=True)


def _bullet_str_list(list_: list) -> str:
    return "\n".join([f" - {i}" for i in list_])


def _cli_check_exist_file(path: pl.Path, label: str = "") -> bool:
    if path.exists() and path.is_file():
        return True
    click.secho(f'Error: {label} file does not exist! "{path}"', fg="red")
    return False


def _cli_check_exist_dir(path: pl.Path, label: str = "") -> bool:
    if path.exists() and path.is_dir():
        return True
    click.secho(f'Error: {label} directory does not exist! "{path}"', fg="red")
    return False


def option_or_prompt(opt: Optional[str], prompt: str, default: Optional[str] = None) -> str:
    if opt is not None:
        return opt
    return click.prompt(prompt, default=default, type=str)


def option_or_confirm(opt: Optional[bool], prompt: str, default: Optional[bool] = False) -> bool:
    if opt is not None:
        return opt
    return click.confirm(prompt, default=default)


def option_truthy(opt: Optional[str]) -> Optional[bool]:
    if opt is None:
        return None
    opt_lower = opt.lower()
    return opt_lower == "true" or opt_lower == "y" or opt_lower == "yes" or opt_lower == "1"


def timedelta_to_hms(t: timedelta) -> str:
    s = t.total_seconds()
    return f"{s // 3600:02.0f}:{s % 3600 // 60:02.0f}:{s % 60:02.0f}"


def _cpac_dir_valid(path: Union[str, os.PathLike]) -> bool:
    p = pl.Path(path)
    return (
        p.exists()
        and (p / "dev/docker_data/run.py").exists()
        and (p / "dev/docker_data/run-with-freesurfer.sh").exists()
    )


def filesafe(f: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", f)


@click.command()
@click.option(
    "-i",
    "--input",
    "arg_input",
    type=str,
    help="Input directory (contains subject folders).",
)
@click.option("-o", "--output", "arg_output", type=str, help="Output directory (contains runs).")
@click.option("-r", "--run", "arg_run", type=str, help="Run name.")
@click.option("-g", "--image", "arg_image", type=str, help="Singularity image file (.sif).")
@click.option(
    "-s",
    "--subject",
    "arg_subject",
    type=str,
    help="List of subjects, separate via whitespace.",
)
@click.option(
    "-p",
    "--pipeline",
    "arg_pipeline",
    type=str,
    help="List of pipeline presets, separate via whitespace.",
)
@click.option(
    "-a",
    "--analysis_level",
    "arg_analysis_level",
    type=str,
    help='Analysis level ("participant", "group", ' '"test_config").',
)
@click.option("-c", "--cpac", "arg_cpac", type=str, help="C-PAC folder for patching image.")
@click.option("-m", "--memory_gb", "arg_memory_gb", type=str, help="Memory (GB) for each job.")
@click.option(
    "-t",
    "--threads",
    "arg_threads",
    type=str,
    help="Number of threads/cores for each job.",
)
@click.option(
    "-d",
    "--duration_h",
    "arg_duration_h",
    type=str,
    help="Maximum job runtime (in hours).",
)
@click.option(
    "-w",
    "--save_working_dir",
    "arg_save_working_dir",
    type=str,
    help="Should the C-PAC working dir be saved.",
)
@click.option(
    "-x",
    "--extra_cpac_args",
    "arg_extra_cpac_args",
    type=str,
    help="Additional arguments that will be passed to C-PAC.",
)
def main(
    arg_input: Optional[str] = None,
    arg_output: Optional[str] = None,
    arg_run: Optional[str] = None,
    arg_image: Optional[str] = None,
    arg_subject: Optional[str] = None,
    arg_pipeline: Optional[str] = None,
    arg_analysis_level: Optional[str] = None,
    arg_cpac: Optional[str] = None,
    arg_memory_gb: Optional[str] = None,
    arg_threads: Optional[str] = None,
    arg_duration_h: Optional[str] = None,
    arg_save_working_dir: Optional[str] = None,
    arg_extra_cpac_args: Optional[str] = None,
) -> None:
    if not PSC_PROJECT_USER.exists():
        click.secho(
            f'Error: User directory does not exist! "{PSC_PROJECT_USER}" ' "(This script is meant to run on PSC)",
            fg="red",
        )
        if not click.confirm(click.style("Continue anyway?", fg="red"), default=False):
            return

    # Run name

    run_id = option_or_prompt(
        opt=arg_run,
        prompt=icons.ICON_JOB + click.style("Run name", fg="blue"),
        default=datetime.now().strftime("run_%y-%m-%d_%H-%M-%S"),
    )

    # Resources

    res_threads = int(
        option_or_prompt(
            opt=arg_threads,
            prompt=icons.ICON_THREADS + click.style("Number of threads/cores (int)", fg="blue"),
            default=str(8),
        )
    )

    res_memory_gb = float(
        option_or_prompt(
            opt=arg_memory_gb,
            prompt=icons.ICON_MEMORY
            + click.style("Memory (GB, float) (can not be more than 2*threads on PSC)", fg="blue"),
            default=f"{2 * res_threads:.1f}",
        )
    )

    res_duration = timedelta(
        hours=float(
            option_or_prompt(
                opt=arg_duration_h,
                prompt=icons.ICON_DURATION + click.style("Duration (hours, float)", fg="blue"),
                default=f"{48.0:.1f}",
            )
        )
    )

    # Image

    while True:
        path_image = pl.Path(
            option_or_prompt(
                opt=arg_image,
                prompt=icons.ICON_SINGULARITY + click.style("Image file", fg="blue"),
                default=str(PSC_IMAGE_DEFAULT),
            )
        )

        if _cli_check_exist_file(path_image, label="Singularity image"):
            break
        arg_image = None

    # C-PAC patching

    while True:
        if arg_cpac is not None:
            patch_cpac = True
            path_cpac = pl.Path(arg_cpac)
        else:
            cpac_opt: str = click.prompt(
                icons.ICON_CPAC + click.style("C-PAC directory (empty to use image version)", fg="blue"),
                default="",
                type=str,
            )
            if len(cpac_opt) == 0:
                patch_cpac = False
                path_cpac = pl.Path()
            else:
                patch_cpac = True
                path_cpac = pl.Path(cpac_opt)

        if not patch_cpac or _cpac_dir_valid(path_cpac):
            break
        else:
            click.secho(f'Error: Not a valid cpac dir! "{path_cpac}"', fg="red")

    # Input directory

    while True:
        path_input = pl.Path(
            option_or_prompt(
                opt=arg_input,
                prompt=icons.ICON_FOLDER + click.style("Input directory", fg="blue"),
            )
        )

        if _cli_check_exist_dir(path_input, label="Input"):
            break

    # Subjects

    while True:
        if arg_subject is None:
            subjects = [path.stem for path in path_input.iterdir() if path.is_dir()]

            subjects = re.split(
                "\s+",
                click.prompt(
                    icons.ICON_SUBJECT + click.style("Subjects (separate with space)", fg="blue"),
                    default=" ".join(subjects),
                ),
            )

        else:
            subjects = re.split("\s+", arg_subject)

        not_exist = []
        for sub in subjects:
            if not (path_input / sub).exists():
                arg_subject = None
                not_exist.append(sub)
        if len(not_exist) == 0:
            break

        not_exist_str = " ".join(f'"{sub}"' for sub in not_exist)
        click.secho(
            f"Error: Some subject directories do not exist in input dir!\n"
            f'Input dir: "{path_input}"\n'
            f"Missing subjects: {not_exist_str}",
            fg="red",
        )

    # Output directory

    path_output = pl.Path(
        option_or_prompt(
            opt=arg_output,
            prompt=icons.ICON_FOLDER + click.style("Output directory", fg="blue"),
            default=str(PSC_OUTPUT_DEFAULT),
        )
    )

    # Pipeline configs

    pipeline_ids = re.split(
        "\s+",
        option_or_prompt(
            opt=arg_pipeline,
            prompt=icons.ICON_PIPELINE + click.style("Pipelines (separate with space)", fg="blue"),
            default=ID_PIPELINE_DEFAULT,
        ),
    )

    preconfig_ids: List[str] = []
    pipeline_config_files: List[str] = []
    for pipe in pipeline_ids:
        if pipe in CPAC_PRECONFIGS:
            preconfig_ids.append(pipe)
        else:
            pipeline_config_files.append(pipe)
            if not pl.Path(pipe).exists():
                click.secho(f'Error: Pipeline config file does not exist! "{pipe}"', fg="red")
                return

    if len(preconfig_ids) > 0 and len(pipeline_config_files) > 0:
        click.secho(
            f"Error: Can not mix preconfigs and pipeline config files!\n"
            f"Preconfigs: {_bullet_str_list(preconfig_ids)}\n"
            f"Pipeline config files: {_bullet_str_list(pipeline_config_files)}",
            fg="red",
        )
        return

    use_preconfigs = len(preconfig_ids) > 0

    if not use_preconfigs:
        pipeline_ids = [str(pl.Path(p).absolute()) for p in pipeline_ids]

    del preconfig_ids
    del pipeline_config_files

    # Analysis level

    while True:
        analysis_level = option_or_prompt(
            opt=arg_analysis_level,
            prompt=click.style(f"Analysis level {CPAC_ANALYSIS_LEVELS}", fg="blue"),
            default=ANALYSIS_LEVEL_DEFAULT,
        )

        if analysis_level in CPAC_ANALYSIS_LEVELS:
            break

        click.secho(
            f"Error: Analysis level invalid ({analysis_level})\n" f'Must be one of: "{CPAC_ANALYSIS_LEVELS}"',
            fg="red",
        )

    # Save C-PAC working dir

    save_working_dir = option_or_confirm(
        opt=option_truthy(arg_save_working_dir),
        default=False,
        prompt=icons.ICON_SAVE + click.style("Save working directory", fg="blue"),
    )

    # Extra cpac args

    extra_cpac_args = option_or_prompt(
        opt=arg_extra_cpac_args,
        prompt=icons.ICON_EXTRA_ARGS + click.style("Extra args to pass to C-PAC?", fg="blue"),
        default="",
    )

    # Plan out dirs and job files

    fs_plans: List[FsPlan] = []
    job_paths = []
    example_job = None
    example_path_stdout_log = None
    for idx, (pipe, sub) in enumerate(itertools.product(pipeline_ids, subjects)):
        pipe_id = pipe if use_preconfigs else f"{idx:03d}_{pl.Path(pipe).stem}"

        path_out = path_output / run_id / pipe_id / sub
        path_out_full = path_out / "output"
        path_out_wd = path_out / "wd"
        path_job = path_out / "run_job.sh"
        path_stdout_log = path_out / "out.log"

        extra_args: List[str] = [extra_cpac_args]
        if save_working_dir:
            extra_args.append(f"--save_working_dir {path_out_wd.absolute()}")

        job = BASH_TEMPLATE_JOB.format(
            job_name=f"{run_id}_{pipe_id}_{sub}",
            stdout_file=path_stdout_log,
            cpac_bin_opt="" if not patch_cpac else BASH_TEMPLATE_JOB_CPAC_BIN.format(cpac_bin=path_cpac.absolute()),
            wd=path_out.absolute(),
            subject=sub,
            pipeline=(
                BASH_TEMPLATE_PIPELINE_PRECONFIG if use_preconfigs else BASH_TEMPLATE_PIPELINE_CONFIG_FILE
            ).format(pipeline=pipe),
            path_input=path_input.absolute(),
            path_output=path_out_full.absolute(),
            image=path_image.absolute(),
            threads=res_threads,
            duration_str=timedelta_to_hms(res_duration),
            memory_mb=int(res_memory_gb * 1000),
            cpac_threads=max(res_threads - 1, 1),
            cpac_memory_gb=max(res_memory_gb - 1, 1),
            extra_cpac_args=" ".join(extra_args),
            analysis_level=analysis_level,
        )

        fs_plans.append(FsPlan(path=path_job, is_file=True, contents_text=job, make_executable=True))
        fs_plans.append(FsPlan(path=path_out_full, is_file=False))
        if save_working_dir:
            fs_plans.append(FsPlan(path=path_out_wd, is_file=False))

        job_paths.append(path_job)

        if example_job is None:
            example_job = job
            example_path_stdout_log = path_stdout_log

    # Plan executor file

    sbatches = "\n".join([f"sbatch {j}" for j in job_paths])
    executor = f"#!/usr/bin/bash\n{sbatches}"
    path_executor = path_output / run_id / "run.sh"

    fs_plans.append(
        FsPlan(
            path=path_executor,
            is_file=True,
            contents_text=executor,
            make_executable=True,
        )
    )

    # User sanity check

    click.secho(icons.ICON_FOLDER + "The following directories and files will be created:", bg="blue")

    fs_plans = sorted(fs_plans, key=lambda i: i.path.absolute().as_posix())

    for plan in fs_plans:
        label_type = "F" if plan.is_file else "D"
        label_executable = "x" if plan.make_executable else " "
        style_fg = "green" if plan.is_file else "blue"
        click.secho(f" - [{label_type}{label_executable}] {plan.path}", fg=style_fg)

    if click.confirm(icons.ICON_PREVIEW + click.style("Preview example job?", fg="blue"), default=False):
        print(example_job)

    if not click.confirm(icons.ICON_SAVE + click.style("Create files + folders?", bg="blue"), default=None):
        return

    for plan in fs_plans:
        plan.apply()

    if click.confirm(icons.ICON_LAUNCH + click.style("Launch now?", bg="blue"), default=None):
        subprocess.run([path_executor], shell=True)

        click.secho("Jobs were executed!", bg="blue")
        click.secho("Some commands you might find helpful:", fg="blue")
        click.secho("  Follow job output:", fg="blue")
        click.secho(f"tail -f {example_path_stdout_log}")
        click.secho("  List all running jobs:", fg="blue")
        click.secho("squeue --me")


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

if __name__ == "__main__":
    main()
