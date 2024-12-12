from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal

from sirocco.core.graph_items import Task
from sirocco.parsing._yaml_data_models import ConfigShellTask


@dataclass
class ShellTask(Task):
    plugin: ClassVar[Literal[ConfigShellTask.plugin]] = ConfigShellTask.plugin

    command: str | None = None
    command_option: str | None = None
    input_arg_options: dict[str, str] | None = None
    src: str | None = None
