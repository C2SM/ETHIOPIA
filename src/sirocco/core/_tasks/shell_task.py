from __future__ import annotations

from dataclasses import dataclass

from sirocco.core.graph_items import Task
from sirocco.parsing._yaml_data_models import ConfigShellTask, ConfigShellTaskCore


@dataclass
class ShellTask(ConfigShellTaskCore, Task, plugin_name=ConfigShellTask.plugin):
    pass
