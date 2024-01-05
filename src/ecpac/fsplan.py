"""File system plan. Used to preview and apply changes to the file system."""

import dataclasses
import pathlib as pl
import stat


@dataclasses.dataclass
class FsPlan:
    """Planned file system change."""

    path: pl.Path
    is_file: bool = False
    contents_text: str | None = None
    make_executable: bool = False

    def apply(self) -> None:
        """Apply the file system change."""
        if self.is_file:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            txt = "" if self.contents_text is None else self.contents_text
            with self.path.open("w", encoding="utf-8") as handle:
                handle.write(txt)

            if self.make_executable:
                self.path.chmod(self.path.stat().st_mode | stat.S_IEXEC)
        else:
            self.path.mkdir(parents=True, exist_ok=True)
