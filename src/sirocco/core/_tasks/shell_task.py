from __future__ import annotations

from dataclasses import field, dataclass
from typing import ClassVar

from sirocco.core.graph_items import Task


@dataclass
class ShellTask(Task):
    plugin: ClassVar[str] = "shell"

    command: str | None = None
    command_option: str | None = None
    input_arg_options: dict[str, str] = field(default_factory=dict) 
    src: str | None = None
