#!/usr/bin/env python3

from datetime import datetime
from isoduration import parse_duration
from isoduration.formatter import Duration
from node_graph.socket import NodeSocket
import yaml
from pathlib import Path
import argparse
from copy import deepcopy
from pprint import pprint
from typing import Tuple, Dict, List, Optional
from collections.abc import Iterable

from aiida_workgraph import WorkGraph, workgraph
from aiida_workgraph.task import Task
from aiida_workgraph.sockets.built_in import SocketGeneral
from aiida.orm import SinglefileData, RemoteData, FolderData, DataNode, Node
from aiida import load_profile
from aiida.orm import load_code

load_profile()

# This is hack to aiida-workgraph, since we are not sure if we keep this behavior, so if a clean implementation is worth the time
def prepare_for_shell_task(task: dict, kwargs: dict) -> dict:
    """Prepare the inputs for ShellTask"""
    from aiida_shell.launch import prepare_code, convert_nodes_single_file_data
    from aiida.common import lang
    from aiida.orm import AbstractCode

    print("Task  type: ShellTask.")
    command = kwargs.pop("command", None)
    resolve_command = kwargs.pop("resolve_command", False)
    metadata = kwargs.pop("metadata", {})
    # setup code
    if isinstance(command, str):
        computer = (metadata or {}).get("options", {}).pop("computer", None)
        code = prepare_code(command, computer, resolve_command)
    else:
        lang.type_check(command, AbstractCode)
        code = command
    # update the tasks with links
    nodes = convert_nodes_single_file_data(kwargs.pop("nodes", {}))
    # find all keys in kwargs start with "nodes."
    for key in list(kwargs.keys()):
        if key.startswith("nodes."):
            nodes[key[6:]] = kwargs.pop(key)
    metadata.update({"call_link_label": task["name"]})

    default_outputs = set(["remote_folder", "remote_stash", "retrieved", "_outputs", "_wait", "stdout", "stderr"]) 
    task_outputs = set([task["outputs"][i]["name"] for i in range(len(task["outputs"]))])
    task_outputs = task_outputs.union(set(kwargs.pop("outputs", [])))
    missing_outputs = task_outputs.difference(default_outputs)
    inputs = {
        "code": code,
        "nodes": nodes,
        "filenames": kwargs.pop("filenames", {}),
        "arguments": kwargs.pop("arguments", []),
        "outputs": list(missing_outputs),
        "parser": kwargs.pop("parser", None),
        "metadata": metadata or {},
    }
    return inputs
import aiida_workgraph.engine.utils
aiida_workgraph.engine.utils.prepare_for_shell_task = prepare_for_shell_task



def sanitize_link_label(node_name):
    import re

    node_name_sanitized = (
        node_name.replace(" ", "_")
        .replace(":", "_")
        .replace("-", "_")
        .replace("@", "_")
        .replace("&", "_")
    )
    node_name_sanitized = re.sub(r"_+", "_", node_name_sanitized)
    return node_name_sanitized


# =======
# Classes
# =======
# todo: Extend WcTask and WcData with required properties
# todo: AG: date unrolling
# todo: JG: Extend classes
# todo: Dict with tuples as keys

# Maybe useful helper?
#class WcDatedTask:
#    @property
#    def date(self):
#        return
#
#    @property
#    def task_node(self):
#        return
#class WcDatedData(WcData):
#    @property
#    def aiida_task(self):
#        return
#
#    @property
#    def aiida_node(self) -> DataNode | NodeSocket:
#        return
#class WcCycleTask:
#    """
#    An object constructed from the task definition within a cycle
#    """
#    @property
#    def argument(self) ->:
#        return
#
#class WcCycleTaskArgument:
#    pass
#class WcCycleTaskInput:
#    pass
#class WcCycleTaskOutput:
#    pass
class TimeUtils:
    @staticmethod
    def duration_is_negative(duration: Duration) -> bool:
        if duration.date.years < 0 or duration.date.months < 0 or duration.date.days < 0 or \
           duration.time.hours < 0 or duration.time.minutes < 0 or duration.time.seconds < 0:
            return True
        return False


