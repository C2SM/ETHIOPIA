from __future__ import annotations

import logging
from dataclasses import dataclass, field
from itertools import product
from typing import TYPE_CHECKING, Any, Self

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


@dataclass
class GraphItem:
    """base class for Data Tasks and Cycles"""

    name: str
    color: str
    coordinates: dict = field(default_factory=dict)

    @classmethod
    def iter_coordinates(cls, param_refs: list, parameters: dict, date: datetime) -> Iterator[dict]:
        space = ({} if date is None else {"date": [date]}) | {k: parameters[k] for k in param_refs}
        yield from (dict(zip(space.keys(), x)) for x in product(*space.values()))


@dataclass
class Task(GraphItem):
    """Internal representation of a task node"""

    color: str = "light_red"
    workflow: Workflow | None = None
    outputs: list[Data] = field(default_factory=list)
    inputs: list[Data] = field(default_factory=list)
    wait_on: list[Task] = field(default_factory=list)
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
        workflow_parameters: dict[str, list],
        graph_spec: ConfigCycleTask,
        workflow: Workflow,
        *,
        date: datetime | None = None,
    ) -> Iterator[Self]:
        for coordinates in cls.iter_coordinates(config.parameters, workflow_parameters, date):
            inputs: list[Data] = []
            for input_spec in graph_spec.inputs:
                inputs.extend(
                    data for data in workflow.data.iter_from_cycle_spec(input_spec, coordinates) if data is not None
                )

            outputs: list[Data] = [workflow.data[output_spec.name, coordinates] for output_spec in graph_spec.outputs]

            # use the fact that pydantic models can be turned into dicts easily
            cls_config = dict(config)
            del cls_config["parameters"]

            new = cls(
                coordinates=coordinates,
                inputs=inputs,
                outputs=outputs,
                workflow=workflow,
                **cls_config,
            )  # this works because dataclass has generated this init for us

            # Store for actual linking in link_wait_on_tasks() once all tasks are created
            new._wait_on_specs = graph_spec.wait_on  # noqa: SLF001 we don't have access to self in a dataclass
            #                                                and setting an underscored attribute from
            #                                                the class itself raises SLF001

            yield new

    def link_wait_on_tasks(self):
        self.wait_on: list[Task] = []
        for wait_on_spec in self._wait_on_specs:
            self.wait_on.extend(
                task
                for task in self.workflow.tasks.iter_from_cycle_spec(wait_on_spec, self.coordinates)
                if task is not None
            )


@dataclass(kw_only=True)
class Data(GraphItem):
    """Internal representation of a data node"""

    color: str = "light_blue"
    type: str
    src: str
    available: bool

    @classmethod
    def from_config(
        cls, config: DataBaseModel, workflow_parameters: dict[str, list], *, date: datetime | None = None
    ) -> Iterator[Self]:
        for coordinates in cls.iter_coordinates(config.parameters, workflow_parameters, date):
            yield cls(
                name=config.name,
                type=config.type,
                src=config.src,
                available=config.available,
                coordinates=coordinates,
            )


@dataclass(kw_only=True)
class Cycle(GraphItem):
    """Internal reprenstation of a cycle"""

    color: str = "light_green"
    tasks: list[Task]


class Array:
    """Dictionnary of GraphItem objects accessed by arbitrary dimensions"""

    def __init__(self, name: str) -> None:
        self._name = name
        self._dims: tuple[str] | None = None
        self._axes: dict | None = None
        self._dict: dict[tuple, GraphItem] | None = None

    def __setitem__(self, coordinates: dict, value: GraphItem) -> None:
        # First access: set axes and initialize dictionnary
        input_dims = tuple(coordinates.keys())
        if self._dims is None:
            self._dims = input_dims
            self._axes = {k: set() for k in self._dims}
            self._dict = {}
        # check dimensions
        elif self._dims != input_dims:
            msg = f"Array {self._name}: coordinate names {input_dims} don't match Array dimensions {self._dims}"
            raise KeyError(msg)
        # Build internal key
        # use the order of self._dims instead of param_keys to ensure reproducibility
        key = tuple(coordinates[dim] for dim in self._dims)
        # Check if slot already taken
        if key in self._dict:
            msg = f"Array {self._name}: key {key} already used, cannot set item twice"
            raise KeyError(msg)
        # Store new axes values
        for dim in self._dims:
            self._axes[dim].add(coordinates[dim])
        # Set item
        self._dict[key] = value

    def __getitem__(self, coordinates: dict) -> GraphItem:
        if self._dims != (input_dims := tuple(coordinates.keys())):
            msg = f"Array {self._name}: coordinate names {input_dims} don't match Array dimensions {self._dims}"
            raise KeyError(msg)
        # use the order of self._dims instead of param_keys to ensure reproducibility
        key = tuple(coordinates[dim] for dim in self._dims)
        return self._dict[key]

    def iter_from_cycle_spec(self, spec: ConfigCycleSpec, reference: dict) -> Iterator[GraphItem]:
        # Check date references
        if "date" not in self._dims and (spec.lag or spec.date):
            msg = f"Array {self._name} has no date dimension, cannot be referenced by dates"
            raise ValueError(msg)
        if "date" in self._dims and reference.get("date") is None and spec.date is []:
            msg = f"Array {self._name} has a date dimension, must be referenced by dates"
            raise ValueError(msg)

        for key in product(*(self._resolve_target_dim(spec, dim, reference) for dim in self._dims)):
            yield self._dict[key]

    def _resolve_target_dim(self, spec: ConfigCycleSpec, dim: str, reference: Any) -> Iterator[Any]:
        if dim == "date":
            if not spec.lag and not spec.date:
                yield reference["date"]
            if spec.lag:
                for lag in spec.lag:
                    yield reference["date"] + lag
            if spec.date:
                yield from spec.date
        elif spec.parameters.get(dim) == "single":
            yield reference[dim]
        else:
            yield from self._axes[dim]

    def __iter__(self) -> Iterator[GraphItem]:
        yield from self._dict.values()


