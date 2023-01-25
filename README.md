# `ecpac`: Easy C-PAC execution on SLURM clusters

## Install

```sh
python3 -m venv ecpac
source ecpac/bin/activate
pip install git+https://github.com/nx10/ecpac.git
```

## Run

```sh
source ecpac/bin/activate  # If not already activated
ecpac # or: 'ecpac --help' for non-interactive use 
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