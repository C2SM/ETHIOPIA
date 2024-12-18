from __future__ import annotations

from typing import TYPE_CHECKING, Any

import aiida.common
import aiida.orm
import aiida_workgraph.engine.utils  # type: ignore[import-untyped]
from aiida_workgraph import WorkGraph  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from aiida_workgraph.socket import TaskSocket  # type: ignore[import-untyped]
    from sirocco.core import graph_items


# This is hack to aiida-workgraph, merging this into aiida-workgraph properly would require
# some major refactor see issue https://github.com/aiidateam/aiida-workgraph/issues/168
# It might be better to give up on the graph like construction and just create the task
# directly with inputs, arguments and outputs
def _prepare_for_shell_task(task: dict, kwargs: dict) -> dict:
    """Prepare the inputs for ShellTask"""
    from aiida.common import lang
    from aiida.orm import AbstractCode
    from aiida_shell.launch import convert_nodes_single_file_data, prepare_code

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

    default_outputs = {"remote_folder", "remote_stash", "retrieved", "_outputs", "_wait", "stdout", "stderr"}
    task_outputs = {task["outputs"][i]["name"] for i in range(len(task["outputs"]))}
    task_outputs = task_outputs.union(set(kwargs.pop("outputs", [])))
    missing_outputs = task_outputs.difference(default_outputs)
    return {
        "code": code,
        "nodes": nodes,
        "filenames": kwargs.pop("filenames", {}),
        "arguments": kwargs.pop("arguments", []),
        "outputs": list(missing_outputs),
        "parser": kwargs.pop("parser", None),
        "metadata": metadata or {},
    }


aiida_workgraph.engine.utils.prepare_for_shell_task = _prepare_for_shell_task


