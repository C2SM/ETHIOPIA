# We create python instances from the yaml file
# to make the objects more accesible when going through with the logic

from wcflow._utils import TimeUtils
import yaml
from datetime import datetime
import time
from isoduration.types import Duration
from isoduration import parse_duration
from os.path import expandvars
from pathlib import Path
from typing import Optional
from wcflow import core
from wcflow._utils import ParseUtils


class WcNamedBase:
    """Base class for WC classes with a key that specifies their name.
    For example

    .. yaml
        name:
            property: true
    """

    required_spec_keys = []
    valid_spec_keys = []

    @classmethod
    def from_spec(cls, name: str, spec: dict | None = None):
        if spec is None:
            return cls(name)
        for key in spec.keys():
            if key not in cls.valid_spec_keys:
                raise ValueError(f"When creating {cls} instance {name!r} found invalid key {key!r}. Key must be in {cls.valid_spec_keys}")
        for key in cls.required_spec_keys:
            if key not in spec.keys():
                raise ValueError(
                    f"When creating {cls} instance {name!r}, {key!r} was not given in the specification but is required."
                )
        return cls(name, **spec)

    def __init__(self, name: str):
        self._name = name
    
    @property
    def name(self) -> str:
        return self._name

class WcTask(WcNamedBase):
    """
    To create an instance of a task defined in a .wc file
    """ 

    # todo for what is src?
    required_spec_keys = ["command"]
    valid_spec_keys = ["command", "host", "account", "plugin", "config", "uenv", "nodes", "walltime", "src", "conda_env"]

    def __init__(
        self,
        name: str,
        command: str,
        host: Optional[str] = None,
        account: Optional[str] = None,
        plugin: Optional[str] = None,
        config: Optional[str] = None,
        uenv: Optional[str] = None,
        nodes: Optional[int] = None,
        walltime: Optional[str] = None,
        src: Optional[str] = None, 
        conda_env: Optional[str] = None, 
    ):
        super().__init__(name)
        self._command = expandvars(command)
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
    def host(self) -> str:
        return self._host

    @property
    def account(self) -> str:
        return self._account

    @property
    def plugin(self) -> str:
        return self._plugin

    @property
    def config(self) -> str:
        return self._config

    @property
    def uenv(self) -> str:
        return self._uenv

    @property
    def nodes(self) -> int:
        return self._nodes

    @property
    def walltime(self) -> datetime:
        return self._walltime
    
    @property
    def src(self) -> str:
        return self._src

    @property
    def conda_env(self) -> str:
        return self._conda_env

class WcData(WcNamedBase):
    """
    Parses an entry of the data key of WC yaml file.
    """
    required_spec_keys = ["type", "src"]
    valid_spec_keys = ["type", "src", "format"]

    def __init__(self, name: str, type: str, src: str, format: Optional[str] = None):
        self._name = name

        self._src = src 

        self._type = type
        if self._type not in ["file", "dir"]:
            raise ValueError(f'Data type {self._type!r} not supported. Please use \'file\' or \'dir\'.')

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


class WcCycleTaskData(WcNamedBase):

    required_spec_keys = []
    valid_spec_keys = ["lag", "date"]

    def __init__(self, name: str, lag: Optional[str | Duration] = None, date: Optional[datetime | str] = None):
        self._name = name

        lags = lag if isinstance(lag, list) else [lag]
        self._lag = [parse_duration(lag)
                        for lag in lags if lag is not None]

        dates = date if isinstance(date, list) else [date]
        self._date = [date if isinstance(date, datetime) else datetime.fromisoformat(date)
                      for date in dates if date is not None]

    @property
    def name(self) -> str:
        """The name of this data instance."""
        return self._name
    
    @property
    def lag(self) -> list[Duration]:
        return self._lag

    @property
    def date(self) -> list[datetime]:
        return self._date

