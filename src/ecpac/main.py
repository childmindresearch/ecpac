import dataclasses
import itertools
import os
import pathlib as pl
import stat
import subprocess
from datetime import datetime, timedelta
from typing import Optional, List, Union

import click

ID_PROJECT = 'med220004p'
USER_NAME = os.getlogin()
ID_PIPELINE_DEFAULT = 'cpac-default-pipeline'
FILENAME_JOB = 'job.sh'
FOLDERNAME_OUTPUT = 'output'

PSC_PROJECT = pl.Path('/ocean/projects') / ID_PROJECT
PSC_PROJECT_USER = PSC_PROJECT / USER_NAME
PSC_OUTPUT_DEFAULT = PSC_PROJECT_USER / 'ecpac_runs'
PSC_IMAGE_DEFAULT = PSC_PROJECT_USER / 'images/cpac.sif'


@dataclasses.dataclass
class FsPlan:
    """Planned file system change"""
    path: pl.Path
    is_file: bool = False
    contents_text: Optional[str] = None
    make_executable: bool = False

    def apply(self):
        if self.is_file:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            txt = '' if self.contents_text is None else self.contents_text
            with open(self.path, 'w', encoding='utf-8') as handle:
                handle.write(txt)

            if self.make_executable:
                self.path.chmod(self.path.stat().st_mode | stat.S_IEXEC)
        else:
            self.path.mkdir(parents=True, exist_ok=True)


def _bullet_str_list(list_: list):
    return '\n'.join([f' - {i}' for i in list_])


def _cli_check_exist_file(path: pl.Path, label: str = ''):
    if path.exists() and path.is_file():
        return True
    click.secho(f'Error: {label} file does not exist! "{path}"', fg='red')
    return False


def _cli_check_exist_dir(path: pl.Path, label: str = ''):
    if path.exists() and path.is_dir():
        return True
    click.secho(f'Error: {label} directory does not exist! "{path}"', fg='red')
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
    return opt_lower == 'true' or opt_lower == 'y' or opt_lower == 'yes' or opt_lower == '1'


def timedelta_to_hms(t: timedelta) -> str:
    s = t.total_seconds()
    return f'{s // 3600:02.0f}:{s % 3600 // 60:02.0f}:{s % 60:02.0f}'


def _cpac_dir_valid(path: Union[str, os.PathLike]) -> bool:
    p = pl.Path(path)
    return p.exists() and \
        (p / 'dev/docker_data/run.py').exists() and \
        (p / 'dev/docker_data/run-with-freesurfer.sh').exists()