class Store:
    """Container for Array or unique items"""

    def __init__(self):
        self._dict: dict[str, Array | GraphItem] = {}

    def add(self, item) -> None:
        if not isinstance(item, GraphItem):
            msg = "items in a Store must be of instance GraphItem"
            raise TypeError(msg)
        name, coordinates = item.name, item.coordinates
        if name in self._dict:
            if not isinstance(self._dict[name], Array):
                msg = f"single entry {name} already set"
                raise KeyError(msg)
            if not coordinates:
                msg = f"entry {name} is an Array, must be accessed by coordinates"
                raise KeyError(msg)
            self._dict[name][coordinates] = item
        elif not coordinates:
            self._dict[name] = item
        else:
            self._dict[name] = Array(name)
            self._dict[name][coordinates] = item

    def __getitem__(self, key: str | tuple[str, dict]) -> GraphItem:
        if isinstance(key, tuple):
            name, coordinates = key
            if "date" in coordinates and coordinates["date"] is None:
                del coordinates["date"]
        else:
            name, coordinates = key, {}
        if name not in self._dict:
            msg = f"entry {name} not found in Store"
            raise KeyError(msg)
        if isinstance(self._dict[name], Array):
            if not coordinates:
                msg = f"entry {name} is an Array, must be accessed by coordinates"
                raise KeyError(msg)
            return self._dict[name][coordinates]
        if coordinates:
            msg = f"entry {name} is not an Array, cannot be accessed by coordinates"
            raise KeyError(msg)
        return self._dict[name]

    def iter_from_cycle_spec(self, spec: ConfigCycleSpec, reference: dict) -> Iterator[GraphItem]:
        # Check if target items should be querried at all
        if (when := spec.when) is not None:
            if (ref_date := reference.get("date")) is None:
                msg = "Cannot use a `when` specification without a `reference date`"
                raise ValueError(msg)
            if (at := when.at) is not None and at != ref_date:
                return
            if (before := when.before) is not None and before <= ref_date:
                return
            if (after := when.after) is not None and after >= ref_date:
                return
        # Yield items
        name = spec.name
        if isinstance(self._dict[name], Array):
            yield from self._dict[name].iter_from_cycle_spec(spec, reference)
        else:
            if spec.lag or spec.date:
                msg = f"item {name} is not an Array, cannot be referenced by date or lag"
                raise ValueError(msg)
            if spec.parameters:
                msg = f"item {name} is not an Array, cannot be referenced by parameters"
                raise ValueError(msg)
            yield self._dict[name]

    def __iter__(self) -> Iterator[GraphItem]:
        for item in self._dict.values():
            if isinstance(item, Array):
                yield from item
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
            for data in Data.from_config(data_config, workflow_config.parameters, date=None):
                self.data.add(data)

        # 2 - create output data nodes
        for cycle_config in workflow_config.cycles:
            for date in self.cycle_dates(cycle_config):
                for task_ref in cycle_config.tasks:
                    for data_ref in task_ref.outputs:
                        data_name = data_ref.name
                        data_config = workflow_config.data_dict[data_name]
                        for data in Data.from_config(data_config, workflow_config.parameters, date=date):
                            self.data.add(data)

        # 3 - create cycles and tasks
        for cycle_config in workflow_config.cycles:
            cycle_name = cycle_config.name
            for date in self.cycle_dates(cycle_config):
                cycle_tasks = []
                for task_graph_spec in cycle_config.tasks:
                    task_name = task_graph_spec.name
                    task_config = workflow_config.task_dict[task_name]
                    for task in Task.from_config(
                        task_config, workflow_config.parameters, task_graph_spec, workflow=self, date=date
                    ):
                        self.tasks.add(task)
                        cycle_tasks.append(task)
                coordinates = {} if date is None else {"date": date}
                self.cycles.add(Cycle(name=cycle_name, tasks=cycle_tasks, coordinates=coordinates))

        # 4 - Link wait on tasks
        for task in self.tasks:
            task.link_wait_on_tasks()

    @staticmethod
    def cycle_dates(cycle_config: ConfigCycle) -> Iterator[datetime]:
        yield (date := cycle_config.start_date)
        if cycle_config.period is not None:
            while (date := date + cycle_config.period) < cycle_config.end_date:
                yield date

    @classmethod
    def from_yaml(cls, config_path: str):
        return cls(load_workflow_config(config_path))
