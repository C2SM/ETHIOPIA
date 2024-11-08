from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Generic, Literal, Self, TypeVar

from termcolor import colored

from sirocco.parsing._yaml_data_models import (
    ConfigCycleTask,
    ConfigCycleTaskDepend,
    ConfigCycleTaskInput,
    ConfigTask,
    ConfigWorkflow,
    load_workflow_config,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import datetime

    from sirocco.parsing._yaml_data_models import ConfigCycle, DataBaseModel

    type ConfigCycleSpec = ConfigCycleTaskDepend | ConfigCycleTaskInput

logging.basicConfig()
logger = logging.getLogger(__name__)


TimeSeriesObject = TypeVar("TimeSeriesObject")


class NodeStr:
    color: str

    def _str_pretty_(self) -> str:
        repr_str = colored(self.name, self.color, attrs=["bold"])
        if self.date is not None:
            repr_str += colored(f" [{self.date}]", self.color)
        return repr_str

    def __str__(self) -> str:
        if self.date is None:
            return self.name
        return f"{self.name} [{self.date}]"

    def __str__(self):
        ret_str = f"{self.name}"
        if self.date is not None:
            ret_str += f"_{self.date}"
        return ret_str


@dataclass
class Task(NodeStr):
    name: str
    workflow: Workflow
    outputs: list[Data] = field(default_factory=list)
    inputs: list[Data] = field(default_factory=list)
    wait_on: list[Task] = field(default_factory=list)
    date: datetime | None = None
    color: str = "light_red"
    # TODO: This list is too long. We should start with the set of supported
    #       keywords and extend it as we support more
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

    # use classmethod instead of custom init
    @classmethod
    def from_config(
        cls, config: ConfigTask, task_ref: ConfigCycleTask, workflow: Workflow, date: datetime | None = None
    ) -> Self:
        inputs: list[Data] = []
        for input_spec in task_ref.inputs:
            inputs.extend(data for data in workflow.data.get(input_spec, date) if data is not None)
        outputs: list[Data] = [workflow.data[output_spec.name, date] for output_spec in task_ref.outputs]

        new = cls(
            date=date,
            inputs=inputs,
            outputs=outputs,
            workflow=workflow,
            **dict(config),  # use the fact that pydantic models can be turned into dicts easily
        )  # this works because dataclass has generated this init for us

        # Store for actual linking in link_wait_on_tasks() once all tasks are created
        new._wait_on_specs = task_ref.depends  # noqa: SLF001 we don't have access to self in a dataclass
        #                                                     and setting an underscored attribute from
        #                                                     the class itself raises SLF001

        return new

    def link_wait_on_tasks(self):
        self.wait_on: list[Task] = []
        for wait_on_spec in self._wait_on_specs:
            self.wait_on.extend(task for task in self.workflow.tasks.get(wait_on_spec, self.date) if task is not None)


@dataclass(kw_only=True)
class Data(NodeStr):
    """Internal representation of a data node"""

    color: str = "light_blue"
    name: str
    type: str
    src: str
    available: bool
    date: datetime | None = None

    @classmethod
    def from_config(cls, config: DataBaseModel, *, date: datetime | None = None):
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

    color: str = "light_green"
    name: str
    tasks: list[Task]
    date: datetime | None = None


class TimeSeries(Generic[TimeSeriesObject]):
    """Dictionnary of objects accessed by date, checking start and end dates"""

    def __init__(self) -> None:
        self.start_date: datetime | None = None
        self.end_date: datetime | None = None
        self._dict: dict[str:TimeSeriesObject] = {}

    def __setitem__(self, date: datetime, data: TimeSeriesObject) -> None:
        if date in self._dict:
            msg = f"date {date} already used, cannot set twice"
            raise KeyError(msg)
        self._dict[date] = data
        if self.start_date is None:
            self.start_date = date
            self.end_date = date
        elif date < self.start_date:
            self.start_date = date
        elif date > self.end_date:
            self.end_date = date

    def __getitem__(self, date: datetime) -> TimeSeriesObject:
        if self.start_date is None:
            msg = "TimeSeries still empty, cannot access by date"
            raise ValueError(msg)
        if date < self.start_date or date > self.end_date:
            item = next(iter(self._dict.values()))
            msg = (
                f"date {date} for item '{item.name}' is out of bounds [{self.start_date} - {self.end_date}], ignoring."
            )
            logger.warning(msg)
            return
        if date not in self._dict:
            item = next(iter(self._dict.values()))
            msg = f"date {date} for item '{item.name}' not found"
            raise KeyError(msg)
        return self._dict[date]

    def values(self) -> Iterator[TimeSeriesObject]:
        yield from self._dict.values()


class Store(Generic[TimeSeriesObject]):
    """Container for TimeSeries or unique data"""

    def __init__(self):
        self._dict: dict[str, TimeSeries | TimeSeriesObject] = {}

    def __setitem__(self, key: str | tuple(str, datetime | None), value: TimeSeriesObject) -> None:
        if isinstance(key, tuple):
            name, date = key
        else:
            name, date = key, None
        if name in self._dict:
            if not isinstance(self._dict[name], TimeSeries):
                msg = f"single entry {name} already set"
                raise KeyError(msg)
            if date is None:
                msg = f"entry {name} is a TimeSeries, must be accessed by date"
                raise KeyError(msg)
            self._dict[name][date] = value
        elif date is None:
            self._dict[name] = value
        else:
            self._dict[name] = TimeSeries()
            self._dict[name][date] = value

    def __getitem__(self, key: str | tuple(str, datetime | None)) -> TimeSeriesObject:
        if isinstance(key, tuple):
            name, date = key
        else:
            name, date = key, None

        if name not in self._dict:
            msg = f"entry {name} not found in Store"
            raise KeyError(msg)
        if isinstance(self._dict[name], TimeSeries):
            if date is None:
                msg = f"entry {name} is a TimeSeries, must be accessed by date"
                raise KeyError(msg)
            return self._dict[name][date]
        if date is not None:
            msg = f"entry {name} is not a TimeSeries, cannot be accessed by date"
            raise KeyError(msg)
        return self._dict[name]

    @staticmethod
    def _resolve_target_dates(spec, ref_date: datetime | None) -> Iterator[datetime]:
        if not spec.lag and not spec.date:
            yield ref_date
        if spec.lag:
            for lag in spec.lag:
                yield ref_date + lag
        if spec.date:
            yield from spec.date

    def get(self, spec: ConfigCycleSpec, ref_date: datetime | None = None) -> Iterator[TimeSeriesObject]:
        name = spec.name
        if isinstance(self._dict[name], TimeSeries):
            if ref_date is None and spec.date is []:
                msg = "TimeSeries object must be referenced by dates"
                raise ValueError(msg)
            for target_date in self._resolve_target_dates(spec, ref_date):
                yield self._dict[name][target_date]
        else:
            if spec.lag or spec.date:
                msg = f"item {name} is not a TimeSeries, cannot be referenced via date or lag"
                raise ValueError(msg)
            yield self._dict[name]

    def values(self) -> Iterator[TimeSeriesObject]:
        for item in self._dict.values():
            if isinstance(item, TimeSeries):
                yield from item.values()
            else:
                yield item


class Workflow:
    """Internal reprensentation of a worflow"""

    def __init__(self, workflow_config: ConfigWorkflow) -> None:
        self.name = workflow_config.name
        self.tasks = Store()
        self.data = Store()
        self.cycles = Store()

        # 1 - create availalbe data nodes
        for data_config in workflow_config.data.available:
            self.data[data_config.name] = Data.from_config(data_config, date=None)

        # 2 - create output data nodes
        for cycle_config in workflow_config.cycles:
            for date in self.cycle_dates(cycle_config):
                for task_ref in cycle_config.tasks:
                    for data_ref in task_ref.outputs:
                        data_name = data_ref.name
                        data_config = workflow_config.data_dict[data_name]
                        self.data[data_name, date] = Data.from_config(data_config, date=date)

        # 3 - create cycles and tasks
        for cycle_config in workflow_config.cycles:
            cycle_name = cycle_config.name
            for date in self.cycle_dates(cycle_config):
                cycle_tasks = []
                for task_ref in cycle_config.tasks:
                    task_name = task_ref.name
                    task_config = workflow_config.task_dict[task_name]
                    self.tasks[task_name, date] = (
                        task := Task.from_config(task_config, task_ref, workflow=self, date=date)
                    )
                    cycle_tasks.append(task)
                self.cycles[cycle_name, date] = Cycle(name=cycle_name, tasks=cycle_tasks, date=date)

        # 4 - Link wait on tasks
        for task in self.tasks.values():
            task.link_wait_on_tasks()

    def cycle_dates(self, cycle_config: ConfigCycle) -> Iterator[datetime]:
        yield (date := cycle_config.start_date)
        if cycle_config.period is not None:
            while (date := date + cycle_config.period) < cycle_config.end_date:
                yield date

    def _str_from_method(self, method_name: Literal["__str__", "_str_pretty_"]) -> str:
        str_method = getattr(NodeStr, method_name)
        ind = ""
        lines = []
        lines.append(f"{ind}cycles:")
        ind += "  "
        for cycle in self.cycles.values():
            lines.append(f"{ind}- {str_method(cycle)}:")
            ind += "    "
            lines.append(f"{ind}tasks:")
            ind += "  "
            for task in cycle.tasks:
                lines.append(f"{ind}- {str_method(task)}:")
                ind += "    "
                if task.inputs:
                    lines.append(f"{ind}input:")
                    ind += "  "
                    lines.extend(f"{ind}- {str_method(data)}" for data in task.inputs)
                    ind = ind[:-2]
                if task.outputs:
                    lines.append(f"{ind}output:")
                    ind += "  "
                    lines.extend(f"{ind}- {str_method(data)}" for data in task.outputs)
                    ind = ind[:-2]
                if task.wait_on:
                    lines.append(f"{ind}wait on:")
                    ind += "  "
                    lines.extend(f"{ind}- {str_method(wait_task)}" for wait_task in task.wait_on)
                    ind = ind[:-2]
                ind = ind[:-4]
            ind = ind[:-4]
            ind = ind[:-2]
        ind = ind[:-2]
        return "\n".join(lines)

    def __str__(self):
        return self._str_from_method("__str__")

    def _str_pretty_(self):
        return self._str_from_method("_str_pretty_")

    def _repr_pretty_(self, p, cycle):
        p.text(self._str_pretty_() if not cycle else "...")

    @classmethod
    def from_yaml(cls, config_path: str):
        return cls(load_workflow_config(config_path))
