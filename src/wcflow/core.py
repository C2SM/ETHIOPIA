from __future__ import annotations

from datetime import datetime
from itertools import chain
from os.path import expandvars
from pathlib import Path
from typing import TYPE_CHECKING

from isoduration import parse_duration
from isoduration.types import Duration

from wcflow._utils import TimeUtils

if TYPE_CHECKING:
    from collections.abc import Generator


class _DataBase:
    def __init__(
        self,
        name: str,
        type: str,  # noqa: A002
        src: str,
        lag: list[Duration],
        date: list[datetime],
        arg_option: str | None,
    ):
        self._name = name

        self._src = src
        self._path = Path(expandvars(self._src))

        self._type = type
        if self._type not in ["file", "dir"]:
            msg = f"Data type {self._type!r} not supported. Please use 'file' or 'dir'."
            raise ValueError(msg)

        if len(lag) > 0 and len(date) > 0:
            msg = "Either 'lag' or 'date' can be nonempty. Not both."
            raise ValueError(msg)

        # COMMENT I think we should just disallow multiple lags, and enforce the user to write multiple lags
        #         I am not sure how this work with icon as it does not need positional arguments
        #         or rather how does it work with plugins
        if arg_option is not None and (len(lag) > 1 or len(date) > 1):
            msg = (
                "You cannot give an arg_option when multiple lags and dates are given. "
                "They must be positional arguments, since passing them to one option is ambiguous."
            )
            raise ValueError(msg)

        self._lag = lag
        self._date = date
        self._arg_option = arg_option

    @property
    def name(self) -> str:
        """The name of this data instance that is used as identifier."""
        return self._name

    @property
    def type(self) -> str:
        """The data type."""
        return self._type

    @property
    def src(self) -> str:
        return self._src

    @property
    def path(self) -> Path:
        return self._path

    @property
    def lag(self) -> list[Duration]:
        return self._lag

    @property
    def date(self) -> list[datetime]:
        return self._date

    @property
    def arg_option(self) -> str | None:
        return self._arg_option


class Data(_DataBase):
    def __init__(
        self,
        name: str,
        type: str,  # noqa: A002
        src: str,
        lag: list[Duration],
        date: list[datetime],
        arg_option: str | None,
    ):
        super().__init__(name, type, src, lag, date, arg_option)
        self._task: Task | None = None

    def unroll(self, unrolled_task: UnrolledTask) -> Generator[UnrolledData, None, None]:
        if len(self._date) == 0 and len(self._lag) == 0:
            yield UnrolledData.from_data(self, unrolled_task, unrolled_task.unrolled_date)

        for lag in self._lag:
            lagged_date = unrolled_task.unrolled_date + lag
            if (
                lagged_date >= unrolled_task.unrolled_cycle.start_date
                and lagged_date <= unrolled_task.unrolled_cycle.end_date
            ):
                yield UnrolledData.from_data(self, unrolled_task, lagged_date)

        for date in self._date:
            yield UnrolledData.from_data(self, unrolled_task, date)

    def __repr__(self) -> str:
        if self.task is None:
            identifier = f"{self.__class__.__name__} '{self.name}'"
        else:
            identifier = f"{self.__class__.__name__} '{self.name}' attached task '{self.task}'"
        return super().__repr__().replace(f"{self.__class__.__name__}", identifier)

    @property
    def task(self) -> Task | None:
        return self._task

    @task.setter
    def task(self, task: Task):
        if self._task is not None:
            msg = f"Data {self} was already assigned to task {self._task}. Cannot assign task to task {task}."
            raise ValueError(msg)
        self._task = task


