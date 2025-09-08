"""Main entry point for ecpac."""

import itertools
import math
import pathlib as pl
import re
import shlex
import subprocess
from datetime import datetime, timedelta

import click

from ecpac import bash_builder, cli_utils, consts, icons, slack, utils
from ecpac.fsplan import FsPlan


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
    help='Analysis level ("participant", "group", "test_config").',
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
def main(  # noqa: C901, PLR0912, PLR0913, PLR0915
    arg_input: str | None = None,
    arg_output: str | None = None,
    arg_run: str | None = None,
    arg_image: str | None = None,
    arg_subject: str | None = None,
    arg_pipeline: str | None = None,
    arg_analysis_level: str | None = None,
    arg_cpac: str | None = None,
    arg_memory_gb: str | None = None,
    arg_threads: str | None = None,
    arg_duration_h: str | None = None,
    arg_save_working_dir: str | None = None,
    arg_extra_cpac_args: str | None = None,
) -> None:
    """CLI entry point."""
    if not consts.PSC_PROJECT_USER.exists():
        click.secho(
            f'Error: User directory does not exist! "{consts.PSC_PROJECT_USER}" (This script is meant to run on PSC)',
            fg="red",
        )
        if not click.confirm(click.style("Continue anyway?", fg="red"), default=False):
            return

    # Run name

    run_id = cli_utils.option_or_prompt(
        opt=arg_run,
        prompt=icons.ICON_JOB + click.style("Run name", fg="blue"),
        default=datetime.now().strftime("run_%y-%m-%d_%H-%M-%S"),  # noqa: DTZ005
    )

    # Resources

    res_threads = int(
        cli_utils.option_or_prompt(
            opt=arg_threads,
            prompt=cli_utils.icon_message(icons.ICON_THREADS, "Number of threads/cores (int) (C-PAC will get 1 less)"),
            default=str(8),
        ),
    )

    res_memory_gb = float(
        cli_utils.option_or_prompt(
            opt=arg_memory_gb,
            prompt=cli_utils.icon_message(icons.ICON_MEMORY, "Memory (GB, float) (C-PAC will get 1GB less)"),
            default=f"{2 * res_threads:.1f}",
        ),
    )

    res_duration = timedelta(
        hours=float(
            cli_utils.option_or_prompt(
                opt=arg_duration_h,
                prompt=cli_utils.icon_message(icons.ICON_DURATION, "Duration (hours, float)"),
                default=f"{48.0:.1f}",
            ),
        ),
    )

    # Image

    while True:
        path_image = pl.Path(
            cli_utils.option_or_prompt(
                opt=arg_image,
                prompt=cli_utils.icon_message(icons.ICON_SINGULARITY, "Image file"),
                default=str(consts.PSC_IMAGE_DEFAULT),
            ),
        )

        if cli_utils.check_exist_file(path_image, label="Singularity image"):
            break
        arg_image = None

    # C-PAC patching

    while True:
        if arg_cpac is not None:
            patch_cpac = True
            path_cpac = pl.Path(arg_cpac)
        else:
            cpac_opt: str = click.prompt(
                cli_utils.icon_message(icons.ICON_CPAC, "C-PAC directory (empty to use image version)"),
                default="",
                type=str,
            )
            if len(cpac_opt) == 0:
                patch_cpac = False
                path_cpac = pl.Path()
            else:
                patch_cpac = True
                path_cpac = pl.Path(cpac_opt)

        if not patch_cpac or utils.cpac_dir_valid(path_cpac):
            break
        click.secho(f'Error: Not a valid cpac dir! "{path_cpac}"', fg="red")

    # Input directory

    while True:
        path_input = pl.Path(
            cli_utils.option_or_prompt(
                opt=arg_input,
                prompt=cli_utils.icon_message(icons.ICON_FOLDER, "Input directory"),
            ),
        )

        if cli_utils.check_exist_dir(path_input, label="Input"):
            break

    # Subjects

    while True:
        if arg_subject is None:
            subjects = [path.stem for path in path_input.iterdir() if path.is_dir()]

            subjects = re.split(
                r"\s+",
                click.prompt(
                    cli_utils.icon_message(icons.ICON_SUBJECT, "Subjects (separate with space)"),
                    default=" ".join(subjects),
                ),
            )

        else:
            subjects = re.split(r"\s+", arg_subject)

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
        cli_utils.option_or_prompt(
            opt=arg_output,
            prompt=cli_utils.icon_message(icons.ICON_FOLDER, "Output directory"),
            default=str(consts.PSC_OUTPUT_DEFAULT),
        ),
    )

    # Pipeline configs

    pipeline_ids = re.split(
        r"\s+",
        cli_utils.option_or_prompt(
            opt=arg_pipeline,
            prompt=cli_utils.icon_message(icons.ICON_PIPELINE, "Pipelines (separate with space)"),
            default=consts.ID_PIPELINE_DEFAULT,
        ),
    )

    preconfig_ids: list[str] = []
    pipeline_config_files: list[str] = []
    for pipe in pipeline_ids:
        if pipe in consts.CPAC_PRECONFIGS:
            preconfig_ids.append(pipe)
        else:
            pipeline_config_files.append(pipe)
            if not pl.Path(pipe).exists():
                click.secho(f'Error: Pipeline config file does not exist! "{pipe}"', fg="red")
                return

    if len(preconfig_ids) > 0 and len(pipeline_config_files) > 0:
        click.secho(
            f"Error: Can not mix preconfigs and pipeline config files!\n"
            f"Preconfigs: {utils.bullet_str_list(preconfig_ids)}\n"
            f"Pipeline config files: {utils.bullet_str_list(pipeline_config_files)}",
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
        analysis_level = cli_utils.option_or_prompt(
            opt=arg_analysis_level,
            prompt=icons.ICON_ANALYSIS_LEVEL + click.style(f" Analysis level {consts.CPAC_ANALYSIS_LEVELS}", fg="blue"),
            default=consts.ANALYSIS_LEVEL_DEFAULT,
        )

        if analysis_level in consts.CPAC_ANALYSIS_LEVELS:
            break

        click.secho(
            f'Error: Analysis level invalid ({analysis_level})\nMust be one of: "{consts.CPAC_ANALYSIS_LEVELS}"',
            fg="red",
        )

    # Save C-PAC working dir

    save_working_dir = cli_utils.option_or_confirm(
        opt=utils.option_truthy(arg_save_working_dir),
        default=False,
        prompt=cli_utils.icon_message(icons.ICON_SAVE, "Save working directory"),
    )

    # Extra cpac args

    extra_cpac_args = cli_utils.option_or_prompt(
        opt=arg_extra_cpac_args,
        prompt=cli_utils.icon_message(icons.ICON_EXTRA_ARGS, "Extra args to pass to C-PAC?"),
        default="",
    )

    # Reconstruct ecpac cli call

    reargs: list[str] = ["ecpac"]
    reargs.extend(["--input", str(path_input)])
    reargs.extend(["--output", str(path_output)])
    reargs.extend(["--image", str(path_image)])
    reargs.extend(["--subject", " ".join(subjects)])
    reargs.extend(["--pipeline", " ".join(pipeline_ids)])
    reargs.extend(["--analysis_level", analysis_level])
    if patch_cpac:
        reargs.extend(["--cpac", str(path_cpac)])
    reargs.extend(["--memory_gb", str(res_memory_gb)])
    reargs.extend(["--threads", str(res_threads)])
    reargs.extend(["--duration_h", str(res_duration.total_seconds() / 3600)])
    if save_working_dir:
        reargs.extend(["--save_working_dir"])
    if len(extra_cpac_args) > 0:
        reargs.extend(["--extra_cpac_args", extra_cpac_args])

    # Plan out dirs and job files

    fs_plans: list[FsPlan] = []
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

        extra_args: list[str] = [extra_cpac_args]
        if save_working_dir:
            extra_args.append(f"--save_working_dir {path_out_wd.absolute()}")

        before_run = None
        after_run = None
        if slack.slack_webhook_available():
            before_run = [
                slack.slack_message_bash_mrkdwn(
                    f"Starting ecpac run:\n"
                    f"- Run: `{run_id}`\n"
                    f"- Pipeline: `{pipe_id}`\n"
                    f"- Subject: `{sub}`\n"
                    f"- Input: `{path_input.absolute()}`\n"
                    f"- Output: `{path_out.absolute()}`\n"
                    f"- Image: `{path_image.absolute()}`\n"
                    f"- Threads: {res_threads}\n"
                    f"- Memory: {res_memory_gb} GB\n"
                    f"- Analysis level: `{analysis_level}`",
                )
            ]
            after_run = [
                slack.slack_message_bash_mrkdwn(
                    f"Finished ecpac run:\n"
                    f"- Run: `{run_id}`\n"
                    f"- Pipeline: `{pipe_id}`\n"
                    f"- Subject: `{sub}`\n"
                    f"- Analysis level: `{analysis_level}`\n"
                    f"- Output: `{path_out.absolute()}`\n",
                )
            ]

        # Adjust ressources for ACCESS limits
        # - ACCESS fixes total memory to 2GB per thread
        # - Let's also keep 1 thread + 1GB free for the system
        # - Also ACCESS uses 1000MB per GB

        if res_memory_gb > (2 * res_threads):  # Memory bound
            job_threads = max(math.ceil(res_memory_gb / 2), 2)
            cpac_threads = max(res_threads - 1, 1)

            # Warn user
            click.secho(
                f"Warning: Job is memory-bound, increased job threads to {job_threads}. "
                f"(C-PAC will get {cpac_threads}.)",
                fg="yellow",
            )

        else:  # Thread bound
            job_threads = res_threads
            cpac_threads = max(res_threads - 1, 1)

        job_memory_gb = res_memory_gb
        cpac_memory_gb = max(res_memory_gb - 1, 1)

        job = bash_builder.job_template(
            job_name=f"{run_id}_{pipe_id}_{sub}",
            job_stdout_file=path_stdout_log.absolute(),
            job_duration_limit=res_duration,
            job_threads=job_threads,
            job_memory_gb=job_memory_gb,
            wd=path_out.absolute(),
            path_input=path_input.absolute(),
            path_output=path_out_full.absolute(),
            cpac_threads=cpac_threads,
            cpac_memory_gb=cpac_memory_gb,
            path_image=path_image.absolute(),
            analysis_level=analysis_level,
            subject=sub,
            pipeline=pipe,
            pipeline_is_preconfig=use_preconfigs,
            cpac_sources=path_cpac.absolute() if patch_cpac else None,
            extra_cpac_args=" ".join(extra_args),
            before_run=before_run,
            after_run=after_run,
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

    sbatches = "\n".join([shlex.join(["sbatch", str(j.absolute())]) for j in job_paths])
    executor = f"#!/usr/bin/bash\n{sbatches}"
    path_executor = path_output / run_id / "run.sh"

    fs_plans.append(
        FsPlan(
            path=path_executor,
            is_file=True,
            contents_text=executor,
            make_executable=True,
        ),
    )

    # Add reproducible ecpac call
    fs_plans.append(
        FsPlan(
            path=path_output / run_id / "ecpac_call.sh",
            is_file=True,
            contents_text=f"{bash_builder.SCHEBANG}\n{shlex.join(reargs)}",
            make_executable=True,
        ),
    )

    # User sanity check

    click.secho(icons.ICON_FOLDER + " The following directories and files will be created:", bg="blue")

    fs_plans = sorted(fs_plans, key=lambda i: i.path.absolute().as_posix())

    for plan in fs_plans:
        label_type = "F" if plan.is_file else "D"
        label_executable = "x" if plan.make_executable else " "
        style_fg = "green" if plan.is_file else "blue"
        click.secho(f" - [{label_type}{label_executable}] {plan.path}", fg=style_fg)

    if click.confirm(cli_utils.icon_message(icons.ICON_PREVIEW, "Preview example job?"), default=False):
        print(example_job)

    if not click.confirm(cli_utils.icon_message_emph(icons.ICON_SAVE, "Create files + folders?"), default=None):
        return

    for plan in fs_plans:
        plan.apply()

    if click.confirm(cli_utils.icon_message_emph(icons.ICON_LAUNCH, "Launch now?"), default=None):
        subprocess.run([path_executor], shell=True, check=False)  # noqa: S602

        click.secho("Jobs were executed!", bg="blue")
        click.secho("Some commands you might find helpful:", fg="blue")
        click.secho("  Follow job output:", fg="blue")
        click.secho(shlex.join(["tail", "-f", str(example_path_stdout_log)]), fg="blue")
        click.secho("  List all running jobs:", fg="blue")
        click.secho("squeue --me")


if __name__ == "__main__":
    main()
