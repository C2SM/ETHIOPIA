from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from datetime import datetime

from sirocco.parsing._yaml_data_models import (
    _DataBaseModel,
    ConfigCycleTaskDepend,
    ConfigCycleTask,
    ConfigCycleTaskInput,
    ConfigCycleTaskOutput,
    ConfigData,
    ConfigTask,
    ConfigWorkflow,
    load_workflow_config,
)

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable, Iterator
    type ConfigCycleSpec = ConfigCycleTaskDepend | ConfigCycleTaskInput | ConfigCycleTaskOutput


class Task:
    """Internal representation of a task node"""

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
            self.inputs.append(data for data in workflow.data.get((input_spec, self.date)))
        for output_spec in task_ref.outputs:
            self.outputs.append(self.workflow.data[output_spec.name, self.date])
        # Store for actual linking in link_wait_on_tasks() once all tasks are created
        self._wait_on_specs = task_ref.depends

    def link_wait_on_tasks(self):
        for wait_on_spec in self._wait_on_specs:
            self.wait_on.append(task for task in self.workflow.tasks.get((wait_on_spec, self.date)))


@dataclass(kw_only=True)
class Data:
    """Internal representation of a data node"""

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


class TimeSeries():
    """Dictionnary of objects accessed by date, checking start and end dates"""

    # start_date: datetime | None = None
    # end_date: datetime | None = None
    # _dict: dict[datetime, Any] = {}

    def __init__(self):
        self.start_date = None
        self.end_date = None
        self._dict = {}

    def __setitem__(self, date: datetime, data: Any) -> None:
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

    def __getitem__(self, date: datetime) -> Any:
        if date < self.start_date or date > self.end_date:
            # TODO proper logging
            print(f"WARNING: date {date} is out of bounds, ignoring.")
            return None
        if date not in self._dict:
            msg = f"date {date} not found"
            raise KeyError(msg)
        return self._dict[date]


# TODO metaclass to generate stores of specific data type (avoid `Any`)
class Store:
    """Container for TimeSeries or unique data"""

    def __init__(self):
        self._dict: dict[str, Any] = {}

    def __setitem__(self, key: str | tuple(str, datetime|None), value: Any) -> None:
        if isinstance(key, tuple):
            name, date = key
        else:
            name, date = key, None
        if date is None:
            if name in self._dict:
                raise KeyError(f"single entry {name} already set")
            else:
                self._dict[name] = value
        else:
            if name in self._dict:
                if isinstance(self._dict[name], TimeSeries):
                    self._dict[name][date] = value
                else:
                    raise KeyError(f"entry {name} is a TimeSeries, must be accessed by date")

    def __getitem__(self, key: str | tuple(str, datetime|None)) -> Any:
        if isinstance(key, tuple):
            name, date = key
        else:
            name, date = key, None
        if date is None:
            if name in self._dict:
                if isinstance(self._dict[name], TimeSeries):
                    raise KeyError(f"entry {name} is a TimeSeries, must be accessed by date")
                else:
                    return self._dict[name]
        else:
            if name in self._dict:
                if isinstance(self._dict[name], TimeSeries):
                    return self._dict[name][date]
                else:
                    raise KeyError(f"entry {name} is not a TimeSeries, cannot be accessed  must by date")

    def add(self, key: str | tuple[str, datetime|None], value: Any) -> None:
        if isinstance(key, tuple):
            name, date = key
        else:
            name, date = key, None
        if date is None:
            if name in self._dict:
                if isinstance(self._dict[name], TimeSeries):
                    raise ValueError(f"TimeSeries object requires a date as key")
                raise ValueError(f"{name} already set, cannot set twice")
            self._dict[name] = value
        else:
            if name not in self._dict:
                self._dict[name] = TimeSeries()
            self._dict[name][date] = value

    def get(self, spec: ConfigCycleSpec, ref_date: datetime|None = None) -> Iterator(Any):
        name = spec.name
        if isinstance(self._dict[name], TimeSeries):
            if ref_date is None:
                raise ValueError("TimeSeries object must be referenced by dates")
            else:
                for target_date in spec.resolve_target_dates(ref_date):
                    yield self._dict[name][target_date]
        else:
            if spec.lag or spec.date:
                raise ValueError(f"item {name} is not a TimeSeries, cannot be referenced vis date or lag")
            else:
                yield self._dict[name]

        if ref_date is None:
            if isinstance(self._dict[name], TimeSeries):
                raise ValueError(f"TimeSeries object requires a date as key")
            return self._dict[name]
        else:
            return self._dict[name][date]

    def values(self) -> Iterator[Any]:
        for item in self._dict.values():
            if isinstance(item, TimeSeries):
                for subitem in item._dict.values():
                    yield subitem
            else:
                yield item


@dataclass(kw_only=True)
class Cycle:
    """Internal reprenstation of a cycle"""

    name: str
    tasks: list[Task]
    date: datetime | None = None


class Workflow:
    """Internal reprensentation of a worflow"""

    def __init__(self, workflow_config: ConfigWorkflow) -> None:

        self.tasks = Store()
        self.data = Store()
        self.cycles = {}

        ind = '    '
        # 1 - create availalbe data nodes
        for data_config in workflow_config.data.available:
            self.data.add(data_config.name, Data.from_config(data_config, date=None))

        # 2 - create output data nodes
        for cycle_config in workflow_config.cycles:
            for date in cycle_config.dates():
                for task_ref in cycle_config.tasks:
                    for data_ref in task_ref.outputs:
                        data_name = data_ref.name
                        data_config = workflow_config.data_dict[data_name]
                        self.data.add((data_name, date), Data.from_config(data_config, date=date))

        # 3 - create cycles and tasks
        for cycle_config in workflow_config.cycles:
            cycle_name = cycle_config.name
            for date in cycle_config.dates():
                cycle_tasks = []
                for task_ref in cycle_config.tasks:
                    task_name = task_ref.name
                    task_config = workflow_config.task_dict[task_name]
                    self.tasks.add((task_name, date), task := Task(task_config, task_ref, workflow=self, date=date))
                    cycle_tasks.append(task)
                self.cycles[cycle_name] = Cycle(name=cycle_name, tasks=cycle_tasks, date=date)

        # 4 - Link wait on tasks
        for task in self.tasks.values():
            task.link_wait_on_tasks()

    @classmethod
    def from_yaml(cls, config_path: str):
        return cls(load_workflow_config(config_path))