class UnrolledData(_DataBase):
    """
    Data that are created during the unrolling of a cycle.
    This class should be only initiated through unrolling a cycle.
    """

    @classmethod
    def from_data(cls, data: Data, unrolled_task: UnrolledTask, unrolled_date: datetime):
        return cls(unrolled_task, unrolled_date, data.name, data.type, data.src, data.lag, data.date, data.arg_option)

    def __init__(
        self,
        unrolled_task: UnrolledTask,
        unrolled_date: datetime,
        name: str,
        type: str,  # noqa: A002
        src: str,
        lag: list[Duration],
        date: list[datetime],
        arg_option: str | None,
    ):
        super().__init__(name, type, src, lag, date, arg_option)
        self._unrolled_task = unrolled_task
        self._unrolled_date = unrolled_date

    def __repr__(self) -> str:
        if self.unrolled_task is None:
            identifier = f"{self.__class__.__name__} '{self.name}' with date {self.unrolled_date}"
        else:
            identifier = f"{self.__class__.__name__} '{self.name}' with date {self.unrolled_date} attached to task {self.unrolled_task}"
        return super().__repr__().replace(f"{self.__class__.__name__}", identifier)

    @property
    def unrolled_date(self) -> datetime:
        return self._unrolled_date

    @property
    def unrolled_task(self) -> UnrolledTask:
        return self._unrolled_task


class _DependencyBase:
    def __init__(self, depend_on_task_name: str, lag: list[Duration], date: list[datetime], cycle_name: str | None):
        self._depend_on_task_name = depend_on_task_name
        if len(lag) > 0 and len(date) > 0:
            msg = "Only one key 'lag' or 'date' is allowed. Not both."
            raise ValueError(msg)

        self._lag = lag
        self._date = date
        self._cycle_name = cycle_name

    @property
    def depend_on_task_name(self) -> str:
        return self._depend_on_task_name

    @property
    def lag(self) -> list[Duration]:
        return self._lag

    @property
    def date(self) -> list[datetime]:
        return self._date

    @property
    def cycle_name(self) -> str | None:
        return self._cycle_name


class Dependency(_DependencyBase):
    def __init__(self, depend_on_task_name: str, lag: list[Duration], date: list[datetime], cycle_name: str | None):
        super().__init__(depend_on_task_name, lag, date, cycle_name)
        self._task: Task | None = None

    def unroll(self, unrolled_task: UnrolledTask) -> Generator[UnrolledDependency, None, None]:
        if len(self._date) == 0 and len(self._lag) == 0:
            yield UnrolledDependency.from_dependency(self, unrolled_task, unrolled_task.unrolled_date)

        for lag in self._lag:
            lagged_date = unrolled_task.unrolled_date + lag
            if (
                lagged_date >= unrolled_task.unrolled_cycle.start_date
                and lagged_date <= unrolled_task.unrolled_cycle.end_date
            ):
                yield UnrolledDependency.from_dependency(self, unrolled_task, lagged_date)

        for date in self._date:
            yield UnrolledDependency.from_dependency(self, unrolled_task, date)

    @property
    def task(self) -> Task | None:
        return self._task

    @task.setter
    def task(self, task: Task):
        if self.task is not None:
            msg = f"Dependency was already assigned to task {self.task}. Cannot assign to task {task}."
            raise ValueError(msg)
        self._task = task

    def __repr__(self) -> str:
        if self._cycle_name is None:
            identifier = f"{self.__class__.__name__} on task '{self.depend_on_task_name}' attached to task {self.task}"
        else:
            identifier = f"{self.__class__.__name__} on task '{self.depend_on_task_name}' in cycle '{self.cycle_name}' attached to task {self.task}"
        return super().__repr__().replace(f"{self.__class__.__name__}", identifier)


