"""Cli utilities."""

import pathlib as pl

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


def option_or_prompt(opt: str | None, prompt: str, *, default: str | None = None) -> str:
    """Prompt the user for input if the option is not provided."""
    if opt is not None:
        return opt
    return click.prompt(prompt, default=default, type=str)


def option_or_confirm(opt: bool | None, prompt: str, *, default: bool | None = False) -> bool:
    """Prompt the user for input (confirmation boolean) if the option is not provided."""
    if opt is not None:
        return opt
    return click.confirm(prompt, default=default)
