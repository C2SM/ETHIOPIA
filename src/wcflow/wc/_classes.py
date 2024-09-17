# We create python instances from the yaml file
# to make the objects more accesible when going through with the logic
from __future__ import annotations

import time
from datetime import datetime
from os.path import expandvars
from pathlib import Path

from isoduration import parse_duration
from isoduration.types import Duration

from wcflow import core
from wcflow._utils import ParseUtils, TimeUtils
from wcflow.wc._schema import load_yaml


class _NamedBase:
    """Base class for WC classes with a key that specifies their name.
    For example

    .. yaml
        name:
            property: true
    """

    @classmethod
    def from_spec(cls, name: str, spec: dict | None = None):
        if spec is None:
            return cls(name)
        return cls(name, **spec)

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name


class Task(_NamedBase):
    """
    To create an instance of a task defined in a .wc file
    """

    def __init__(
        self,
        name: str,
        command: str,
        command_option: str | None = None,
        host: str | None = None,
        account: str | None = None,
        plugin: str | None = None,
        config: str | None = None,
        uenv: str | None = None,
        nodes: int | None = None,
        walltime: str | None = None,
        src: str | None = None,
        conda_env: str | None = None,
    ):
        super().__init__(name)
        self._command = expandvars(command)
        self._command_option = command_option
        self._host = host
        self._account = account
        self._plugin = plugin
        self._config = config
        self._uenv = uenv
        self._nodes = nodes
        self._walltime = None if walltime is None else time.strptime(walltime, "%H:%M:%S")
        self._src = src
        self._conda_env = conda_env

    @property
    def command(self) -> str:
        return self._command

    @property
    def command_option(self) -> str | None:
        return self._command_option

    @property
    def host(self) -> str | None:
        return self._host

    @property
    def account(self) -> str | None:
        return self._account

    @property
    def plugin(self) -> str | None:
        return self._plugin

    @property
    def config(self) -> str | None:
        return self._config

    @property
    def uenv(self) -> str | None:
        return self._uenv

    @property
    def nodes(self) -> int | None:
        return self._nodes

    @property
    def walltime(self) -> time.struct_time | None:
        return self._walltime

    @property
    def src(self) -> str | None:
        return self._src

    @property
    def conda_env(self) -> str | None:
        return self._conda_env


class Data(_NamedBase):
    """
    Parses an entry of the data key of WC yaml file.
    """

    def __init__(
        self,
        name: str,
        type: str,  # noqa: A002
        src: str,
        format: str | None = None,  # noqa: A002
    ):
        self._name = name

        self._src = src

        self._type = type
        if self._type not in ["file", "dir"]:
            msg = f"Data type {self._type!r} not supported. Please use 'file' or 'dir'."
            raise ValueError(msg)

        self._format = format

    @property
    def name(self) -> str:
        """The name of this data instance."""
        return self._name

    @property
    def src(self) -> str:
        return self._src

    @property
    def type(self) -> str:
        """The type of this data instance."""
        return self._type

    @property
    def format(self):
        return self._format


class CycleTaskDepend(_NamedBase):
    def __init__(
        self, task_name: str, lag: str | None = None, date: datetime | str | None = None, cycle_name: str | None = None
    ):
        self._task_name = task_name
        if lag is not None and date is not None:
            msg = "Only one key 'lag' or 'date' is allowed. Not both."
            raise ValueError(msg)

        lags = lag if isinstance(lag, list) else [lag]
        self._lag = [parse_duration(lag) for lag in lags if lag is not None]

        dates = date if isinstance(date, list) else [date]
        self._date = [
            date if isinstance(date, datetime) else datetime.fromisoformat(date) for date in dates if date is not None
        ]

        self._cycle_name = cycle_name

    @property
    def task_name(self) -> str:
        return self._task_name

    @property
    def lag(self) -> list[Duration]:
        return self._lag

    @property
    def date(self) -> list[datetime]:
        return self._date

    @property
    def cycle_name(self) -> str | None:
        return self._cycle_name


class CycleTaskData(_NamedBase):
    def __init__(
        self,
        name: str,
        lag: list[str] | str | None = None,
        date: list[str | datetime] | str | datetime | None = None,
        arg_option: str | None = None,
    ):
        super().__init__(name)

        if lag is not None and date is not None:
            msg = "Only one key 'lag' or 'date' is allowed. Not both."
            raise ValueError(msg)

        if lag is None:
            lags = []
        elif isinstance(lag, str):
            lags = [lag]
        else:
            lags = lag
        self._lag = [parse_duration(lag) for lag in lags]

        if date is None:
            dates = []
        elif isinstance(date, (datetime, str)):
            dates = [date]
        else:
            dates = date
        self._date = [date if isinstance(date, datetime) else datetime.fromisoformat(date) for date in dates]

        self._arg_option = arg_option

    @property
    def lag(self) -> list[Duration]:
        return self._lag

    @property
    def date(self) -> list[datetime]:
        return self._date

    @property
    def arg_option(self) -> str | None:
        return self._arg_option


