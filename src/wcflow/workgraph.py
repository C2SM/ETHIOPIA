from typing import TYPE_CHECKING, Any

import aiida.common
import aiida.orm
import aiida_workgraph.engine.utils  # type: ignore[import-untyped]
from aiida_workgraph import WorkGraph  # type: ignore[import-untyped]

from wcflow import core

if TYPE_CHECKING:
    from aiida_workgraph.socket import TaskSocket  # type: ignore[import-untyped]


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

        self._workgraph = WorkGraph(core_workflow.name)

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
        for cycle in self._core_workflow.unrolled_cycles:
            try:
                aiida.common.validate_link_label(cycle.name)
            except ValueError as exception:
                msg = f"Raised error when validating cycle name '{cycle.name}': {exception.args[0]}"
                raise ValueError(msg) from exception
            for task in cycle.unrolled_tasks:
                try:
                    aiida.common.validate_link_label(task.name)
                except ValueError as exception:
                    msg = f"Raised error when validating task name '{cycle.name}': {exception.args[0]}"
                    raise ValueError(msg) from exception
                for input_ in task.unrolled_inputs:
                    try:
                        aiida.common.validate_link_label(task.name)
                    except ValueError as exception:
                        msg = f"Raised error when validating input name '{input_.name}': {exception.args[0]}"
                        raise ValueError(msg) from exception
                for output in task.unrolled_outputs:
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
        for cycle in self._core_workflow.unrolled_cycles:
            for task in cycle.unrolled_tasks:
                for input_ in task.unrolled_inputs:
                    if self._core_workflow.is_available_on_init(input_):
                        self._add_aiida_input_data_node(input_)

    @staticmethod
    def parse_to_aiida_label(label: str) -> str:
        return label.replace("-", "_").replace(" ", "_").replace(":", "_")

    @staticmethod
    def get_aiida_label_from_unrolled_data(data: core.UnrolledData) -> str:
        """ """
        return AiidaWorkGraph.parse_to_aiida_label(f"{data.name}_{data.unrolled_date}")

    @staticmethod
    def get_aiida_label_from_unrolled_task(task: core.UnrolledTask) -> str:
        """ """
        return AiidaWorkGraph.parse_to_aiida_label(
            f"{task.unrolled_cycle.name}_" f"{task.unrolled_cycle.unrolled_date}_" f"{task.name}"
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
        for cycle in self._core_workflow.unrolled_cycles:
            for task in cycle.unrolled_tasks:
                self._add_aiida_task_node(task)
        # after creation we can link the wait_on tasks
        for cycle in self._core_workflow.unrolled_cycles:
            for task in cycle.unrolled_tasks:
                self._link_wait_on_to_task(task)

    def _add_aiida_task_node(self, task: core.UnrolledTask):
        label = AiidaWorkGraph.get_aiida_label_from_unrolled_task(task)
        workgraph_task = self._workgraph.tasks.new(
            "ShellJob",
            name=label,
            command=task.command,
        )
        workgraph_task.set({"arguments": []})
        workgraph_task.set({"nodes": {}})
        self._aiida_task_nodes[label] = workgraph_task

    def _link_wait_on_to_task(self, task: core.UnrolledTask):
        label = AiidaWorkGraph.get_aiida_label_from_unrolled_task(task)
        workgraph_task = self._aiida_task_nodes[label]
        wait_on_tasks = []
        for depend in task.unrolled_depends:
            wait_on_task_label = AiidaWorkGraph.get_aiida_label_from_unrolled_task(depend.depend_on_task)
            wait_on_tasks.append(self._aiida_task_nodes[wait_on_task_label])
        workgraph_task.wait = wait_on_tasks

    def _add_aiida_links(self):
        for cycle in self._core_workflow.unrolled_cycles:
            self._add_aiida_links_from_cycle(cycle)

    def _add_aiida_links_from_cycle(self, cycle: core.UnrolledCycle):
        for task in cycle.unrolled_tasks:
            for input_ in task.unrolled_inputs:
                self._link_input_to_task(input_)
            for output in task.unrolled_outputs:
                self._link_output_to_task(output)

    def _link_input_to_task(self, input_: core.UnrolledData):
        task_label = AiidaWorkGraph.get_aiida_label_from_unrolled_task(input_.unrolled_task)
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
        if input_.arg_option is not None:
            workgraph_task_arguments.value.append(f"{input_.arg_option}")
        workgraph_task_arguments.value.append(f"{{{input_label}}}")

    def _link_output_to_task(self, output: core.UnrolledData):
        workgraph_task = self._aiida_task_nodes[AiidaWorkGraph.get_aiida_label_from_unrolled_task(output.unrolled_task)]
        output_label = AiidaWorkGraph.get_aiida_label_from_unrolled_data(output)
        output_socket = workgraph_task.outputs.new("Any", output.src)
        self._aiida_socket_nodes[output_label] = output_socket

    def run(self) -> dict[str, Any]:
        return self._workgraph.run()