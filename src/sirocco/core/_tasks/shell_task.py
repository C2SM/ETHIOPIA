from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from sirocco.core.graph_items import Task


@dataclass
class ShellTask(Task):
    plugin: ClassVar[str] = "shell"

    command: str | None = None
    command_option: str | None = None
    input_arg_options: dict[str, str] | None = None
    src: str | None = None