class CycleTask(_NamedBase):
    def __init__(
        self,
        name: str,
        inputs: list[str | dict] | None = None,
        outputs: list[str | dict] | None = None,
        depends: list[str | dict] | None = None,
    ):
        super().__init__(name)
        self._inputs = (
            [CycleTaskData.from_spec(name, spec) for name, spec in ParseUtils.entries_to_dicts(inputs).items()]
            if inputs is not None
            else []
        )
        self._outputs = (
            [CycleTaskData.from_spec(name, spec) for name, spec in ParseUtils.entries_to_dicts(outputs).items()]
            if outputs is not None
            else []
        )
        self._depends = (
            [CycleTaskDepend.from_spec(name, spec) for name, spec in ParseUtils.entries_to_dicts(depends).items()]
            if depends is not None
            else []
        )

    @property
    def inputs(self) -> list[CycleTaskData]:
        return self._inputs

    @property
    def outputs(self) -> list[CycleTaskData]:
        return self._outputs

    @property
    def depends(self) -> list[CycleTaskDepend]:
        return self._depends


class Cycle(_NamedBase):
    """
    We never need to create instances of a cycle class so we only contains static methods
    """

    def __init__(
        self,
        name: str,
        tasks: dict[str, dict],
        start_date: str | datetime | None = None,
        end_date: str | datetime | None = None,
        period: str | Duration | None = None,
    ):
        super().__init__(name)
        self._tasks = [CycleTask.from_spec(name, spec) for name, spec in tasks.items()]

        self._start_date = datetime.fromisoformat(start_date) if isinstance(start_date, str) else start_date
        self._end_date = datetime.fromisoformat(end_date) if isinstance(end_date, str) else end_date
        if self._start_date is not None and self._end_date is not None and self._start_date > self._end_date:
            msg = "For cycle {self._name!r} the start_date {start_date!r} lies after given end_date {end_date!r}."
            raise ValueError(msg)

        self._period = period if period is None or isinstance(period, Duration) else parse_duration(period)
        if self._period is not None and TimeUtils.duration_is_less_equal_zero(self._period):
            msg = f"For cycle {self._name!r} the period {period!r} is negative or zero."
            raise ValueError(msg)

    def __iter__(self):
        yield from self._tasks

    @property
    def start_date(self) -> datetime | None:
        return self._start_date

    @property
    def end_date(self) -> datetime | None:
        return self._end_date

    @property
    def period(self) -> Duration | None:
        return self._period

    @property
    def tasks(self) -> list[CycleTask]:
        return self._tasks


class Workflow(_NamedBase):
    @classmethod
    def from_yaml(cls, config):
        config_path = Path(config)

        loaded_config = load_yaml(config_path)
        return cls.from_spec(expandvars(config_path.stem), loaded_config)

    def __init__(
        self,
        name: str,
        start_date: str,
        end_date: str,
        cycles: dict[str, dict],
        tasks: dict[str, dict],
        data: dict[str, dict],
    ):
        self._name = name
        self._start_date = datetime.fromisoformat(start_date)
        self._end_date = datetime.fromisoformat(end_date)
        self._cycles = [Cycle.from_spec(name, spec) for name, spec in cycles.items()]
        if (root_task := tasks.pop("root", None)) is not None:
            for root_key in root_task:
                for task_spec in tasks.values():
                    if root_key not in task_spec:
                        task_spec[root_key] = root_task[root_key]
        self._tasks = {name: Task.from_spec(name, spec) for name, spec in tasks.items()}
        self._data = {name: Data.from_spec(name, spec) for name, spec in data.items()}

    def to_core_workflow(self):
        core_cycles = [self._to_core_cycle(cycle) for cycle in self._cycles]
        return core.Workflow(self.name, core_cycles)

    def _to_core_cycle(self, cycle: Cycle) -> core.Cycle:
        core_tasks = [self._to_core_task(task) for task in cycle.tasks]
        start_date = self._start_date if cycle.start_date is None else cycle.start_date
        end_date = self._end_date if cycle.end_date is None else cycle.end_date
        return core.Cycle(cycle.name, core_tasks, start_date, end_date, cycle.period)

    def _to_core_task(self, task: CycleTask) -> core.Task:
        inputs = []
        outputs = []
        dependencies = []
        for input_ in task.inputs:
            if (data := self._data.get(input_.name)) is None:
                msg = f"Task {task.name!r} has input {input_.name!r} that is not specied in the data section."
                raise ValueError(msg)
            core_data = core.Data(input_.name, data.type, data.src, input_.lag, input_.date, input_.arg_option)
            inputs.append(core_data)
        for output in task.outputs:
            if (data := self._data.get(output.name)) is None:
                msg = f"Task {task.name!r} has output {output.name!r} that is not specied in the data section."
                raise ValueError(msg)
            core_data = core.Data(output.name, data.type, data.src, [], [], None)
            outputs.append(core_data)
        for depend in task.depends:
            core_dependency = core.Dependency(depend.task_name, depend.lag, depend.date, depend.cycle_name)
            dependencies.append(core_dependency)

        return core.Task(
            task.name,
            self._tasks[task.name].command,
            inputs,
            outputs,
            dependcies,
            self._tasks[task.name].command_option,
        )
