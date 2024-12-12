from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal

from sirocco.core.graph_items import Task
from sirocco.parsing._yaml_data_models import ConfigShellTask, ConfigShellTaskCore


@dataclass
class ShellTask(ConfigShellTaskCore, Task):
    plugin: ClassVar[Literal[ConfigShellTask.plugin]] = ConfigShellTask.plugin
