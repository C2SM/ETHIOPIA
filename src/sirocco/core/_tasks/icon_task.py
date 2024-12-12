from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Literal

from sirocco.core.graph_items import Task
from sirocco.parsing._yaml_data_models import ConfigIconTask


@dataclass
class IconTask(Task):
    plugin: ClassVar[Literal[ConfigIconTask.plugin]] = ConfigIconTask.plugin

    namelists: dict = field(default_factory=dict)
