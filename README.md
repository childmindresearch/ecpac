# `ecpac`: Easy C-PAC execution on PSC ACCESS

[![Build](https://github.com/cmi-dair/ecpac/actions/workflows/test.yaml/badge.svg?branch=main)](https://github.com/cmi-dair/ecpac/actions/workflows/test.yaml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/cmi-dair/ecpac/branch/main/graph/badge.svg?token=22HWWFWPW5)](https://codecov.io/gh/cmi-dair/ecpac)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![stability-stable](https://img.shields.io/badge/stability-stable-green.svg)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/cmi-dair/ecpac/blob/main/LICENSE)
[![pages](https://img.shields.io/badge/api-docs-blue)](https://cmi-dair.github.io/ecpac)

## Install (first time only)

Create a conda environment on PSC ACCESS:

```sh
module load anaconda3/2022.10
conda create -n ecpac python=3.11
conda activate ecpac
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

## Slack notifications

To enable Slack notifications, create a Slack app and create a webhook URL. Then, set the following environment variable:

```sh
SLACK_WEBHOOK_URL=...
```
