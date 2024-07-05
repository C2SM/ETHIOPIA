#!/usr/bin/env python3

from datetime import datetime
from importlib_metadata import entry_points
from isoduration import parse_duration
from isoduration.formatter import Duration
from node_graph.socket import NodeSocket
import yaml
from pathlib import Path
import argparse
from copy import deepcopy
from pprint import pprint
from typing import Tuple, Dict, List, Optional
from collections.abc import Hashable, Iterable

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

class TimeUtils:
    @staticmethod
    def duration_is_negative(duration: Duration) -> bool:
        if duration.date.years < 0 or duration.date.months < 0 or duration.date.days < 0 or \
           duration.time.hours < 0 or duration.time.minutes < 0 or duration.time.seconds < 0:
            return True
        return False

class ParseUtils:
    @staticmethod
    def entries_to_dicts(entries: List[Hashable | dict]) -> List[dict]:
        """
        We have often expressions that can be dicts or str during the parsing that are always converted to dicts to simplify handling

        .. yaml
            - key_1
            - key_2:
                property: true

        When parsing this results in an object of the form [key_1, {key_2: {property: true}}]. This function converts this to [{key_1: None}, {key_2: {property: true}}]
        """
        return [{entry : None} if not isinstance(entry, dict) else entry
                            for entry in entries]

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
    def to_full_spec_task_from_spec(spec: Dict[str, dict], wc_data: Dict[str, WcData])
        spec
        task_spec = deepcopy(task_spec)
        for task_name, cycle_task_spec in tasks.items():
            task_spec.update(cycle_task_spec)
            WcFullSpecCycle()

    def to_full_spec_task(inputs: List[str | dict], outputs: List[str], wc_data: Dict[str, WcData])
        #...
        pass

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
    """
    We never need to create instances of a cycle class so we only contains static methods
    """
    @staticmethod
    def valid_spec_keys() -> List[str]:
        return ["tasks", "period", "start_date", "end_date"]

    @staticmethod
    def required_spec_keys() -> List[str]:
        return ["tasks", "start_date", "end_date"]

class WcFullSpecCycle(WcCycle):

    @classmethod
    def from_spec(cls, name: str, spec: dict, wc_tasks: Dict[str, WcTask], wc_data: Dict[str, WcData]):
        for key in spec.keys():
            if key not in cls.valid_spec_keys():
                raise ValueError(f"Cycle {name!r} found invalid key {key!r}. Key must be in {WcCycle.valid_spec_keys()}")
        for key in cls.required_spec_keys():
            if key not in spec.keys():
                raise ValueError(
                    f"When creating cycle instance for {name!r}, {key!r} was given in the specification"
                )
        return cls(name, **spec, wc_tasks=wc_tasks, wc_data=wc_data)

    def __init__(self, name: str, start_date: str, end_date: str, tasks: Dict[str, dict], wc_tasks: Dict[str, WcTask], wc_data: Dict[str, WcData], period: Optional[str] = None):
        self._name = name

        self._start_date = datetime.fromisoformat(start_date)
        self._end_date = datetime.fromisoformat(end_date)
        if self._start_date > self._end_date:
            raise ValueError("For cycle {self._name!r} the start_date {start_date!r} lies after given end_date {end_date!r}.")

        self._period = None if period is None else parse_duration("P0M")
        if self._period is not None and TimeUtils.duration_is_negative(self._period):
            raise ValueError("For cycle {self._name!r} the period {period!r} is negative.")

        self._tasks = tasks

        self._wc_tasks = wc_tasks 
        self._wc_data = wc_data

    def __iter__(self):
        cycle_current_date = self._start_date
        while cycle_current_date <= self._end_date: 
            for task_name, task_spec in self._wc_tasks.items():
                yield self._wc_tasks[task_name].to_full_spec_task(task_spec)
            if self._period is None:
                break
            else:
                cycle_current_date += self._period
        WcFullSpecTask()

    @staticmethod
    def valid_spec_keys() -> List[str]:
        return super().valid_spec_keys + ["inputs", "outputs", "arguments"]

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


class WcCycleTask(WcData):