class WcTask:
    def __init__(
        self,
        name: str,
        command: str,
    ):
        self._name = name
        self._command = command
        self._input = input if input is not None else []
        self._output = output if output is not None else []
        self._argument = argument if argument is not None else {}
        self._depends = depends if depends is not None else []

    @property
    def name(self) -> str:
        return self._name

    @property
    def command(self) -> str:
        return self._command

    @property
    def input(self) -> List[str]:
        return self._input

    @property
    def output(self) -> List[str]:
        return self._output

    @property
    def argument(self) -> str | Dict[str, str | None]:
        return self._argument

    def __str__(self):
        return "\n\nWcTask\n" + "\n".join(
            f"{k}: {v}" for k, v in vars(self).items() if not k.startswith("_")
        )

    def __repr__(self):
        return "\n\nWcTask\n" + "\n".join(
            f"{k}: {v}" for k, v in vars(self).items() if not k.startswith("_")
        )

class WcData:
    """
    Parses an entry of the data key of WC yaml file.
    """
    @classmethod
    def from_spec(cls, name: str, spec: dict):
        for key in spec.keys():
            if key not in WcData.valid_spec_keys():
                raise ValueError(f"In data {name!r} found invalid name {key!r}. Key must be in {WcData.valid_spec_keys()}")
        for key in WcData.required_spec_keys():
            if key not in spec.keys():
                raise ValueError(
                    f"When creating data instance for {name!r}, {key!r} was given in the specification"
                )
        return cls(name, **spec)

    def __init__(self, name: str, type: str, src: str):
        self._name = name

        self._src = src 

        self._type = type
        if self._type not in ["file", "dir"]:
            raise ValueError(f'Data type {self._type!r} not supported. Please use \'file\' or \'dir\'.')

    @property
    def name(self) -> str:
        """The name of this data instance."""
        return self._name

    @property
    def type(self) -> str:
        """The type of this data instance."""
        return self._type

    @property
    def path(self) -> Path:
        """The path of this data instance."""
        return Path(self._src)

    @staticmethod
    def valid_spec_keys() -> List[str]:
        return ["type", "src"]
    
    @staticmethod
    def required_spec_keys() -> List[str]:
        return ["type", "src"]

    def has_abs_path(self) -> bool:
        return self.path.is_absolute()

class WcCycle:

    @classmethod
    def from_spec(cls, name: str, spec: dict):
        for key in spec.keys():
            if key not in WcCycle.valid_spec_keys():
                raise ValueError(f"Cycle {name!r} found invalid key {key!r}. Key must be in {WcCycle.valid_spec_keys()}")
        for key in WcCycle.required_spec_keys():
            if key not in spec.keys():
                raise ValueError(
                    f"When creating cycle instance for {name!r}, {key!r} was given in the specification"
                )
        return cls(name, **spec)

    def __init__(self, name: str, start_date: str, end_date: str, tasks: Dict[str, dict], period: Optional[str] = None):
        self._name = name

        self._start_date = datetime.fromisoformat(start_date)
        self._end_date = datetime.fromisoformat(end_date)
        if self._start_date > self._end_date:
            raise ValueError("For cycle {self._name!r} the start_date {start_date!r} lies after given end_date {end_date!r}.")

        self._period = None if period is None else parse_duration("P0M")
        if self._period is not None and TimeUtils.duration_is_negative(self._period):
            raise ValueError("For cycle {self._name!r} the period {period!r} is negative.")

        self._tasks = tasks
        self._input = {}
        for task_name, task_spec in self._task.items():
            WcCycleTask.from_spec(task_spec)

        def from_spec
            if (inputs := task_spec.get("input")) is None:
                self._input[task_name] = []
            else:
                self._input[task_name] = WcCycleTaskData.from_spec(task_spec)

                raise ValueError(f"Task {task_name!r} in cycle {cycle._name!r} has no input key. Please specify one even when no input")

        self._input = {}
        if task_spec.get("input") is None
            self._input[task_name] = []}
        [WcCycleTaskData() for input_ in task_spec.get("input")]
        # COMMENT: This should be covered by a grammar check later on, not sure if keeping here
        for task_name, task_spec in self._task.items():
            if (inputs := task_spec.get("input")) is None:
                raise ValueError(f"Task {task_name!r} in cycle {cycle._name!r} has no input key. Please specify one even when no input")
            if task_spec.get("output")

    @staticmethod
    def valid_spec_keys() -> List[str]:
        return ["tasks", "period", "start_date", "end_date"]

    @staticmethod
    def required_spec_keys() -> List[str]:
        return ["tasks", "start_date", "end_date"]

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
    def tasks(self) -> Dict[str, dict]:
        return self._tasks

    def get_task_input(self, task_name: str) -> List[WcCycleTaskData]:
        return self._input[task_name]