@click.command()
@click.option('-i', '--input', 'arg_input', type=str, help='Input directory.')
@click.option('-o', '--output', 'arg_output', type=str)
@click.option('-r', '--run', 'arg_run', type=str, help='Run name.')
@click.option('-g', '--image', 'arg_image', type=str)
@click.option('-s', '--subject', 'arg_subject', type=str)
@click.option('-p', '--pipeline', 'arg_pipeline', type=str)
@click.option('-c', '--cpac', 'arg_cpac', type=str)
@click.option('-m', '--memory_gb', 'arg_memory_gb', type=str)
@click.option('-t', '--threads', 'arg_threads', type=str)
@click.option('-d', '--duration_h', 'arg_duration_h', type=str)
@click.option('-w', '--save_working_dir', 'arg_save_working_dir', type=str)
@click.option('-x', '--extra_cpac_args', 'arg_extra_cpac_args', type=str)
def main(
        arg_input: Optional[str] = None,
        arg_output: Optional[str] = None,
        arg_run: Optional[str] = None,
        arg_image: Optional[str] = None,
        arg_subject: Optional[str] = None,
        arg_pipeline: Optional[str] = None,
        arg_cpac: Optional[str] = None,
        arg_memory_gb: Optional[str] = None,
        arg_threads: Optional[str] = None,
        arg_duration_h: Optional[str] = None,
        arg_save_working_dir: Optional[str] = None,
        arg_extra_cpac_args: Optional[str] = None
):
    if not PSC_PROJECT_USER.exists():
        click.secho(f'Error: User directory does not exist! "{PSC_PROJECT_USER}" (This script is meant to run on PSC)',
                    fg='red')
        if not click.confirm(click.style('Continue anyway?', fg='red'), default=False):
            return

    # Run name

    run_id = option_or_prompt(
        opt=arg_run,
        prompt=click.style('Run name', fg='blue'),
        default=datetime.now().strftime("run_%y-%m-%d_%H-%M-%S")
    )

    # Resources

    res_threads = int(option_or_prompt(
        opt=arg_threads,
        prompt=click.style('Number of threads/cores (int)', fg='blue'),
        default=str(8)
    ))

    res_memory_gb = float(option_or_prompt(
        opt=arg_memory_gb,
        prompt=click.style('Memory (GB, float) (can not be more than 2*threads on PSC)', fg='blue'),
        default=f'{2 * res_threads:.1f}'
    ))

    res_duration = timedelta(hours=float(option_or_prompt(
        opt=arg_duration_h,
        prompt=click.style('Duration (hours, float)', fg='blue'),
        default=f'{48.0:.1f}'
    )))

    # Image

    while True:
        path_image = pl.Path(option_or_prompt(
            opt=arg_image,
            prompt=click.style('Image file', fg='blue'),
            default=str(PSC_IMAGE_DEFAULT)
        ))

        if _cli_check_exist_file(path_image, label='Singularity image'):
            break

    # C-PAC patching

    while True:
        if arg_cpac is not None:
            patch_cpac = True
            path_cpac = pl.Path(arg_cpac)
        else:
            cpac_opt: str = click.prompt(click.style('C-PAC directory (empty to use image version)', fg='blue'),
                                         default='',
                                         type=str)
            if len(cpac_opt) == 0:
                patch_cpac = False
                path_cpac = pl.Path()
            else:
                patch_cpac = True
                path_cpac = pl.Path(cpac_opt)

        if not patch_cpac or _cpac_dir_valid(path_cpac):
            break
        else:
            click.secho(f'Error: Not a valid cpac dir! "{path_cpac}"', fg='red')

    # Input directory

    while True:
        path_input = pl.Path(option_or_prompt(
            opt=arg_input,
            prompt=click.style('Input directory', fg='blue')
        ))

        if _cli_check_exist_dir(path_input, label='Input'):
            break

    # Subjects

    if arg_subject is None:
        subjects = [path.stem for path in path_input.iterdir() if path.is_dir()]

        subjects = click.prompt(
            click.style(f'Subjects (separate with space)', fg='blue'),
            default=' '.join(subjects)
        ).split(' ')

    else:
        subjects = arg_subject.split(' ')

        for sub in subjects:
            if not (path_input / sub).exists():
                return

    # Output directory

    path_output = pl.Path(option_or_prompt(
        opt=arg_output,
        prompt=click.style('Output directory', fg='blue'),
        default=str(PSC_OUTPUT_DEFAULT)
    ))

    # Pipeline configs

    pipeline_ids = option_or_prompt(
        opt=arg_pipeline,
        prompt=click.style('Pipelines (separate with space)', fg='blue'),
        default=ID_PIPELINE_DEFAULT
    ).split(' ')

    # Save C-PAC working dir

    save_working_dir = option_or_confirm(
        opt=option_truthy(arg_save_working_dir),
        default=False,
        prompt=click.style('Save working directory', fg='blue')
    )

    # Extra cpac args

    extra_cpac_args = option_or_prompt(
        opt=arg_extra_cpac_args,
        prompt=click.style('Extra args to pass to C-PAC? (E.g. --save_pipeline)', fg='blue'),
        default=''
    )

    # Plan out dirs and job files

    fs_plans: List[FsPlan] = []
    job_paths = []
    example_job = None
    for pipe, sub in itertools.product(pipeline_ids, subjects):
        path_out = path_output / run_id / pipe / sub
        path_out_full = path_out / 'output'
        path_out_wd = path_out / 'wd'
        path_job = path_out / "run_job.sh"
        path_stdout_log = path_out / "out.log"

        extra_args: List[str] = [extra_cpac_args]
        if save_working_dir:
            extra_args.append(f'--save_working_dir {path_out_wd.absolute()}')

        job = BASH_TEMPLATE_JOB.format(
            job_name=f'{run_id}_{pipe}_{sub}',
            stdout_file=path_stdout_log,
            cpac_bin_opt='' if not patch_cpac else BASH_TEMPLATE_JOB_CPAC_BIN.format(cpac_bin=path_cpac.absolute()),
            wd=path_out.absolute(),
            subject=sub,
            pipeline=pipe,
            path_input=(path_input / sub).absolute(),
            path_output=path_out_full.absolute(),
            image=path_image.absolute(),
            threads=res_threads,
            duration_str=timedelta_to_hms(res_duration),
            memory_mb=int(res_memory_gb * 1024),
            cpac_threads=max(res_threads - 1, 1),
            cpac_memory_gb=max(res_memory_gb - 1, 1),
            extra_cpac_args=' '.join(extra_args)
        )

        fs_plans.append(FsPlan(path=path_job, is_file=True, contents_text=job, make_executable=True))
        fs_plans.append(FsPlan(path=path_out_full, is_file=False))
        if save_working_dir:
            fs_plans.append(FsPlan(path=path_out_wd, is_file=False))

        job_paths.append(path_job)

        if example_job is None:
            example_job = job

    # Plan executor file

    sbatches = "\n".join([f'sbatch {j}' for j in job_paths])
    executor = f'#!/usr/bin/bash\n{sbatches}'
    path_executor = path_output / run_id / 'run.sh'

    fs_plans.append(FsPlan(path=path_executor, is_file=True, contents_text=executor, make_executable=True))

    # User sanity check

    click.secho(f'The following directories and files will be created:', bg='blue')

    fs_plans = sorted(fs_plans, key=lambda i: i.path.absolute().as_posix())

    for plan in fs_plans:
        label_type = "F" if plan.is_file else "D"
        label_executable = 'x' if plan.make_executable else ' '
        style_fg = 'green' if plan.is_file else 'blue'
        click.secho(f' - [{label_type}{label_executable}] {plan.path}', fg=style_fg)

    if click.confirm(
            click.style('Preview example job?', fg='blue'),
            default=False
    ):
        print(example_job)

    if not click.confirm(
            click.style('Create files + folders?', bg='blue'), default=None
    ):
        return

    for plan in fs_plans:
        plan.apply()

    if click.confirm(
            '\U0001f680' + click.style('Launch now?', bg='blue'), default=None
    ):
        subprocess.run([path_executor], shell=True)


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
{image} {path_input} {path_output} participant \
--skip_bids_validator \
--n_cpus {cpac_threads} \
--mem_gb {cpac_memory_gb} \
--participant_label {subject} \
--preconfig {pipeline} \
{extra_cpac_args} \
"""
# --save_working_dir \


BASH_TEMPLATE_JOB_CPAC_BIN = """\
-B {cpac_bin}:/code \
-B {cpac_bin}/dev/docker_data/run.py:/code/run.py \
-B {cpac_bin}/dev/docker_data/run-with-freesurfer.sh:/code/run-with-freesurfer.sh \
"""

if __name__ == '__main__':
    main()
