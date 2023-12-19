# `ecpac`: Easy C-PAC execution on PSC ACCESS

## Install (first time only)

Create a conda environment on PSC ACCESS:

```sh
module load anaconda3/2022.10
conda create -n ecpac python=3.11
pip install git+https://github.com/cmi-dair/ecpac.git
```

## Run

```sh
module load anaconda3/2022.10
conda activate ecpac
ecpac # or: 'ecpac --help' for non-interactive use 
```

## Update

```sh
module load anaconda3/2022.10
conda activate ecpac
pip uninstall -y ecpac && sleep 2 && pip install git+https://github.com/cmi-dair/ecpac.git
```

## TODO

- Command line option for non-interactive use (fallback to all defaults)
- Support pipeline configs not just presets
- Glob / regex pattern for subjects + pipelines
- Quote paths with whitespace
- More validation
- Patch cpac from git+URL directly
- optionally wrap jobs in hpc_benchmark
- Print full command after interactive use 