class WcCycleTaskArgument:

    @classmethod
    def from_spec(cls, name: str, spec: dict):
        return cls(**({'name': name} | spec))

    def __init__(self, argument: str | dict):
        # 3 options for arguments
        # argument options:

        # - input_file --> f"command {input_file}"
        # - input: preproc_output --> f"command --input {preproc_output}"
        # - verbose: null --> f"command --verbose"
        if isinstance(argument, str):
            self._option = None
            self._value = argument
        elif isinstance(argument, dict) and len(argument) == 1:
            self._option, self._value = next(iter(argument.items()))
        else:
            raise ValueError("Argument {argument!r} not supported. Please only use arguments of the form 'key: value' or 'key'")

    @property
    def option(self) -> str | None:
        return self._option

    @property
    def value(self) -> str | None:
        return self._value
    
    @property
    def positional_argument(self) -> bool:
        return self._option is None and self._value is not None

class WcCycleTaskDependency:

    def __init__(self, dependency: str | dict):
        # TODO somewhere check that tasks actually exist 
        if isinstance(dependency, str):
            self._task_name = dependency 
        elif isinstance(dependency, dict):
            # TODO check that only is possible
            self._task_name = next(iter(dependency.keys()))
            self._lag = dependency.get('lag')
            self._date = dependency.get('date')

    @property
    def lag(self) -> Duration | None:
        return self._lag

    @property
    def date(self) -> datetime | None:
        return self._date

class WcCycleTask(WcNamedBase):

    required_spec_keys = []
    valid_spec_keys = ["inputs", "outputs", "arguments", "depends"]

    def __init__(
        self,
        name: str,
        inputs: list[str, dict], # TODO make optional
        outputs: list[str], # TODO make optional
        arguments: list[str, dict], # TODO make optional
        depends: Optional[list[str]] = None
    ):
        super().__init__(name)
        self._inputs = [WcCycleTaskData.from_spec(name, spec) for name, spec in ParseUtils.entries_to_dicts(inputs).items()]
        self._outputs = [WcCycleTaskData.from_spec(name, spec) for name, spec in ParseUtils.entries_to_dicts(outputs).items()]
        self._arguments = [WcCycleTaskArgument(argument) for argument in arguments]
        self._depends = [WcCycleTaskArgument(depend) for depend in depends] if depends is not None else []

    @property
    def inputs(self) -> list[WcCycleTaskData]:
        return self._inputs

    @property
    def outputs(self) -> list[WcCycleTaskData]:
        return self._outputs

    @property
    def arguments(self) -> list[WcCycleTaskArgument] | None:
        return self._arguments

    @property
    def depends(self) -> list[WcCycleTaskDependency] | None:
        return self._depends

class WcWcCycleTaskData(WcNamedBase):

    required_spec_keys = []
    valid_spec_keys = ["lag", "date"]

    def __init__(self, name: str, lag: Optional[list[str] | str] = None, date: Optional[list[str | datetime] | str | datetime] = None):
        super().__init__(name)

        if lag is not None and date is not None:
            raise ValueError("Only one key 'lag' or 'date' is allowed. Not both.")

        lags = lag if isinstance(lag, list) else [lag]
        self._lag = [parse_duration(lag)
                        for lag in lags if lag is not None]

        dates = date if isinstance(date, list) else [date]
        self._date = [date if isinstance(date, datetime) else datetime.fromisoformat(date)
                      for date in dates if date is not None]

    def lag(self) -> list[str]:
        return self._lag

    def date(self) -> list[datetime]:
        return self._date