class UnrolledDependency(_DependencyBase):
    """
    This class should be only initiated through unrolling a cycle.
    """

    @classmethod
    def from_dependency(cls, depend: Dependency, unrolled_task: UnrolledTask, unrolled_date: datetime):
        return cls(unrolled_task, unrolled_date, depend.depend_on_task_name, depend.lag, depend.date, depend.cycle_name)

    def __init__(
        self,
        unrolled_task: UnrolledTask,
        unrolled_date: datetime,
        depend_on_task_name: str,
        lag: list[Duration],
        date: list[datetime],
        cycle_name: str | None,
    ):
        super().__init__(depend_on_task_name, lag, date, cycle_name)
        self._unrolled_task = unrolled_task
        self._unrolled_date = unrolled_date

    def __repr__(self) -> str:
        if self._cycle_name is None:
            identifier = (
                f"{self.__class__.__name__} on task '{self.depend_on_task_name}' with date {self.unrolled_date}"
            )
        else:
            identifier = f"{self.__class__.__name__} on task '{self.depend_on_task_name}' in cycle '{self.cycle_name}' with date {self.unrolled_date}"
        return super().__repr__().replace(f"{self.__class__.__name__}", identifier)

    @property
    def depend_on_task(self) -> UnrolledTask:
        """
        throws error if not found
        """
        # for now we only support looking in the same cycle
        workflow = self._unrolled_task.unrolled_cycle.workflow
        if self._cycle_name is None:
            tasks_to_search = [
                cycle.unrolled_tasks for cycle in workflow.unrolled_cycles if cycle.unrolled_date == self._unrolled_date
            ]
            potential_tasks = [
                task for task in chain.from_iterable(tasks_to_search) if task.name == self._depend_on_task_name
            ]
            if len(potential_tasks) > 1:
                msg = (
                    f"Found multiple instances of the task '{self._depend_on_task_name}' with date {self._unrolled_date}"
                    " for dependency of the task {self._unrolled_task}. Please specify a cycle name."
                )
                raise ValueError(msg)
            if len(potential_tasks) == 0:
                msg = (
                    f"Found no instance of the task '{self._depend_on_task_name}' with date {self._unrolled_date}"
                    f" for dependency attached to task {self._unrolled_task}."
                )
                raise ValueError(msg)
            return potential_tasks[0]

        cycle = workflow.unrolled_cycles_map[(self._cycle_name, self._unrolled_date)]
        return cycle.unrolled_tasks_map[self._depend_on_task_name]

    @property
    def unrolled_task(self) -> UnrolledTask:
        return self._unrolled_task

    @property
    def unrolled_date(self) -> datetime:
        return self._unrolled_date


class _TaskBase:
    """
    Common class for Task and UnrolledTask to reduce code duplications
    """

    def __init__(
        self,
        name: str,
        command: str,
        inputs: list[Data],
        outputs: list[Data],
        depends: list[Dependency],
        command_option: str | None,
    ):
        self._name = name
        self._command = expandvars(command)
        self._inputs = inputs
        self._outputs = outputs
        self._depends = depends
        self._command_option = command_option

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
    def command_option(self) -> str | None:
        return self._command_option

    @property
    def depends(self) -> list[Dependency]:
        return self._depends


class Task(_TaskBase):
    """A task that is created during the unrolling of a cycle."""

    def __init__(
        self,
        name: str,
        command: str,
        inputs: list[Data],
        outputs: list[Data],
        depends: list[Dependency],
        command_option: str | None,
    ):
        super().__init__(name, command, inputs, outputs, depends, command_option)
        for input_ in inputs:
            input_.task = self
        for output in outputs:
            output.task = self
        for depend in depends:
            depend.task = self
        self._cycle: Cycle | None = None

    def __repr__(self) -> str:
        identifier = f"Task '{self.name}'"
        if self.cycle is not None:
            identifier += f" in cycle {self.cycle.name}"
        return super().__repr__().replace("Task", identifier)

    def unroll(self, unrolled_cycle: UnrolledCycle) -> Generator[tuple[str, UnrolledTask], None, None]:
        # an unrolled task is just one task, since the date is determined
        # by the cycle, but we keep the pattern for consistency
        unrolled_task = UnrolledTask.from_task(self, unrolled_cycle)
        yield unrolled_task.name, unrolled_task

    @property
    def cycle(self) -> Cycle | None:
        return self._cycle

    @cycle.setter
    def cycle(self, cycle: Cycle):
        if self._cycle is not None:
            msg = f"Task {self} was already assigned to cycle {self._cycle}. Cannot assign task to cycle {cycle}."
            raise ValueError(msg)
        self._cycle = cycle


