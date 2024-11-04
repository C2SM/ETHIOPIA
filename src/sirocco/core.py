from __future__ import annotations
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING, TypeVar, Generic

from datetime import datetime

from sirocco.parsing._yaml_data_models import (
    _DataBaseModel,
    ConfigCycleTaskDepend,
    ConfigCycleTask,
    ConfigCycleTaskInput,
    ConfigData,
    ConfigTask,
    ConfigWorkflow,
    load_workflow_config,
)

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable, Iterator
type ConfigCycleSpec = ConfigCycleTaskDepend | ConfigCycleTaskInput
TimeSeriesObject = TypeVar('TimeSeriesObject')

light_red = '\x1b[91m'
light_green = '\x1b[92m'
light_blue = '\x1b[94m'
bold = '\x1b[1m'
reset = '\x1b[0m'


class NodeStr:

    def __str__(self):
        ret_str = f"{self.color}{bold}{self.name}{reset}"
        if self.date is not None:
            ret_str += f" {self.color}[{self.date}]"
        return ret_str + f"{reset}"


class Task(NodeStr):
    """Internal representation of a task node"""

    color: str = light_red

    name: str
    outputs: list[Data]
    inputs: list[Data]
    wait_on: list[Task]
    date: datetime | None = None
    # TODO This list is too long. We should start with the set of supported
    #      keywords and extend it as we support more
    command: str | None = None
    command_option: str | None = None
    input_arg_options: dict[str, str] | None = None
    host: str | None = None
    account: str | None = None
    plugin: str | None = None
    config: str | None = None
    uenv: dict | None = None
    nodes: int | None = None
    walltime: str | None = None
    src: str | None = None
    conda_env: str | None = None

    def __init__(self,
                 config: ConfigTask,
                 task_ref: ConfigCycleTask,
                 workflow: Workflow,
                 date: datetime | None = None):
        self.name = config.name
        self.date = date
        self.inputs = []
        self.outputs = []
        self.wait_on = []
        self.workflow = workflow
        # Long list of not always supported keywords
        self.command = config.command
        self.command_option = config.command_option
        self.input_arg_options = config.input_arg_options
        self.host = config.host
        self.account = config.account
        self.plugin = config.plugin
        self.config = config.config
        self.uenv = config.uenv
        self.nodes = config.nodes
        self.walltime = config.walltime
        self.src = config.src
        self.conda_env = config.conda_env

        for input_spec in task_ref.inputs:
            for data in workflow.data.get(input_spec, self.date):
                if data is not None:
                    self.inputs.append(data)
        for output_spec in task_ref.outputs:
            self.outputs.append(self.workflow.data[output_spec.name, self.date])
        # Store for actual linking in link_wait_on_tasks() once all tasks are created
        self._wait_on_specs = task_ref.depends

    def link_wait_on_tasks(self):
        for wait_on_spec in self._wait_on_specs:
            for task in self.workflow.tasks.get(wait_on_spec, self.date):
                if task is not None:
                    self.wait_on.append(task)


@dataclass(kw_only=True)
class Data(NodeStr):
    """Internal representation of a data node"""

    color: str = light_blue
    name: str
    type: str
    src: str
    available: bool
    date: datetime | None = None

    @classmethod
    def from_config(cls, config: _DataBaseModel, *, date: datetime = None):
        return cls(
            name=config.name,
            type=config.type,
            src=config.src,
            available=config.available,
            date=date,
        )


@dataclass(kw_only=True)
class Cycle(NodeStr):
    """Internal reprenstation of a cycle"""

    color: str = light_green
    name: str
    tasks: list[Task]
    date: datetime | None = None


class TimeSeries(Generic[TimeSeriesObject]):
    """Dictionnary of objects accessed by date, checking start and end dates"""

    def __init__(self) -> None:
        self.start_date: datetime | None = None
        self.end_date: datetime | None = None
        self._dict: dict[str: TimeSeriesObject] = {}

    def __setitem__(self, date: datetime, data: TimeSeriesObject) -> None:
        if date in self._dict.keys():
            raise KeyError(f"date {date} already used, cannot set twice")
        self._dict[date] = data
        if self.start_date is None:
            self.start_date = date
            self.end_date = date
        elif date < self.start_date:
            self.start_date = date
        elif date > self.end_date:
            self.end_date = date

    def __getitem__(self, date: datetime) -> TimeSeriesObject:
        if date < self.start_date or date > self.end_date:
            # TODO proper logging
            item = next(iter(self._dict.values()))
            print(f"WARNING: date {date} for item {item.name} is out of bounds [{self.start_date} - {self.end_date}], ignoring.")
            return None
        if date not in self._dict:
            msg = f"date {date} not found"
            raise KeyError(msg)
        return self._dict[date]