class WcFullSpecData:
    @classmethod
    def from_spec(self, name, spec)
        return
    def __init__(self, name: str, lag: Optonal[str] = None, Optiona):

    @property
    def get_date(self) -> Dict[str, dict]:
        return self._tasks


class WcFullSpecTask(WcTask):
    def __init__(
        self,
        name: str,
        command: str,
        input: Optional[List[str]] = None,
        output: Optional[List[str]] = None,
        argument: Optional[str | Dict[str, str | None]] = None,
        depends: Optional[List[str]] = None,
    ):
        self._name = name
        self._command = command
        self._input = input if input is not None else []
        self._output = output if output is not None else []
        self._argument = argument if argument is not None else {}
        self._depends = depends if depends is not None else []

# TODO I dont use consistently name and key
class WcWorkflow:

    @classmethod
    def from_yaml(cls, config):
        config_path = Path(config)
        loaded_config = yaml.safe_load(config_path.read_text())
        return cls.from_spec(config_path.stem, loaded_config)

    @classmethod
    def from_spec(cls, name: str, spec: dict):
        # TODO: validate spec key words
        return cls(name, **spec)

    def __init__(self, name: str, start_date: str, end_date: str, cycles: Dict[str, dict], tasks: Dict[str, dict], data: Dict[str, dict]):
        self._start_date = datetime.fromisoformat(start_date)
        self._end_date = datetime.fromisoformat(end_date)
        self._name = name

        # Needed for date indexing
        self._validate_parameters()
        # TOOD would be nicer if we give spec as kwargs
        self._wc_data = {name: WcData.from_spec(name, spec) for name, spec in data.items()}
        self._wc_cycles = WcWorkflow._create_wc_cycles(cycles, start_date, end_date)
        self._wc_tasks = WcWorkflow._create_wc_tasks(self._wc_cycles.values(), tasks)

        self._workgraph = WorkGraph(self._name)

        # aiida objects with dated labels 
        # accesible by (yaml key name, date)
        #self._data_output_names = []

        # TODO maybe use as property? Since information is available in workgraph, but wg is super hacky and unrobust
        #      maybe use workgraph_data_nodes?
        self._aiida_data_nodes: Dict[Tuple[str, datetime], DataNode] = {}
        # TODO rename _aiida_output_socket_nodes
        self._aiida_socket_nodes: Dict[Tuple[str, datetime], NodeSocket] = {}
        #self._aiida_nodes: Dict[Tuple[str, datetime], NodeSocket] = {}

        #self._aiida_task_input_output_nodes: Dict[Tuple[str, datetime], Union[DataNode, NodeSocket]] = {}
        # Input/Output name -> Input/Output node 
        #self._aiida_input_output_nodes: Dict[Tuple[str, datetime], Tuple(Union[DataNode, NodeSocket, TaskNode)]] = {}
        # Input/Output name -> task node 
        self._aiida_task_nodes: Dict[Tuple[str, datetime], Task] = {}

        self._add_aiida_data_nodes()
        self._add_aiida_task_nodes()
        self._add_aiida_links()

    @staticmethod
    def _create_wc_cycles(cycles: Dict[str, dict], start_date: str, end_date: str) -> Dict[str, WcCycle]:
        wc_cycles = {}
        for cycle_name, cycle_spec in cycles.items():
            cycles_spec = deepcopy(cycle_spec)
            if "start_date" not in cycle_spec:
                cycles_spec["start_date"] = start_date
            if "end_date" not in cycle_spec:
                cycles_spec["end_date"] = end_date
            wc_cycles[cycle_name] = WcCycle.from_spec(cycle_name, cycle_spec)
        return wc_cycles

    @staticmethod
    def _create_wc_tasks(cycles: Iterable[WcCycle], tasks: Dict[str, dict]) -> Dict[str, WcTask]:
        # checks if no task is repetitive in cycles
        tasks_in_cycles = set({}) 
        for cycle in cycles:
            cycle_task_keys = set(cycle.tasks.keys()) 
            if len(intersection := tasks_in_cycles.intersection(cycle_task_keys)) != 0:
                raise ValueError(f"Found tasks {intersection} in two cycles. Tasks cannot be used in multiple cycles.")
            tasks_in_cycles.union(cycle_task_keys)

        # gets the task specification from cycles
        cycles_tasks_spec = {}
        for cycle in cycles:
            cycles_tasks_spec.update(cycle.tasks)
        all_task_keys = set(cycles_tasks_spec.keys()).union(set(tasks.keys()))

        # Because the task definitions can be specified in tasks and a cycle we have to gather the definitions from both places
        wc_tasks = {}
        # COMMENT Logic is not so nice since the cycle name cannot be retrieved for error message
        for task_key in all_task_keys:
            task_spec_keys_from_cycles = cycles_tasks_spec.get(task_key, {})
            task_spec_keys_from_tasks = tasks.get(task_key, {})
            if len(intersection := set(task_spec_keys_from_cycles).intersection(set(task_spec_keys_from_tasks))) != 0: 
                raise ValueError(f"For task {task_key!r} found repetitive definitions for {intersection!r} in tasks and a cycle. Please define these only in tasks or cycles.tasks")
            task_kwargs = task_spec_keys_from_cycles.update(task_spec_keys_from_tasks)
            wc_tasks[task_key] = WcTask(task_key, **task_kwargs)

        return wc_tasks


    def _validate_parameters(self):
        """Checks if the defined workflow is correctly referencing key names."""
        # TODO This is a placeholder function that I would like to split up into different validation functions later
        #      Since the invidual validation should happen before parameter assignment
        # - Check end_date > start_date 
        # - Check for undefined input/output in data
        # - Check for undefined argument keys in input
        # - Check that all key names that are used for aiida labels, are valid key values
        # - Warning if output nodes that are overwritten by other tasks before usage, if this actually happens? 
        pass

    def _add_aiida_data_nodes(self):
        """
        Nodes that correspond to data that are available on initialization of the workflow
        """
        # retrieve a list of data that is the output of a task
        outputs_name = []
        for cycle in self._wc_cycles.values():
            for task_name in cycle.tasks.keys():
                # TODO consider lag ['initial'] that speciifes that a file is there on initialization
                outputs_name.extend(self._wc_tasks[task_name].output)

        for cycle in self._wc_cycles.values():
            for task_name in cycle.tasks.keys():
                for input_name in self._wc_tasks[task_name].input:
                    if input_name not in outputs_name:  
                        self._add_aiida_data_node(input_name, cycle.start_date)

    @staticmethod
    def get_aiida_label(name: str, date: datetime):
        """
        """
        # COMMENT I am not sure how to handle aiida stuff consistentl
        #         Thought about moving aiida_creation to WcData/Task
        #         but these things are too entangled with the workgraph
        return f"{name}_{date}"

    def _add_aiida_data_node(self, input_name: str, date: datetime):
        """
        Create an :class:`aiida.orm.Node` instance from this wc data instance.

        :param input_name: Name from the input that should be added to workgraph.
        :param date: The date that is used as the label of the form `<self.name>_<date>`
        """
        label = WcWorkflow.get_aiida_label(self._name, date)
        wc_data = self._wc_data[input_name]
        if wc_data.type == "file":
            aiida_data_node = SinglefileData(label=label, file=wc_data.path.resolve())

        elif wc_data.type == "dir":
            aiida_data_node = FolderData(label=label, tree=wc_data.path.resolve())
        else:
            raise ValueError(f'Data type {wc_data.type!r} not supported. Please use \'file\' or \'dir\'.')

        self._aiida_data_nodes[(input_name, date)] = aiida_data_node

    def _add_aiida_task_nodes(self):
        for cycle in self._wc_cycles.values():
            self._add_aiida_task_nodes_from_cycle(cycle)

    def _add_aiida_task_nodes_from_cycle(self, cycle: WcCycle):
        cycle_current_date = cycle.start_date
        while cycle_current_date <= cycle.end_date: 
            for name, _ in cycle.tasks:
                self._add_aiida_task_node(name, cycle_current_date)
            if cycle.period is None:
                break
            else:
                cycle_current_date += cycle.period

    def _add_aiida_task_node(self, task_name, date):
        workgraph_task = self._workgraph.tasks.new(
            "ShellTask",
            name=WcWorkflow.get_aiida_label(task_name, date),
            command=self._wc_tasks[task_name].command,
            # ... more properties that are taken from wc_task
        )
        workgraph_task.set({'arguments':[]})
        workgraph_task.set({"nodes": {}})
        self._aiida_task_nodes[(task_name, date)] = workgraph_task

    def _add_aiida_links(self):
        for cycle in self._wc_cycles.values():
            self._add_aiida_links_from_cycle(cycle)

    def _add_aiida_links_from_cycle(self, cycle: WcCycle):
        cycle_current_date = cycle.start_date
        while cycle_current_date <= cycle.end_date: 
            for task_name, cycle_task_spec in cycle.tasks.items():
                wc_task = self._wc_tasks[task_name]
                wc_full_spec_task = wc_task.to_full_spec_task(cycle_task_spec, cycle_current_date)
                for wc_input in wc_full_spec_task.wc_input:
                    input_date = wc_input.get_date(cycle_current_date)
                    if input_date >= self._start_date and input_date <= self._end_date:
                        self._link_input_to_task(task_name, wc_input.input_name, input_date)
                for argument in wc_task.argument: 
                    self._link_argument_to_task(task_name, argument, cycle_current_date)
                for output_name in wc_task.output: 
                    self._link_output_to_task(task_name, output_name, cycle_current_date)
            if cycle.period is None:
                break
            else:
                cycle_current_date = cycle_current_date + cycle.period

    def _link_input_to_task(self, task_name, input_name: str, date: datetime):
        workgraph_task = self._aiida_task_nodes[(task_name, date)]
        workgraph_task.inputs.new("General", f"nodes.{input_name}")

        if (data_node := self._aiida_data_nodes[(input_name, date)] is not None):
            if (nodes := workgraph_task.inputs.get("nodes")) is None:
                # TODO can Julian/Xing check if this is correct error message? 
                raise ValueError(f"Workgraph task {workgraph_task.name!r} did not initialize input nodes in the workgraph before linking. This is a bug in the code, please contact devevlopers.")
            nodes.value.update({f"{input_name}": data_node})
        elif (output_socket := self._aiida_socket_nodes[(input_name, date)] is not None):
            self._workgraph.links.new(output_socket, task.inputs[f"nodes.{input_name}"])
        else:
            raise ValueError("Input data node was neither found in socket nodes nor in data nodes. The task {task_name!r} must have dependencies on inputs before they are created.")

    def _link_argument_to_task(self, task_name: str, argument: str | Dict[str, str | None], date: datetime):
        workgraph_task = self._aiida_task_nodes[(task_name, date)]
        if (workgraph_task_arguments := workgraph_task.inputs.get("arguments")) is None:
            raise ValueError(f"Workgraph task {workgraph_task.name!r} did not initialize argument nodes in the workgraph before linking. This is a bug in the code, please contact devevlopers.")
        # 4 options for arguments
        # argument options:
        # - input: preproc_output --> "command --input {preproc_output}"
        # - i: preproc_output --> "command -i {preproc_output}"
        # - v: null --> "command -v"
        # - verbose: null --> "command --verbose"
        # - input_file -->"command {input_file}"
        if argument is str:
            workgraph_task_arguments.value.append(f"{{{argument}}}")
        elif argument is dict and len(argument) == 1:
            argument_key = next(iter(argument.keys()))
            if len(argument_key) == 1: 
                workgraph_task_arguments.value.append(f"-{argument_key}")
            else:
                workgraph_task_arguments.value.append(f"--{argument_key}")
            argument_value = next(iter(argument.values()))
            if argument_value is not None: 
                # argument less parametrization key: null
                workgraph_task_arguments.value.append(f"{{{argument_value}}}")
        else:
            raise ValueError("Argument {argument!r} not supported. Please only use arguments of the form 'key: value' or 'key'")

    def _link_output_to_task(self, task_name: str, output_name: str, date: datetime):
        workgraph_task = self._aiida_task_nodes[(task_name, date)]
        output_socket = workgraph_task.outputs.new("General", output_name)
        self._aiida_socket_nodes[(output_name, date)] = output_socket

    #def _add_nodes_from_cycle(self, cycle):
    #    self.cycling_date = cycle.start_date
    #    p = cycle.period
    #    do_parsing = True
    #    while do_parsing:
    #        # Tasks nodes with correponding output but not input
    #        for name, task_graph_spec in cycle.tasks.items():
    #            # Task nodes
    #            # note: input, output and dependencies added at second traversing
    #            self.add_task(name)
    #            # output nodes
    #            for out_name in task_graph_spec.get("output", []):
    #                self.add_data(out_name)
    #        # Continue cycling
    #        if not p:
    #            do_parsing = False
    #        else:
    #            self.cycling_date += p
    #            do_parsing = (self.cycling_date + p) <= cycle.end_date
    #
    #def add_wc_data(self, specification):
    #    if name not in self.data_specs:
    #        raise ValueError(f"{name} not declared as data")
    #    data_node = WcData(name, self.data_specs[name])
    #    if data_node.has_abs_path():
    #        if not self.data[name]:
    #            self.data[name] = data_node
    #            self.graph.add_node(
    #                data_node,
    #                label=name,
    #                tooltip=yaml.dump(data_node.run_spec),
    #                **data_node.gv_kw,
    #            )
    #    elif self.cycling_date not in self.data[name]:
    #        self.data[name][self.cycling_date] = data_node
    #        self.graph.add_node(
    #            data_node,
    #            label=name,
    #            tooltip=yaml.dump(data_node.run_spec),
    #            **data_node.gv_kw,
    #        )


    #@property
    #def cycles(self):
    #    return self._cycles

    #@cycles.setter
    #def cycles(self, specs):
    #    self._cycles = []
    #    for name, spec in specs.items():
    #        self._cycles.append(WcCycle(name, spec, self))

    #def verify_workflow(self):
    #    """Checks if the defined workflow is correctly referencing files."""
    #    # - no duplicates keys (no redefinition)
    #    # - no undefined keys (e.g. inputs in tasks that are not defined)
    #    # - Do we require files to be present?

    #def init_wc_data(self):
    #    """Initializes the WcData objects"""

    #def init_wc_tasks(self):
    #    pass

    #def init_wc_cycles(self):
    #    pass

    #def add_task(self, name):
    #    if name not in self.tasks_specs:
    #        raise ValueError(f"{name} not declared as task")
    #    if self.cycling_date not in self.tasks[name]:
    #        task_node = WcTask(name, self.tasks_specs[name])
    #        self.tasks[name][self.cycling_date] = task_node
    #        self.graph.add_node(
    #            task_node,
    #            label=name,
    #            tooltip=yaml.dump(task_node.run_spec),
    #            **task_node.gv_kw,
    #        )

    #def add_data(self, name, spcs):
    #    if name not in self.data_specs:
    #        raise ValueError(f"{name} not declared as data")
    #    data_node = WcData(name, self.data_specs[name])
    #    if data_node.has_abs_path():
    #        if not self.data[name]:
    #            self.data[name] = data_node
    #            self.graph.add_node(
    #                data_node,
    #                label=name,
    #                tooltip=yaml.dump(data_node.run_spec),
    #                **data_node.gv_kw,
    #            )
    #    elif self.cycling_date not in self.data[name]:
    #        self.data[name][self.cycling_date] = data_node
    #        self.graph.add_node(
    #            data_node,
    #            label=name,
    #            tooltip=yaml.dump(data_node.run_spec),
    #            **data_node.gv_kw,
    #        )

    #def get_task(self, spec):
    #    if isinstance(spec, dict):
    #        name, graph_spec = next(iter(spec.items()))
    #    else:
    #        name, graph_spec = spec, None
    #    if graph_spec is None:
    #        return self.tasks[name][self.cycling_date]
    #    else:
    #        date = graph_spec.get("date")
    #        lag = graph_spec.get("lag")
    #        if date and lag:
    #            raise ValueError("graph_spec cannot contain both date and lag")
    #        if not date and not lag:
    #            raise ValueError("graph_spec must contain eiher date or lag")
    #        if date:
    #            return self.task["name"][date]
    #        else:
    #            dates = [*self.tasks[name].keys()]
    #            if isinstance(lag, list):
    #                nodes = []
    #                for lg in lag:
    #                    date = self.cycling_date + parse_duration(lg)
    #                    if date <= dates[-1] and date >= dates[0]:
    #                        nodes.append(self.tasks[name][date])
    #                return nodes
    #            else:
    #                date = self.cycling_date + parse_duration(lag)
    #                if date <= dates[-1] and date >= dates[0]:
    #                    return self.tasks[name][date]

    #def get_data(self, spec):
    #    if isinstance(spec, dict):
    #        name, graph_spec = next(iter(spec.items()))
    #    else:
    #        name, graph_spec = spec, None
    #    if "abs_path" in self.data_specs[name]:
    #        if graph_spec:
    #            raise ValueError(
    #                "graph_spec cannot be provided to access data with abs_path"
    #            )
    #        return self.data[name]
    #    elif graph_spec is None:
    #        return self.data[name][self.cycling_date]
    #    else:
    #        date = graph_spec.get("date")
    #        lag = graph_spec.get("lag")
    #        if date and lag:
    #            raise ValueError("graph_spec cannot contain both date and lag")
    #        if not date and not lag:
    #            raise ValueError("graph_spec must contain eiher date or lag")
    #        if date:
    #            return self.data[name][datetime.fromisoformat(date)]
    #        else:
    #            dates = [*self.data[name].keys()]
    #            if isinstance(lag, list):
    #                nodes = []
    #                for lg in lag:
    #                    date = self.cycling_date + parse_duration(lg)
    #                    if date <= dates[-1] and date >= dates[0]:
    #                        nodes.append(self.data[name][date])
    #                return nodes
    #            else:
    #                date = self.cycling_date + parse_duration(lag)
    #                if date <= dates[-1] and date >= dates[0]:
    #                    return self.data[name][date]

    #def add_edge(self, u, v):
    #    if isinstance(u, list) and isinstance(v, list):
    #        raise ValueError("Only origin or target of edge can be a list")
    #    if isinstance(u, list):
    #        for node in u:
    #            self.graph.add_edge(node, v, **self.edge_gv_kw)
    #    elif isinstance(v, list):
    #        for node in v:
    #            self.graph.add_edge(u, node, **self.edge_gv_kw)
    #    else:
    #        self.graph.add_edge(u, v, **self.edge_gv_kw)
    #
    #def _create_workgraph(self):
    #    # Add concrete data nodes
    #    for name, spec in self.data_specs.items():
    #        if "abs_path" in spec:
    #            self.add_data(name)
    #    # Define all the other task and data nodes
    #    for cycle in self.cycles:
    #        self._add_nodes_from_cycle(cycle)
    #    # Draw edges between nodes
    #    for cycle in self.cycles:
    #        self._add_edges_from_cycle(cycle)

    #    
    #def _add_nodes_from_cycle(self, cycle):



    #    self.cycling_date = cycle.start_date
    #    p = cycle.period
    #    do_parsing = True
    #    while do_parsing:
    #        # Tasks nodes with correponding output but not input
    #        for name, task_graph_spec in cycle.tasks.items():
    #            # Task nodes
    #            # note: input, output and dependencies added at second traversing
    #            self.add_task(name)
    #            # output nodes
    #            for out_name in task_graph_spec.get("output", []):
    #                self.add_data(out_name)
    #        # Continue cycling
    #        if not p:
    #            do_parsing = False
    #        else:
    #            self.cycling_date += p
    #            do_parsing = (self.cycling_date + p) <= cycle.end_date

    #def _add_edges_from_cycle(self, cycle):
    #    self.cycling_date = cycle.start_date
    #    p = cycle.period
    #    do_parsing = True
    #    k = 0
    #    while do_parsing:
    #        cluster = []
    #        for name, task_graph_spec in cycle.tasks.items():
    #            task_node = self.get_task(name)
    #            cluster.append(task_node)
    #            # add input nodes
    #            for in_spec in task_graph_spec.get("input", []):
    #                if in_node := self.get_data(in_spec):
    #                    if isinstance(in_node, list):
    #                        task_node.input.extend(in_node)
    #                    else:
    #                        task_node.input.append(in_node)
    #                    self.add_edge(in_node, task_node)
    #            # add output nodes
    #            for out_spec in task_graph_spec.get("output", []):
    #                if out_node := self.get_data(out_spec):
    #                    task_node.output.append(out_node)
    #                    self.add_edge(task_node, out_node)
    #                    if not out_node.is_concrete():
    #                        cluster.append(out_node)
    #            # add dependencies
    #            for dep_spec in task_graph_spec.get("depends", []):
    #                if dep_node := self.get_task(dep_spec):
    #                    if isinstance(dep_node, list):
    #                        task_node.depends.extend(dep_node)
    #                    else:
    #                        task_node.depends.append(dep_node)
    #                    self.add_edge(dep_node, task_node)
    #        # Add clsuter
    #        d1 = self.cycling_date
    #        dates = d1.isoformat()
    #        if p:
    #            d2 = self.cycling_date + p
    #            dates += f" -- {d2.isoformat()}"
    #        label = f"{cycle.name}\n{dates}"
    #        self.graph.add_subgraph(
    #            cluster,
    #            name=f"cluster_{cycle.name}_{k}",
    #            clusterrank="global",
    #            label=label,
    #            tooltip=label,
    #            **self.cluster_kw,
    #        )
    #        # Continue cycling
    #        if not p:
    #            do_parsing = False
    #        else:
    #            self.cycling_date += p
    #            k += 1
    #            do_parsing = (self.cycling_date + p) <= cycle.end_date

    #@classmethod
    #def from_yaml(cls, config):
    #    config_path = Path(config)
    #    config = yaml.safe_load(config_path.read_text())
    #    return cls(
    #        *map(config["scheduling"].get, ("start_date", "end_date", "graph")),
    #        *map(config["runtime"].get, ("tasks", "data")),
    #        name=config_path.stem,
    #    )

    ## ? JG mod here -> To build WorkGraph from dict
    #def resolve_inputs(self, task, task_io_dict):
    #    # ? This should either resolve to the outputs of a previous node, or, if not, to the absolute inputs
    #    print("self.build_up_dict")
    #    pprint(self.build_up_dict, sort_dicts=False)

    #    # Extpar@2025-01-01-00-00
    #    # extpar_file@2025-01-01-00-00
    #    # extpar_file@2025-01-01-00-00

    #    # print('task_io_dict')
    #    # pprint(task_io_dict, sort_dicts=False)

    #    input_node_list = []

    #    prev_outputs = [
    #        list(_["outputs"].values())[0] for _ in self.build_up_dict.values()
    #    ]
    #    output_nodes = [_["task"] for _ in self.build_up_dict.values()]
    #    # print('prev_outputs', prev_outputs)
    #    # print('output_nodes', output_nodes)
    #    prev_output_node_mapping = dict(zip(prev_outputs, output_nodes))
    #    # print('prev_output_node_mapping')
    #    # pprint(prev_output_node_mapping, sort_dicts=False)

    #    # print('input_dict')
    #    print("prev_output_node_mapping", prev_output_node_mapping)
    #    for input_argument, input_instance in task_io_dict["inputs"].items():
    #        print("input_argument", input_argument)
    #        print("input_instance", input_instance)
    #        # ? This works if input of current task is output of previous task
    #        try:
    #            input_node_list.append(
    #                prev_output_node_mapping[input_instance].outputs[input_argument]
    #            )
    #        except KeyError:
    #            print("input_instance")
    #            print(input_instance)
    #            print(self.data)
    #            # ? Here instead attach global input node. For now, just append as string as a quick hack.
    #            input_node_list.append(input_instance)
    #            pass

    #    print("input_node_list", input_node_list)

    #    # for prev_task, prev_task_outputs in zip(self.build_up_dict.keys(), :
    #    #     print(prev_task)
    #    #     print(prev_task_io_dict)

    #    # print(task_io_dict['inputs'].keys())
    #    input_node_mapping_dict = dict(
    #        zip(task_io_dict["inputs"].keys(), input_node_list)
    #    )
    #    print(f"task_name: {task}, input_node_mapping_dict")
    #    pprint(input_node_mapping_dict, sort_dicts=False)
    #    return input_node_mapping_dict

    #def to_aiida_workgraph(self):
    #    tmp_dict = deepcopy(self.graph_dict)

    #    print("self.graph_dict")
    #    pprint(self.graph_dict, sort_dicts=False)

    #    for itask, (task, task_io_dict) in enumerate(self.graph_dict.items()):
    #        print("task", task)
    #        task_name_sanitized = sanitize_link_label(task)
    #        task_name_no_datetime = sanitize_link_label(task.split("@")[0].lower())

    #        task_inputs = self.resolve_inputs(task=task, task_io_dict=task_io_dict)

    #        wg_node = self._workgraph.nodes.new(
    #            "ShellJob",
    #            name=task_name_sanitized,
    #            command=load_code(task_name_no_datetime),
    #            arguments=list(task_io_dict["inputs"].keys()),
    #            # nodes=task_io_dict["inputs"],
    #            nodes=task_inputs,
    #            outputs=task_io_dict["outputs"],
    #        )

    #        self.build_up_dict[task] = tmp_dict.pop(task)
    #        self.build_up_dict[task]["task"] = wg_node

    #        # print("self.tmp_dict")
    #        # pprint(tmp_dict, sort_dicts=False)
    #        print("self.build_up_dict")
    #        pprint(self.build_up_dict, sort_dicts=False)

    #        # if itask > 2:
    #        #     raise SystemExit


# ============
# Main program
# ============


def main():
    # Parse user input
    # ================
    parser = argparse.ArgumentParser(
        description="draw the graph specified in a weather and climate yaml format"
    )

    parser.add_argument("config", help="path to yaml configuration file")
    args = parser.parse_args()

    # Build and draw graph
    # ====================
    WCG = WcWorkflow.from_yaml(args.config)
    WCG.prepare()
    from target_dict import dev_dict
    pprint(dev_dict, sort_dicts=False)
    WCG.to_aiida_workgraph()
    # WCG.draw()


if __name__ == "__main__":
    main()
