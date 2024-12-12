from __future__ import annotations

from dataclasses import dataclass

from sirocco.core.graph_items import Task
from sirocco.parsing._yaml_data_models import ConfigShellTaskCore


@dataclass
class ShellTask(ConfigShellTaskCore, Task):
    pass