# TODO metaclass to generate stores of specific data type (avoid `Any`)
class Store(Generic[TimeSeriesObject]):
    """Container for TimeSeries or unique data"""

    def __init__(self):
        self._dict: dict[str, TimeSeries | TimeSeriesObject] = {}

    def __setitem__(self, key: str | tuple(str, datetime|None), value: TimeSeriesObject) -> None:
        if isinstance(key, tuple):
            name, date = key
        else:
            name, date = key, None
        if name in self._dict:
            if not isinstance(self._dict[name], TimeSeries):
                raise KeyError(f"single entry {name} already set")
            if date is None:
                raise KeyError(f"entry {name} is a TimeSeries, must be accessed by date")
            self._dict[name][date] = value
        else:
            if date is None:
                self._dict[name] = value
            else:
                self._dict[name] = TimeSeries()
                self._dict[name][date] = value

    def __getitem__(self, key: str | tuple(str, datetime|None)) -> TimeSeriesObject:
        if isinstance(key, tuple):
            name, date = key
        else:
            name, date = key, None

        if name not in self._dict:
            raise KeyError(f"entry {name} not found in Store")
        if isinstance(self._dict[name], TimeSeries):
            if date is None:
                raise KeyError(f"entry {name} is a TimeSeries, must be accessed by date")
            return self._dict[name][date]
        else:
            if date is not None:
                raise KeyError(f"entry {name} is not a TimeSeries, cannot be accessed by date")
            return self._dict[name]

    def get(self, spec: ConfigCycleSpec, ref_date: datetime|None = None) -> Iterator(TimeSeriesObject):
        name = spec.name
        if isinstance(self._dict[name], TimeSeries):
            if ref_date is None and spec.date is []:
                raise ValueError("TimeSeries object must be referenced by dates")
            for target_date in spec.resolve_target_dates(ref_date):
                yield self._dict[name][target_date]
        else:
            if spec.lag or spec.date:
                raise ValueError(f"item {name} is not a TimeSeries, cannot be referenced via date or lag")
            yield self._dict[name]

    def values(self) -> Iterator[Any]:
        for item in self._dict.values():
            if isinstance(item, TimeSeries):
                for subitem in item._dict.values():
                    yield subitem
            else:
                yield item


class Workflow:
    """Internal reprensentation of a worflow"""

    def __init__(self, workflow_config: ConfigWorkflow) -> None:
        self.tasks = Store()
        self.data = Store()
        self.cycles = Store()

        # 1 - create availalbe data nodes
        for data_config in workflow_config.data.available:
            self.data[data_config.name] = Data.from_config(data_config, date=None)

        # 2 - create output data nodes
        for cycle_config in workflow_config.cycles:
            for date in cycle_config.dates():
                for task_ref in cycle_config.tasks:
                    for data_ref in task_ref.outputs:
                        data_name = data_ref.name
                        data_config = workflow_config.data_dict[data_name]
                        self.data[data_name, date] = Data.from_config(data_config, date=date)

        # 3 - create cycles and tasks
        for cycle_config in workflow_config.cycles:
            cycle_name = cycle_config.name
            for date in cycle_config.dates():
                cycle_tasks = []
                for task_ref in cycle_config.tasks:
                    task_name = task_ref.name
                    task_config = workflow_config.task_dict[task_name]
                    self.tasks[task_name, date] = (task := Task(task_config, task_ref, workflow=self, date=date))
                    cycle_tasks.append(task)
                self.cycles[cycle_name, date] = Cycle(name=cycle_name, tasks=cycle_tasks, date=date)

        # 4 - Link wait on tasks
        for task in self.tasks.values():
            task.link_wait_on_tasks()

    def __str__(self):
        ind = ''
        lines = []
        lines.append(f"{ind}cycles:")
        ind += '  '
        for cycle in self.cycles.values():
            lines.append(f"{ind}- {cycle}:")
            ind += '    '
            lines.append(f"{ind}tasks:")
            ind += '  '
            for task in cycle.tasks:
                lines.append(f"{ind}- {task}:")
                ind += '    '
                if task.inputs:
                    lines.append(f"{ind}input:")
                    ind += '  '
                    for data in task.inputs:
                        lines.append(f"{ind}- {data}")
                    ind = ind[:-2]
                if task.outputs:
                    lines.append(f"{ind}output:")
                    ind += '  '
                    for data in task.outputs:
                        lines.append(f"{ind}- {data}")
                    ind = ind[:-2]
                if task.wait_on:
                    lines.append(f"{ind}wait on:")
                    ind += '  '
                    for task in task.wait_on:
                        lines.append(f"{ind}- {task}")
                    ind = ind[:-2]
                ind = ind[:-4]
            ind = ind[:-4]
            ind = ind[:-2]
        ind = ind[:-2]
        return '\n'.join(lines)

    @classmethod
    def from_yaml(cls, config_path: str):
        return cls(load_workflow_config(config_path))
