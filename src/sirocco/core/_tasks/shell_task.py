from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
from typing import ClassVar

from sirocco.core.graph_items import Task
# from sirocco.parsing._yaml_data_models import _CliArgsBaseModel


@dataclass
class ShellTask(Task):
    plugin: ClassVar[str] = "shell"

    command: str | None = None
    src: str | Path | None = None
    # cli_arguments: '_CliArgsBaseModel' | None = None
