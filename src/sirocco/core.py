from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Generic, Self, TypeVar

from sirocco.parsing._yaml_data_models import (
    ConfigCycleTask,
    ConfigCycleTaskInput,
    ConfigCycleTaskWaitOn,
    ConfigTask,
    ConfigWorkflow,
    load_workflow_config,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import datetime

    from sirocco.parsing._yaml_data_models import ConfigCycle, DataBaseModel

    type ConfigCycleSpec = ConfigCycleTaskWaitOn | ConfigCycleTaskInput

logging.basicConfig()
logger = logging.getLogger(__name__)


StoreObject = TypeVar("StoreObject")


class BaseNode:
    name: str
    color: str


@dataclass
class Task(BaseNode):
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
        cls,
        config: ConfigTask,
        task_ref: ConfigCycleTask,
        workflow: Workflow,
        date: datetime | None = None,
    ) -> Self:
        inputs: list[Data] = []
        for input_spec in task_ref.inputs:
            inputs.extend(data for data in workflow.data.iter_from_cycle_spec(input_spec, date) if data is not None)
        outputs: list[Data] = [workflow.data[output_spec.name, {"date": date}] for output_spec in task_ref.outputs]

        new = cls(
            date=date,
            inputs=inputs,
            outputs=outputs,
            workflow=workflow,
            **dict(config),  # use the fact that pydantic models can be turned into dicts easily
        )  # this works because dataclass has generated this init for us

        # Store for actual linking in link_wait_on_tasks() once all tasks are created
        new._wait_on_specs = task_ref.wait_on  # noqa: SLF001 we don't have access to self in a dataclass
        #                                                     and setting an underscored attribute from
        #                                                     the class itself raises SLF001

        return new

    def link_wait_on_tasks(self):
        self.wait_on: list[Task] = []
        for wait_on_spec in self._wait_on_specs:
            self.wait_on.extend(
                task for task in self.workflow.tasks.iter_from_cycle_spec(wait_on_spec, self.date) if task is not None
            )


@dataclass(kw_only=True)
class Data(BaseNode):
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
class Cycle(BaseNode):
    """Internal reprenstation of a cycle"""

    color: str = "light_green"
    name: str
    tasks: list[Task]
    date: datetime | None = None


class ParamSeries(Generic[StoreObject]):
    """Dictionnary of objects accessed by arbitrary parameters"""

    def __init__(self, name: str) -> None:
        self._name = name
        self._dims: set | None = None
        self._axes: dict | None = None
        self._dict: dict[tuple:StoreObject] | None = None

    def __setitem__(self, parameters: dict, value: StoreObject) -> None:
        # First access: set axes and initialize dictionnary
        param_keys = set(parameters.keys())
        if self._dims is None:
            self._dims = param_keys
            self._axes = {k: set() for k in param_keys}
            self._dict = {}
        # check dimensions
        elif self._dims != param_keys:
            msg = (
                f"ParamSeries {self._name}: parameter keys {param_keys} don't match ParamSeries dimensions {self._dims}"
            )
            raise KeyError(msg)
        # Build internal key
        # use the order of self._dims instead of param_keys to ensure reproducibility
        key = tuple(parameters[dim] for dim in self._dims)
        # Check if slot already taken
        if key in self._dict:
            msg = f"ParamSeries {self._name}: key {key} already used, cannot set item twice"
            raise KeyError(msg)
        # Store new axes values
        for dim in self._dims:
            self._axes[dim].add(parameters[dim])
        # Set item
        self._dict[key] = value

    def __getitem__(self, parameters: dict) -> StoreObject:
        if self._dims != (param_keys := set(parameters.keys())):
            msg = (
                f"ParamSeries {self._name}: parameter keys {param_keys} don't match ParamSeries dimensions {self._dims}"
            )
            raise KeyError(msg)
        # use the order of self._dims instead of param_keys to ensure reproducibility
        key = tuple(parameters[dim] for dim in self._dims)
        return self._dict[key]

    def iter_from_cycle_spec(self, spec: ConfigCycleSpec, ref_date: datetime | None = None) -> Iterator[StoreObject]:
        # Check date references
        if "date" not in self._dims and (spec.lag or spec.date):
            msg = f"ParamSeries {self._name} has no date dimension, cannot be referenced by dates"
            raise ValueError(msg)
        if "date" in self._dims and ref_date is None and spec.date is []:
            msg = f"ParamSeries {self._name} has a date dimension, must be referenced by dates"
            raise ValueError(msg)
        # Generate list of target item keys
        keys = [()]
        for dim in self._dims:
            if dim == "date":
                keys = [(*key, date) for key in keys for date in self._resolve_target_dates(spec, ref_date)]
            elif dim in spec.parameters:
                keys = [(*key, spec.parameters[dim]) for key in keys]
            else:
                keys = [(*key, item) for key in keys for item in self._axes[dim]]
        # Yield items
        for key in keys:
            yield self._dict[key]

    @staticmethod
    def _resolve_target_dates(spec: ConfigCycleSpec, ref_date: datetime | None) -> Iterator[datetime]:
        if not spec.lag and not spec.date:
            yield ref_date
        if spec.lag:
            for lag in spec.lag:
                yield ref_date + lag
        if spec.date:
            yield from spec.date

    def values(self) -> Iterator[StoreObject]:
        yield from self._dict.values()