class WcCycle(WcNamedBase):
    """
    We never need to create instances of a cycle class so we only contains static methods
    """

    required_spec_keys = ["tasks"]
    valid_spec_keys =  ["tasks"] + ["start_date", "end_date", "period"]

    def __init__(self,
                name: str,
                tasks: dict[str, WcCycleTask],
                start_date: Optional[str | datetime] = None,
                end_date: Optional[str | datetime] = None,
                period: Optional[str | Duration] = None):
        super().__init__(name)
        self._tasks = [WcCycleTask.from_spec(name, spec) for name, spec in tasks.items()]

        self._start_date = None if start_date is None else datetime.fromisoformat(start_date)
        self._end_date = None if end_date is None else datetime.fromisoformat(end_date)
        if self._start_date is not None and self._end_date is not None and self._start_date > self._end_date:
            raise ValueError("For cycle {self._name!r} the start_date {start_date!r} lies after given end_date {end_date!r}.")

        self._period = period if period is None or isinstance(period, Duration) else parse_duration(period)
        if self._period is not None and TimeUtils.duration_is_less_equal_zero(self._period):
            raise ValueError(f"For cycle {self._name!r} the period {period!r} is negative or zero.")

    def __iter__(self):
        for task in self._tasks:
            yield task

    @property
    def start_date(self) -> datetime:
        return self._start_date

    @property
    def end_date(self) -> datetime:
        return self._end_date

    @property
    def period(self) -> Duration | None:
        return self._period

    @property
    def tasks(self) -> WcTask:
        return self._tasks


class WcWorkflow(WcNamedBase):

    required_spec_keys = ["start_date", "end_date", "cycles", "tasks", "data"]
    valid_spec_keys = ["start_date", "end_date", "cycles", "tasks", "data"]

    @classmethod
    def from_yaml(cls, config):
        config_path = Path(config)
        loaded_config = yaml.safe_load(config_path.read_text())
        return cls.from_spec(expandvars(config_path.stem), loaded_config)

    def __init__(self, name: str, start_date: str, end_date: str, cycles: dict[str, dict], tasks: dict[str, dict], data: dict[str, dict]):
        self._name = name
        self._start_date = datetime.fromisoformat(start_date)
        self._end_date = datetime.fromisoformat(end_date)
        self._cycles = [WcCycle.from_spec(name, spec) for name, spec in cycles.items()]
        if (root_task := tasks.pop("root")) is not None:
            for root_key in root_task.keys():
                for task_spec in tasks.values():
                    if root_key not in task_spec.keys():
                        task_spec[root_key] = root_task[root_key]
        self._tasks = {name: WcTask.from_spec(name, spec) for name, spec in tasks.items()}
        self._data = {name: WcData.from_spec(name, spec) for name, spec in data.items()}

    def to_core_workflow(self):
        core_cycles = []
        for cycle in self._cycles:
            core_cycles.append(self._to_core_cycle(cycle))
        return core.Workflow(self.name, core_cycles)
        
    def _to_core_cycle(self, cycle: WcCycle) -> core.Cycle:
        core_tasks = []
        for task in cycle.tasks:
            core_tasks.append(self._to_core_task(task))
        start_date = self._start_date if cycle.start_date is None else cycle.start_date
        end_date = self._end_date if cycle.end_date is None else cycle.end_date
        return core.Cycle(cycle.name, core_tasks, start_date, end_date, cycle.period)

    def _to_core_task(self, task: WcCycleTask) -> core.Task:
        inputs = []
        arguments = []
        outputs = []
        for input in task.inputs:
            if (data := self._data.get(input.name)) is None:
                raise ValueError(f"Task {task.name!r} has input {input.name!r} that is not specied in the data section.")
            core_data = core.Data(input.name, data.type, data.src, input.lag, input.date)
            inputs.append(core_data)
        for output in task.outputs:
            if (data := self._data.get(output.name)) is None:
                raise ValueError(f"Task {task.name!r} has output {output.name!r} that is not specied in the data section.")
            core_data = core.Data(output.name, data.type, data.src, output.lag ,input.date)
            outputs.append(core_data)
        for argument in task.arguments:
            # if argument value is input, then use input.src as value
            if (input_src := {input.name: self._data[input.name].src for input in task.inputs}.get(argument.value)) is None:
                arguments.append(core.Argument(argument.option, input_src))
            else:
                arguments.append(core.Argument(argument.option, argument.value))
                
        # TODO add depends
        return core.Task(task.name, self._tasks[task.name].command, inputs, outputs, arguments)