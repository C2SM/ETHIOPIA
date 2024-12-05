from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from sirocco.core.graph_items import Task


@dataclass
class IconTask(Task):
    plugin: ClassVar[str] = "icon"

    namelists: dict = field(default_factory=dict)