class Store(Generic[StoreObject]):
    """Container for ParamSeries or unique items"""

    def __init__(self):
        self._dict: dict[str, ParamSeries | StoreObject] = {}

    def __setitem__(self, key: str | tuple(str, dict | None), value: StoreObject) -> None:
        if isinstance(key, tuple):
            name, parameters = key
            if "date" in parameters and parameters["date"] is None:
                del parameters["date"]
        else:
            name, parameters = key, None
        if name in self._dict:
            if not isinstance(self._dict[name], ParamSeries):
                msg = f"single entry {name} already set"
                raise KeyError(msg)
            if parameters is None:
                msg = f"entry {name} is a ParamSeries, must be accessed by parameters"
                raise KeyError(msg)
            self._dict[name][parameters] = value
        elif not parameters:
            self._dict[name] = value
        else:
            self._dict[name] = ParamSeries(name)
            self._dict[name][parameters] = value

    def __getitem__(self, key: str | tuple(str, dict | None)) -> StoreObject:
        if isinstance(key, tuple):
            name, parameters = key
            if "date" in parameters and parameters["date"] is None:
                del parameters["date"]
        else:
            name, parameters = key, None
        if name not in self._dict:
            msg = f"entry {name} not found in Store"
            raise KeyError(msg)
        if isinstance(self._dict[name], ParamSeries):
            if parameters is None:
                msg = f"entry {name} is a ParamSeries, must be accessed by parameters"
                raise KeyError(msg)
            return self._dict[name][parameters]
        if parameters:
            msg = f"entry {name} is not a ParamSeries, cannot be accessed by parameters"
            raise KeyError(msg)
        return self._dict[name]

    def iter_from_cycle_spec(self, spec: ConfigCycleSpec, ref_date: datetime | None = None) -> Iterator[StoreObject]:
        # Check if target items should be querried at all
        if (when := spec.when) is not None:
            if ref_date is None:
                msg = "Cannot use a `when` specification without a `ref_date`"
                raise ValueError(msg)
            if (at := when.at) is not None and at != ref_date:
                return
            if (before := when.before) is not None and before <= ref_date:
                return
            if (after := when.after) is not None and after >= ref_date:
                return
        # Yield items
        name = spec.name
        if isinstance(self._dict[name], ParamSeries):
            yield from self._dict[name].iter_from_cycle_spec(spec, ref_date)
        else:
            if spec.lag or spec.date:
                msg = f"item {name} is not a ParamSeries, cannot be referenced by date or lag"
                raise ValueError(msg)
            if spec.parameters:
                msg = f"item {name} is not a ParamSeries, cannot be referenced by parameters"
                raise ValueError(msg)
            yield self._dict[name]

    def values(self) -> Iterator[StoreObject]:
        for item in self._dict.values():
            if isinstance(item, ParamSeries):
                yield from item.values()
            else:
                yield item


class Workflow:
    """Internal reprensentation of a workflow"""

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
                        self.data[data_name, {"date": date}] = Data.from_config(data_config, date=date)

        # 3 - create cycles and tasks
        for cycle_config in workflow_config.cycles:
            cycle_name = cycle_config.name
            for date in self.cycle_dates(cycle_config):
                cycle_tasks = []
                for task_ref in cycle_config.tasks:
                    task_name = task_ref.name
                    task_config = workflow_config.task_dict[task_name]
                    task = Task.from_config(task_config, task_ref, workflow=self, date=date)
                    self.tasks[task_name, {"date": date}] = (
                        task := Task.from_config(task_config, task_ref, workflow=self, date=date)
                    )
                    cycle_tasks.append(task)
                self.cycles[cycle_name, {"date": date}] = Cycle(name=cycle_name, tasks=cycle_tasks, date=date)

        # 4 - Link wait on tasks
        for task in self.tasks.values():
            task.link_wait_on_tasks()

    def cycle_dates(self, cycle_config: ConfigCycle) -> Iterator[datetime]:
        yield (date := cycle_config.start_date)
        if cycle_config.period is not None:
            while (date := date + cycle_config.period) < cycle_config.end_date:
                yield date

    @classmethod
    def from_yaml(cls, config_path: str):
        return cls(load_workflow_config(config_path))
