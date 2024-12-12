from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal

from sirocco.core.graph_items import Task
from sirocco.parsing._yaml_data_models import ConfigIconTask, ConfigIconTaskCore


@dataclass
class IconTask(ConfigIconTaskCore, Task):
    plugin: ClassVar[Literal[ConfigIconTask.plugin]] = ConfigIconTask.plugin