class WcCycleTaskData(WcData):
    @classmethod
    def from_spec(self, name, spec)
        return

    def __init__(self, name: str)


    @staticmethod
    def valid_keys() -> List[str]:
        return WcCycle.valid_spec_keys + ["inputs", "outputs", "arguments"]

    def to_full_spec_task_from_spec(spec: Dict[str, dict], wc_data: Dict[str, WcData])
        spec
        task_spec = deepcopy(task_spec)
        for task_name, cycle_task_spec in tasks.items():
            task_spec.update(cycle_task_spec)
            WcFullSpecCycle()

    def to_full_spec_task(inputs: List[str | dict], outputs: List[str], wc_data: Dict[str, WcData])
        #...
        pass

    def __init__(self, name: str, lag: Optional[str] = None, Optiona):
        pass

    @property
    def date(self, offset_date: Optional[datetime] = None) -> datetime:
        if isinstance(self._when, Duration): 
            if offset_date is None:
                raise ValueError("")
            else:
                return offset_date + self._when
        else:
            return self._when


    def to_workgraph_node(self, workgraph: WorkGraph):
        workgraph_task = self._aiida_task_nodes[(task_name, task_date)]
        workgraph.tasks[""]
        workgraph_task.inputs.new("General", f"nodes.{input_name}")

        if (data_node := self._aiida_data_nodes[(input_name, input_date)] is not None):
            if (nodes := workgraph_task.inputs.get("nodes")) is None:
                # TODO can Julian/Xing check if this is correct error message? 
                raise ValueError(f"Workgraph task {workgraph_task.name!r} did not initialize input nodes in the workgraph before linking. This is a bug in the code, please contact devevlopers.")
            nodes.value.update({f"{input_name}": data_node})
        elif (output_socket := self._aiida_socket_nodes[(input_name, input_date)] is not None):
            self._workgraph.links.new(output_socket, workgraph_task.inputs[f"nodes.{input_name}"])
        else:
            raise ValueError("Input data node was neither found in socket nodes nor in data nodes. The task {task_name!r} must have dependencies on inputs before they are created.")

        if :
            workgraph_task = self._aiida_task_nodes[(task_name, date)]
            output_socket = workgraph_task.outputs.new("General", output_name)
            self._aiida_socket_nodes[(output_name, date)] = output_socket

class WcFullSpecTask(WcTask):
    def __init__(
        self,
        name: str,
        command: str,
        inputs: Optional[List[str | dict]] = None
        outputs: Optional[List[str]] = None,
        arguments: Optional[str | Dict[str, str | None]] = None,
        depends: Optional[List[str]] = None,
        wc_data: Dict[str, WcData]
        date: datetime,
    ):
        self._name = name
        self._command = command
        # [{'stream': {when: '-P2M'}}, 'icon_input']
        if inputs is None:
            formatted_inputs: List[dict] = ParseUtils.entries_to_dicts(inputs)
            self._inputs = ParseUtils.entries_to_dicts(inputs){}
        else:
            inputs_list = [WcFullSpecData(input_) for input_ in inputs]
            dict(input_ )
            self._inputs = {input_.name: input_ for input_ in inputs_list}
        self._output = output if output is not None else []
        self._argument = argument if argument is not None else {}
        self._depends = depends if depends is not None else []
        
        self._wc_data
        

    @classmethod
    def from_wc_task(cls, wc_task: WcTask, cycle_spec: Dict[str, dict], wc_data: Dict[str, WcData]):
        for key in cycle_spec.keys():
            if key not in WcFullSpecTask.valid_spec_keys():
                raise ValueError(f"Cycle {name!r} found invalid key {key!r}. Key must be in {WcCycle.valid_spec_keys()}")
        for key in WcFullSpecTask.required_spec_keys():
            if key not in cycle_spec.keys():
                raise ValueError(
                    f"When creating cycle instance for {name!r}, {key!r} was given in the specification"
                )
        full_spec = wc_task.to_spec()
        full_spec.update(spec)
        spec.update({
            "command": wc_task.command,
            "": wc_task.command,
        })
        return cls(name, **spec, wc_tasks=wc_tasks, wc_data=wc_data)

    @classmethod
    def from_spec(cls, spec: Dict[str, dict]):
        pass


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
        self._wc_data = {name: WcData.from_spec(name, spec) for name, spec in data.items()}
        #self._wc_cycles = WcWorkflow._create_wc_cycles(cycles, start_date, end_date)
        self._wc_tasks = WcWorkflow._create_wc_tasks(tasks)
        self._wc_cycles = WcWorkflow._create_wc_cycles(cycles, start_date, end_date, self._wc_tasks, self._wc_tasks)

        self._workgraph = WorkGraph(self._name)

        self._aiida_data_nodes: Dict[Tuple[str, datetime], DataNode] = {}
        # TODO rename _aiida_output_socket_nodes
        self._aiida_socket_nodes: Dict[Tuple[str, datetime], NodeSocket] = {}
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
        for wc_full_spec_task in cycle:
            for wc_input in wc_full_spec_task.inputs:
                self._link_input_to_task(wc_full_spec_task.name, wc_full_spec_task.date, wc_input.name, wc_input.date)
            for argument in wc_full_spec_task.arguments: 
                self._link_argument_to_task(wc_full_spec_task.name, wc_full_spec_task.date, argument)
            for output_name in wc_task.outputs: 
                self._link_output_to_task(wc_full_spec_task.name, wc_full_spec_task.date, output_name)


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

    def _link_input_to_task(self, task_name, task_date: datetime, input_name: str, input_date: datetime):
        workgraph_task = self._aiida_task_nodes[(task_name, task_date)]
        workgraph_task.inputs.new("General", f"nodes.{input_name}")

        if (data_node := self._aiida_data_nodes[(input_name, input_date)] is not None):
            if (nodes := workgraph_task.inputs.get("nodes")) is None:
                # TODO can Julian/Xing check if this is correct error message? 
                raise ValueError(f"Workgraph task {workgraph_task.name!r} did not initialize input nodes in the workgraph before linking. This is a bug in the code, please contact devevlopers.")
            nodes.value.update({f"{input_name}": data_node})
        elif (output_socket := self._aiida_socket_nodes[(input_name, input_date)] is not None):
            self._workgraph.links.new(output_socket, workgraph_task.inputs[f"nodes.{input_name}"])
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
