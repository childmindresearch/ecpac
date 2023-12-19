import pathlib as pl
from typing import Optional

import click


def check_exist_file(path: pl.Path, label: str = "") -> bool:
    """Check if a file exists. Or print a message if it doesn't."""
    if path.exists() and path.is_file():
        return True
    click.secho(f'Error: {label} file does not exist! "{path}"', fg="red")
    return False


def check_exist_dir(path: pl.Path, label: str = "") -> bool:
    """Check if a directory exists. Or print a message if it doesn't."""
    if path.exists() and path.is_dir():
        return True
    click.secho(f'Error: {label} directory does not exist! "{path}"', fg="red")
    return False


def option_or_prompt(opt: Optional[str], prompt: str, default: Optional[str] = None) -> str:
    """Prompt the user for input if the option is not provided."""
    if opt is not None:
        return opt
    return click.prompt(prompt, default=default, type=str)


def option_or_confirm(opt: Optional[bool], prompt: str, default: Optional[bool] = False) -> bool:
    """Prompt the user for input (confirmation boolean) if the option is not provided."""
    if opt is not None:
        return opt
    return click.confirm(prompt, default=default)