class AiidaWorkGraph:
    def __init__(self, core_workflow: core.Workflow):
        # Needed for date indexing
        self._core_workflow = core_workflow

        self._validate_workflow()

        self._workgraph = WorkGraph() # core_workflow.name TODO use filename

        # stores the input data available on initialization
        self._aiida_data_nodes: dict[str, aiida_workgraph.orm.Data] = {}
        # stores the outputs sockets of tasks
        self._aiida_socket_nodes: dict[str, TaskSocket] = {}
        self._aiida_task_nodes: dict[str, aiida_workgraph.Task] = {}

        self._add_aiida_initial_data_nodes()
        self._add_aiida_task_nodes()
        self._add_aiida_links()

    def _validate_workflow(self):
        """Checks if the defined workflow is correctly referencing key names."""
        for cycle in self._core_workflow.cycles:
            try:
                aiida.common.validate_link_label(cycle.name)
            except ValueError as exception:
                msg = f"Raised error when validating cycle name '{cycle.name}': {exception.args[0]}"
                raise ValueError(msg) from exception
            for task in cycle.tasks:
                try:
                    aiida.common.validate_link_label(task.name)
                except ValueError as exception:
                    msg = f"Raised error when validating task name '{cycle.name}': {exception.args[0]}"
                    raise ValueError(msg) from exception
                for input_ in task.inputs:
                    try:
                        aiida.common.validate_link_label(task.name)
                    except ValueError as exception:
                        msg = f"Raised error when validating input name '{input_.name}': {exception.args[0]}"
                        raise ValueError(msg) from exception
                for output in task.outputs:
                    try:
                        aiida.common.validate_link_label(task.name)
                    except ValueError as exception:
                        msg = f"Raised error when validating output name '{output.name}': {exception.args[0]}"
                        raise ValueError(msg) from exception
        # - Warning if output nodes that are overwritten by other tasks before usage, if this actually happens?

    def _add_aiida_initial_data_nodes(self):
        """
        Nodes that correspond to data that are available on initialization of the workflow
        """
        for cycle in self._core_workflow.cycles:
            for task in cycle.tasks:
                for input_ in task.inputs:
                    if input_.available:
                        self._add_aiida_input_data_node(input_)

    @staticmethod
    def parse_to_aiida_label(label: str) -> str:
        invalid_chars = ["-", " ", ":", "."]
        for invalid_char in invalid_chars:
            label = label.replace(invalid_char, "_")
        return label

    @staticmethod
    def get_aiida_label_from_unrolled_data(obj: core.BaseNode) -> str:
        """ """
        return AiidaWorkGraph.parse_to_aiida_label(
            f"{obj.name}" + "__".join(f"_{key}_{value}" for key, value in obj.coordinates.items())
        )

    @staticmethod
    def get_aiida_label_from_unrolled_task(obj: core.BaseNode) -> str:
        """ """
        # TODO task is not anymore using cycle name because information is not there
        #      so do we check somewhere that a task is not used in multiple cycles?
        #      Otherwise the label is not unique
        # --> task name + date + parameters
        return AiidaWorkGraph.parse_to_aiida_label(
            "__".join([f"{obj.name}"] + [f"_{key}_{value}" for key, value in obj.coordinates.items()])
        )

    def _add_aiida_input_data_node(self, input_: core.UnrolledData):
        """
        Create an :class:`aiida.orm.Data` instance from this wc data instance.

        :param input: ...
        """
        label = AiidaWorkGraph.get_aiida_label_from_unrolled_data(input_)
        if input_.type == "file":
            self._aiida_data_nodes[label] = aiida.orm.SinglefileData(label=label, file=input_.path.resolve())
        elif input_.type == "dir":
            self._aiida_data_nodes[label] = aiida.orm.FolderData(label=label, tree=input_.path.resolve())
        else:
            msg = f"Data type {input_.type!r} not supported. Please use 'file' or 'dir'."
            raise ValueError(msg)

    def _add_aiida_task_nodes(self):
        for cycle in self._core_workflow.cycles:
            for task in cycle.tasks:
                self._add_aiida_task_node(task)
        # after creation we can link the wait_on tasks
        # TODO check where this is now
        #for cycle in self._core_workflow.cycles:
        #    for task in cycle.tasks:
        #        self._link_wait_on_to_task(task)

    def _add_aiida_task_node(self, task: graph_items.Task):
        label = AiidaWorkGraph.get_aiida_label_from_unrolled_task(task)
        # breakpoint()
        if task.command is None:
            msg = f"The command is None of task {task}."
            raise ValueError(msg)
        workgraph_task = self._workgraph.tasks.new(
            "ShellJob",
            name=label,
            command=task.command,
        )
        workgraph_task.set({"arguments": []})
        workgraph_task.set({"nodes": {}})
        self._aiida_task_nodes[label] = workgraph_task

    def _link_wait_on_to_task(self, task: core.UnrolledTask):
        # TODO
        msg = ""
        raise NotImplementedError(msg)
        label = AiidaWorkGraph.get_aiida_label_from_unrolled_task(task)
        workgraph_task = self._aiida_task_nodes[label]
        wait_on_tasks = []
        for depend in task.unrolled_depends:
            wait_on_task_label = AiidaWorkGraph.get_aiida_label_from_unrolled_task(depend.depend_on_task)
            wait_on_tasks.append(self._aiida_task_nodes[wait_on_task_label])
        workgraph_task.wait = wait_on_tasks

    def _add_aiida_links(self):
        for cycle in self._core_workflow.cycles:
            self._add_aiida_links_from_cycle(cycle)

    def _add_aiida_links_from_cycle(self, cycle: core.UnrolledCycle):
        for task in cycle.tasks:
            for input_ in task.inputs:
                self._link_input_to_task(task, input_)
            for output in task.outputs:
                self._link_output_to_task(task, output)

    def _link_input_to_task(self, task: graph_items.Task, input_: graph_items.Data):
        """
        task: the task corresponding to the input
        input: ...
        """
        task_label = AiidaWorkGraph.get_aiida_label_from_unrolled_task(task)
        input_label = AiidaWorkGraph.get_aiida_label_from_unrolled_data(input_)
        workgraph_task = self._aiida_task_nodes[task_label]
        workgraph_task.inputs.new("Any", f"nodes.{input_label}")
        workgraph_task.kwargs.append(f"nodes.{input_label}")

        # resolve data
        if (data_node := self._aiida_data_nodes.get(input_label)) is not None:
            if (nodes := workgraph_task.inputs.get("nodes")) is None:
                msg = f"Workgraph task {workgraph_task.name!r} did not initialize input nodes in the workgraph before linking. This is a bug in the code, please contact the developers by making an issue."
                raise ValueError(msg)
            nodes.value.update({f"{input_label}": data_node})
        elif (output_socket := self._aiida_socket_nodes.get(input_label)) is not None:
            self._workgraph.links.new(output_socket, workgraph_task.inputs[f"nodes.{input_label}"])
        else:
            msg = f"Input data node {input_label!r} was neither found in socket nodes nor in data nodes. The task {task_label!r} must have dependencies on inputs before they are created."
            raise ValueError(msg)

        # resolve arg_option
        if (workgraph_task_arguments := workgraph_task.inputs.get("arguments")) is None:
            msg = f"Workgraph task {workgraph_task.name!r} did not initialize arguments nodes in the workgraph before linking. This is a bug in the code, please contact devevlopers."
            raise ValueError(msg)
        # TODO think about that the yaml file should have aiida valid labels
        # if (arg_option := task.input_arg_options.get(input_.name, None)) is not None:
        #     workgraph_task_arguments.value.append(f"{arg_option}")
        workgraph_task_arguments.value.append(f"{{{input_label}}}")

    def _link_output_to_task(self, task: graph_items.Task, output: graph_items.Data):
        """
        task: the task corresponding to the output
        output: ...
        """
        workgraph_task = self._aiida_task_nodes[AiidaWorkGraph.get_aiida_label_from_unrolled_task(task)]
        output_label = AiidaWorkGraph.get_aiida_label_from_unrolled_data(output)
        output_socket = workgraph_task.outputs.new("Any", output.src)
        self._aiida_socket_nodes[output_label] = output_socket

    def run(
        self,
        inputs: None | dict[str, Any] = None,
        metadata: None | dict[str, Any] = None,
    ) -> dict[str, Any]:
        return self._workgraph.run(inputs=inputs, metadata=metadata)

    def submit(
        self,
        *,
        inputs: None | dict[str, Any] = None,
        wait: bool = False,
        timeout: int = 60,
        metadata: None | dict[str, Any] = None,
    ) -> dict[str, Any]:
        return self._workgraph.submit(inputs=inputs, wait=wait, timeout=timeout, metadata=metadata)