class UnrolledTask(_TaskBase):
    """
    This class should be only initiated through unrolling a cycle.
    """

    @classmethod
    def from_task(cls, task: Task, unrolled_cycle: UnrolledCycle):
        return cls(
            unrolled_cycle, task.name, task.command, task.inputs, task.outputs, task.depends, task.command_option
        )

    def __init__(
        self,
        unrolled_cycle: UnrolledCycle,
        name: str,
        command: str,
        inputs: list[Data],
        outputs: list[Data],
        depends: list[Dependency],
        command_option: str | None,
    ):
        super().__init__(name, command, inputs, outputs, depends, command_option)
        self._unrolled_cycle = unrolled_cycle
        self._unrolled_inputs = list(self.unroll_inputs())
        self._unrolled_outputs = list(self.unroll_outputs())
        self._unrolled_depends = list(self.unroll_depends())

    def __repr__(self) -> str:
        if self.unrolled_cycle is None:
            identifier = f"Task '{self.name}' with date {self.unrolled_date}"
        else:
            identifier = f"Task '{self.name}' in cycle {self.unrolled_cycle.name} with date {self.unrolled_date}"
        return super().__repr__().replace("Task", identifier)

    def unroll_inputs(self) -> Generator[UnrolledData, None, None]:
        """
        Outputs the inputs together with a unique identifier within the task
        """
        for input_ in self._inputs:
            yield from input_.unroll(self)

    def unroll_outputs(self) -> Generator[UnrolledData, None, None]:
        for output in self._outputs:
            yield from output.unroll(self)

    def unroll_depends(self) -> Generator[UnrolledDependency, None, None]:
        for depend in self._depends:
            yield from depend.unroll(self)

    @property
    def unrolled_inputs(self) -> list[UnrolledData]:
        return self._unrolled_inputs

    @property
    def unrolled_outputs(self) -> list[UnrolledData]:
        return self._unrolled_outputs

    @property
    def unrolled_depends(self) -> list[UnrolledDependency]:
        return self._unrolled_depends

    @property
    def unrolled_date(self) -> datetime:
        return self._unrolled_cycle.unrolled_date

    @property
    def unrolled_cycle(self) -> UnrolledCycle:
        return self._unrolled_cycle


class _CycleBase:
    def __init__(
        self,
        name: str,
        tasks: list[Task],
        start_date: str | datetime,
        end_date: str | datetime,
        period: str | Duration | None = None,
    ):
        self._name = name
        self._tasks = tasks
        self._start_date = start_date if isinstance(start_date, datetime) else datetime.fromisoformat(start_date)
        self._end_date = end_date if isinstance(end_date, datetime) else datetime.fromisoformat(end_date)

        if self._start_date > self._end_date:
            msg = "For cycle {self} the start_date {start_date} lies after given end_date {end_date}."
            raise ValueError(msg)

        self._period = period if period is None or isinstance(period, Duration) else parse_duration(period)
        if self._period is not None and TimeUtils.duration_is_less_equal_zero(self._period):
            msg = f"For cycle {self} the period {period} is negative or zero."
            raise ValueError(msg)

        task_names = set()
        for task in self._tasks:
            if task.name in task_names:
                msg = f"List of tasks does contain tasks with duplicate names. The task name '{task.name}' has been found twice."
                raise ValueError(msg)
            task_names.add(task.name)

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
    def period(self) -> Duration | None:
        return self._period

    @property
    def tasks(self) -> list[Task]:
        return self._tasks


class Cycle(_CycleBase):
    def __init__(
        self,
        name: str,
        tasks: list[Task],
        start_date: str | datetime,
        end_date: str | datetime,
        period: str | Duration | None,
    ):
        super().__init__(name, tasks, start_date, end_date, period)
        for task in self._tasks:
            task.cycle = self

        self._workflow: Workflow | None = None

    def __repr__(self) -> str:
        if self.workflow is None:
            identifier = f"Cycle '{self.name}'"
        else:
            identifier = f"Cycle '{self.name}' in workflow {self.workflow.name}"
        return super().__repr__().replace("Cycle", identifier)

    def unroll(self) -> Generator[tuple[str, datetime, UnrolledCycle], None, None]:
        if self._workflow is None:
            msg = f"Cannot unroll cycle {self} because it was not attached to a workflow before."
            raise ValueError(msg)
        current_date = self._start_date
        while current_date <= self._end_date:
            unrolled_cycle = UnrolledCycle.from_cycle(self, current_date, self._workflow)
            yield unrolled_cycle.name, unrolled_cycle.unrolled_date, unrolled_cycle
            if self._period is None:
                break
            else:
                current_date += self._period

    @property
    def workflow(self) -> Workflow | None:
        return self._workflow

    @workflow.setter
    def workflow(self, workflow: Workflow):
        if self._workflow is not None:
            msg = f"Cycle {self} was already assigned to workflow {self._workflow}. Cannot assign cycle to workflow {workflow}."
            raise ValueError(msg)
        self._workflow = workflow


