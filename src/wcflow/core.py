from __future__ import annotations

from datetime import datetime
from isoduration.types import Duration
from isoduration import parse_duration 
from os.path import expandvars
from pathlib import Path
from typing import Generator, Optional
from wcflow._utils import TimeUtils

class Data:

    def __init__(self, name: str, type: str, src: str, lags: list[Duration], dates: list[datetime]):
        self._name = name

        self._src = src 
        self._path = Path(expandvars(self._src))

        self._type = type
        if self._type not in ["file", "dir"]:
            raise ValueError(f'Data type {self._type!r} not supported. Please use \'file\' or \'dir\'.')

        self._lags = lags
        self._dates = dates

    @property
    def name(self) -> str:
        """The name of this data instance."""
        return self._name

    @property
    def type(self) -> str:
        """The type of this data instance."""
        return self._type

    @property
    def src(self) -> str:
        return self._src

    @property
    def path(self) -> str:
        return self._path

    @property
    def lags(self) -> list[Duration]:
        return self._lags

    @property
    def dates(self) -> list[datetime]:
        return self._dates

    def __eq__(self, other_data: Data) -> bool:
        return self._name == other_data.name

    def unroll(self, unrolled_task: UnrolledTask) -> Generator[UnrolledData]:
        if len(self._dates) == 0 and len(self._lags) == 0:
            yield UnrolledData.from_data(self, unrolled_task, unrolled_task.date)

        for lag in self._lags:
            lagged_date = unrolled_task.date + lag
            if lagged_date >= unrolled_task.unrolled_cycle.start_date and lagged_date <= unrolled_task.unrolled_cycle.end_date:
                yield UnrolledData.from_data(self, unrolled_task, lagged_date)

        for date in self._dates:
            yield UnrolledData.from_data(self, unrolled_task, date)

# COMMENT I think it makes more sense to separate UnrolledData from Data (same for others),
#         since it refers to a certain instance from Data (keeping all dates and lags present does not make so much sense)
#         To reduce code one could do BaseData -> Data, BaseData -> UnrolledData
class UnrolledData(Data):
    """Data that are created during the unrolling of a cycle.
    """
    @classmethod
    def from_data(cls, data: Data, unrolled_task: UnrolledTask, date: datetime):
        return cls(unrolled_task, date, data.name, data.type, data.src, data.lags, data.dates)

    def __init__(self, unrolled_task: UnrolledTask, date: datetime, name: str, type: str, src: str, lags: list[Duration], dates: list[datetime]):
        super().__init__(name, type, src, lags, dates)
        self._unrolled_task = unrolled_task
        self._date = date

    def __eq__(self, other_data: UnrolledData) -> bool:
        return self.name == other_data.name and self.date == other_data.date

    def __hash__(self) -> int:
        return hash((self._name, self.date))

    @property
    def date(self) -> datetime:
        return self._date

    @property
    def unrolled_task(self) -> UnrolledTask:
        return self._unrolled_task

class Argument:
    def __init__(self, option: Optional[str] = None, value: Optional[str] = None):
        self._option = option
        self._value = value 

    @property
    def option(self) -> str | None:
        return self._option

    @property
    def value(self) -> str | None:
        return self._value
    
    @property
    def positional_argument(self) -> bool:
        return self._option is None and self._value is not None

class UnrolledArgument(Argument):
    @classmethod
    def from_argument(cls, argument: Argument, unrolled_task: UnrolledTask):
        return cls(unrolled_task, argument.option, argument.value)

    def __init__(self, unrolled_task: UnrolledTask, option: Optional[str] = None, value: Optional[str] = None):
        super().__init__(option, value)
        self._unrolled_task = unrolled_task

    @property
    def date(self) -> datetime:
        return self._unrolled_task.date

    @property
    def unrolled_task(self) -> Task:
        return self._unrolled_task

class Dependency:

    def __init__(self, task_name: str, lag: Duration, date: datetime):
        # TODO somewhere check that tasks actually exist 
        self._task_name = task_name
        # TODO check that only is possible
        self._lag = lag
        self._date = date

    @property
    def task_name(self):
        return self._task_name

    @property
    def lag(self):
        return self._lag

    @property
    def date(self):
        return self._date

class UnrolledDependency:
    # TODO
    pass

class Task:
    """A task that is created during the unrolling of a cycle.
    """

    def __init__(
        self,
        name: str,
        command: str,
        inputs: Optional[list[Data]],
        outputs: Optional[list[Data]],
        arguments: Optional[list[Argument]] = None, 
        depends: Optional[list[Dependency]] = None,
    ):
        self._name = name
        self._command = expandvars(command)
        self._inputs = inputs
        self._outputs = outputs 
        self._arguments = arguments
        self._depends = depends 
        
    @property
    def name(self) -> str:
        return self._name

    @property
    def command(self) -> str:
        return self._command

    @property
    def inputs(self) -> list[Data]:
        return self._inputs

    @property
    def outputs(self) -> list[Data]:
        return self._outputs

    @property
    def arguments(self) -> list[Argument] | None:
        return self._arguments

    @property
    def depends(self) -> list[Dependency] | None:
        return self._depends

