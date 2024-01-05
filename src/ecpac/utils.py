import datetime
import os
import pathlib as pl
import re
from typing import Optional, Union


def filesafe(f: str) -> str:
    """Convert a string to a file-safe string."""
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", f)


def option_truthy(opt: Optional[str]) -> Optional[bool]:
    """
    Convert a string option to a boolean option.
    Common truthy values like "true", "y", "yes", and "1" are converted to True.
    None is converted to None.
    All other values are converted to False.
    """
    if opt is None:
        return None
    opt_lower = opt.lower()
    return opt_lower == "true" or opt_lower == "y" or opt_lower == "yes" or opt_lower == "1"


def timedelta_to_hms(t: datetime.timedelta) -> str:
    """Convert a timedelta to a string in the format HH:MM:SS."""
    s = t.total_seconds()
    return f"{s // 3600:02.0f}:{s % 3600 // 60:02.0f}:{s % 60:02.0f}"


def bullet_str_list(list_: list) -> str:
    """Convert a list of strings to a bulleted string."""
    return "\n".join([f" - {i}" for i in list_])


def cpac_dir_valid(path: Union[str, os.PathLike]) -> bool:
    """Check if a directory is a valid C-PAC source code directory."""
    p = pl.Path(path)
    return (
        p.exists()
        and (p / "dev/docker_data/run.py").exists()
        and (p / "dev/docker_data/run-with-freesurfer.sh").exists()
    )


def bridges_gb_to_mb(gb: float | int) -> float | int:
    """ACCESS/Bridges uses 1000 MB per GB instead of 1024 MB per GB."""
    return gb * 1000