class UnrolledCycle(_CycleBase):
    """
    This class should be only initiated through unrolling a cycle.
    """

    @classmethod
    def from_cycle(cls, cycle: Cycle, unrolled_date: datetime, workflow: Workflow):
        return cls(unrolled_date, cycle.name, cycle.tasks, cycle.start_date, cycle.end_date, cycle.period, workflow)

    def __init__(
        self,
        unrolled_date: datetime,
        name: str,
        tasks: list[Task],
        start_date: str | datetime,
        end_date: str | datetime,
        period: str | Duration | None,
        workflow: Workflow,
    ):
        super().__init__(name, tasks, start_date, end_date, period)

        self._unrolled_date = unrolled_date

        self._unrolled_tasks_map = dict(self.unroll_tasks())
        self._workflow = workflow

    def __repr__(self) -> str:
        if self.workflow is None:
            identifier = f"UnrolledCycle '{self.name}' with date {self.unrolled_date}"
        else:
            identifier = f"UnrolledCycle '{self.name}' in workflow {self.workflow.name} with date {self.unrolled_date}"
        return super().__repr__().replace("UnrolledCycle", identifier)

    def unroll_tasks(self) -> Generator[tuple[str, UnrolledTask], None, None]:
        for task in self._tasks:
            yield from task.unroll(self)

    @property
    def unrolled_tasks(self) -> list[UnrolledTask]:
        return list(self._unrolled_tasks_map.values())

    @property
    def unrolled_tasks_map(self) -> dict[str, UnrolledTask]:
        return self._unrolled_tasks_map

    @property
    def unrolled_date(self) -> datetime:
        return self._unrolled_date

    @property
    def workflow(self) -> Workflow:
        return self._workflow


class Workflow:
    def __init__(self, name: str, cycles: list[Cycle]):
        self._name = name
        self._cycles = cycles
        for cycle in self._cycles:
            cycle.workflow = self
        self._validate_cycles()
        self._unrolled_cycles_map = {(name, date): cycle for name, date, cycle in self.unroll_cycles()}

        unrolled_outputs = []
        for unrolled_cycle in self.unrolled_cycles:
            for unrolled_task in unrolled_cycle.unrolled_tasks:
                unrolled_outputs.extend(unrolled_task.unrolled_outputs)
        self._unrolled_outputs = unrolled_outputs

    def _validate_cycles(self):
        """Checks if the defined workflow is correctly referencing key names."""
        cycle_names = set()
        for cycle in self._cycles:
            if cycle.name in cycle_names:
                msg = f"List of cycles does contain cycles with duplicate names. The cycle name '{cycle.name}' has been found twice."
                raise ValueError(msg)
            cycle_names.add(cycle.name)

    def unroll_cycles(self) -> Generator[tuple[str, datetime, UnrolledCycle], None, None]:
        for cycle in self._cycles:
            yield from cycle.unroll()

    @property
    def name(self) -> str:
        return self._name

    @property
    def cycles(self) -> list[Cycle]:
        return self._cycles

    def is_available_on_init(self, data: UnrolledData) -> bool:
        """Determines if the data is available on init of the workflow."""

        def equal_check(output: UnrolledData) -> bool:
            return output.name == data.name and output.unrolled_date == data.unrolled_date

        return len(list(filter(equal_check, self._unrolled_outputs))) == 0

    @property
    def unrolled_cycles(self) -> list[UnrolledCycle]:
        return list(self._unrolled_cycles_map.values())

    @property
    def unrolled_cycles_map(self) -> dict[tuple[str, datetime], UnrolledCycle]:
        return self._unrolled_cycles_map