class UnrolledTask(Task):

    @classmethod
    def from_task(cls, task: Task, unrolled_cycle: UnrolledCycle):
        return cls(unrolled_cycle, task.name, task.command, task.inputs, task.outputs, task.arguments, task.depends)

    def __init__(
        self,
        unrolled_cycle: UnrolledCycle,
        name: str,
        command: str,
        inputs: list[Data],
        outputs: list[Data],
        arguments: list[Argument] = None, # todo should not be optional
        depends: list[Dependency] = None, # todo should not be optional
    ):
        super().__init__(name, command, inputs, outputs, arguments, depends)
        self._unrolled_cycle = unrolled_cycle
        # todo unroll depends
    
    def unroll_inputs(self) -> Generator[UnrolledData]:
        for input in self._inputs:
            for unrolled_input in input.unroll(self):
                yield unrolled_input 

    def unroll_outputs(self) -> Generator[UnrolledData]:
        for output in self._outputs:
            for unrolled_output in output.unroll(self):
                yield unrolled_output 

    def unroll_arguments(self) -> Generator[UnrolledArgument]:
        for argument in self.arguments:
            yield UnrolledArgument.from_argument(argument, self)

    @property
    def date(self) -> datetime:
        return self._unrolled_cycle.date

    @property
    def unrolled_cycle(self) -> UnrolledCycle:
        return self._unrolled_cycle

class Cycle:

    def __init__(self,
                name: str,
                tasks: list[Task],
                start_date: str | datetime,
                end_date: str | datetime,
                period: Optional[str | Duration] = None):
        self._name = name
        self._tasks = tasks
        self._start_date = start_date if isinstance(start_date, datetime) else datetime.fromisoformat(start_date)
        self._end_date = end_date if isinstance(end_date, datetime) else datetime.fromisoformat(end_date)

        if self._start_date > self._end_date:
            raise ValueError("For cycle {self._name!r} the start_date {start_date!r} lies after given end_date {end_date!r}.")

        self._period = period if period is None or isinstance(period, Duration) else parse_duration(period)
        if self._period is not None and TimeUtils.duration_is_less_equal_zero(self._period):
            raise ValueError(f"For cycle {self._name!r} the period {period!r} is negative or zero.")

    @property
    def name(self) -> str:
        return self._name

    @property
    def start_date(self) -> datetime:
        return self._start_date

    @property
    def end_date(self) -> datetime:
        return self._end_date

    @property
    def period(self) -> Duration:
        return self._period

    @property
    def tasks(self) -> list[Task]:
        return self._tasks

class UnrolledCycle(Cycle):

    @classmethod
    def from_cycle(cls, cycle: Cycle, date: datetime):
        return cls(date, cycle.tasks, cycle.name, cycle.start_date, cycle.end_date, cycle.period)

    def __init__(self,
                date: datetime,
                tasks: list[Task],
                name: str,
                start_date: str | datetime,
                end_date: str | datetime,
                period: Optional[str] = None):
        super().__init__(name, tasks, start_date, end_date, period)
        self._date = date
        self._tasks = [UnrolledTask.from_task(task, self) for task in tasks]

    def unroll_tasks(self) -> Generator[UnrolledTask]:
        for task in self._tasks:
            yield UnrolledTask.from_task(task, self)

    @property
    def date(self) -> datetime:
        return self._date

    @property
    def tasks(self) -> list[UnrolledTask]:
        return self._tasks

class Workflow:

    def __init__(self, name: str, cycles: list[Cycle]):
        self._name = name
        self._cycles = cycles
        self._validate_cycles()

        unrolled_outputs = set()
        for cycle in self.unroll_cycles():
            for task in cycle.unroll_tasks():
                for output in task.unroll_outputs():
                    unrolled_outputs.add(output)
        self._unrolled_outputs = unrolled_outputs


    def _validate_cycles(self):
        """Checks if the defined workflow is correctly referencing key names."""
        # TODO This is a placeholder function that I would like to split up into different validation functions later
        #      Since the invidual validation should happen before parameter assignment
        # - Check end_date > start_date -- DONE do test
        # - Check for undefined input/output in data -- DONE in wc._classes
        # - Check uniqueness (for the moment really a concern, since the only entry point yaml is ensuring uniqueness by overwrite)
        # - Check for undefined argument keys in input 
        # - Warning if output nodes that are overwritten by other tasks before usage, if this actually happens? 
        pass

    def unroll_cycles(self) -> Generator[UnrolledCycle]:
        for cycle in self._cycles:
            current_date = cycle.start_date
            while current_date <= cycle.end_date: 
                yield UnrolledCycle.from_cycle(cycle, current_date)
                if cycle.period is None:
                    break
                else:
                    current_date += cycle.period

    @property
    def name(self) -> str:
        return self._name

    @property
    def cycles(self) -> list[Cycle]:
        return self._cycles

    @property
    def unrolled_outputs(self) -> set[UnrolledData]:
        return self._unrolled_outputs