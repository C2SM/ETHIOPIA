from aiida_workgraph import WorkGraph
from aiida.orm import SinglefileData, RemoteData, FolderData, Data, Node
from datetime import datetime
from wcflow import core

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


class AiidaWorkGraph:

    def __init__(self, core_workflow: core.Workflow):
        # Needed for date indexing
        self._core_workflow = core_workflow

        self._validate_workflow()

        self._workgraph = WorkGraph(core_workflow.name)

        self._aiida_data_nodes: dict[str, Data] = {}
        # TODO rename _aiida_output_socket_nodes
        self._aiida_socket_nodes: dict[tuple[str, datetime], NodeSocket] = {}
        self._aiida_task_nodes: dict[tuple[str, datetime], Task] = {}

        self._add_aiida_initial_data_nodes()
        self._add_aiida_task_nodes()
        self._add_aiida_links()

    def _validate_workflow(self):
        """Checks if the defined workflow is correctly referencing key names."""
        # TODO This is a placeholder function that I would like to split up into different validation functions later
        #      Since the invidual validation should happen before parameter assignment
        # - Check that all key names that are used for aiida labels, are valid key values
        # - Warning if output nodes that are overwritten by other tasks before usage, if this actually happens? 

    def _add_aiida_initial_data_nodes(self):
        """
        Nodes that correspond to data that are available on initialization of the workflow
        """
        for cycle in self._core_workflow.unroll_cycles():
            for task in cycle.unroll_tasks():
                for input in task.unroll_inputs():
                    if input not in self._core_workflow.unrolled_outputs:
                        self._add_aiida_input_data_node(input)

    @staticmethod
    def parse_to_aiida_label(label: str) -> str:
        return label.replace("-", "_").replace(" ", "_").replace(":", "_")

    @staticmethod
    def get_aiida_label_from_unrolled_data(data: core.UnrolledData) -> str:
        """
        """
        return AiidaWorkGraph.parse_to_aiida_label(
                f"{data.name}_{data.date}")

    @staticmethod
    def get_aiida_label_from_unrolled_task(task: core.UnrolledTask) -> str:
        """
        """
        return AiidaWorkGraph.parse_to_aiida_label(
                f"{task.unrolled_cycle.name}_"
                f"{task.unrolled_cycle.date}_"
                f"{task.name}_"
                f"{task.date}")

    def _add_aiida_input_data_node(self, input: core.UnrolledData):
        """
        Create an :class:`aiida.orm.Data` instance from this wc data instance.

        :param input: ...
        """
        label = AiidaWorkGraph.get_aiida_label_from_unrolled_data(input)
        if input.type == "file":
            aiida_data_node = SinglefileData(label=label, file=input.path.resolve())
        elif input.type == "dir":
            aiida_data_node = FolderData(label=label, tree=input.path.resolve())
        else:
            raise ValueError(f'Data type {input.type!r} not supported. Please use \'file\' or \'dir\'.')

        self._aiida_data_nodes[label] = aiida_data_node

    def _add_aiida_task_nodes(self):
        for cycle in self._core_workflow.unroll_cycles():
            for task in cycle.unroll_tasks():
                self._add_aiida_task_node(task)


    def _add_aiida_task_node(self, task: core.UnrolledTask):
        label = AiidaWorkGraph.get_aiida_label_from_unrolled_task(task)
        workgraph_task = self._workgraph.tasks.new(
            "ShellJob",
            name=label,
            command=task.command,
            # TODO ... more properties that are taken from wc_task
        )
        workgraph_task.set({'arguments':[]})
        workgraph_task.set({"nodes": {}})
        self._aiida_task_nodes[label] = workgraph_task

    def _add_aiida_links(self):
        for cycle in self._core_workflow.unroll_cycles():
            self._add_aiida_links_from_cycle(cycle)

    def _add_aiida_links_from_cycle(self, cycle: core.UnrolledCycle):
        for task in cycle.unroll_tasks():
            for input in task.unroll_inputs():
                self._link_input_to_task(input)
            for argument in task.unroll_arguments(): 
                self._link_argument_to_task(argument)
            for output in task.unroll_outputs(): 
                self._link_output_to_task(output)

    def _link_input_to_task(self, input: core.UnrolledData):
        #                    task_name, task_date: datetime, input_name: str, input_date: datetime):
        task_label = AiidaWorkGraph.get_aiida_label_from_unrolled_task(input.unrolled_task)
        input_label = AiidaWorkGraph.get_aiida_label_from_unrolled_data(input)
        workgraph_task = self._aiida_task_nodes[task_label]
        workgraph_task.inputs.new("General", f"nodes.{input.name}")
        workgraph_task.kwargs.append(f"nodes.{input.name}")

        if (data_node := self._aiida_data_nodes.get(input_label)) is not None:
            if (nodes := workgraph_task.inputs.get("nodes")) is None:
                # TODO can Julian/Xing check if this is correct error message? 
                raise ValueError(f"Workgraph task {workgraph_task.name!r} did not initialize input nodes in the workgraph before linking. This is a bug in the code, please contact devevlopers.")
            nodes.value.update({f"{input.name}": data_node})
        elif (output_socket := self._aiida_socket_nodes.get(input_label)) is not None:
            self._workgraph.links.new(output_socket, workgraph_task.inputs[f"nodes.{input.name}"])
        else:
            raise ValueError(f"Input data node {input_label!r} was neither found in socket nodes nor in data nodes. The task {task_label!r} must have dependencies on inputs before they are created.")

    def _link_argument_to_task(self, argument: core.UnrolledArgument):
        workgraph_task = self._aiida_task_nodes[AiidaWorkGraph.get_aiida_label_from_unrolled_task(argument.unrolled_task)]
        if (workgraph_task_arguments := workgraph_task.inputs.get("arguments")) is None:
            raise ValueError(f"Workgraph task {workgraph_task.name!r} did not initialize argument nodes in the workgraph before linking. This is a bug in the code, please contact devevlopers.")
        # 3 options for arguments
        # argument options:
        # - input: preproc_output --> "command --input {preproc_output}"
        # - verbose: null --> "command --verbose"
        # - input_file -->"command {input_file}"
        # The first two options can have the form "--input" and "-i"

        if argument.option is None and argument.value is not None:
            workgraph_task_arguments.value.append(f"{{{argument}}}")
        elif argument.option is not None:
            if len(argument.option) == 1: 
                workgraph_task_arguments.value.append(f"-{argument.option}")
            else:
                workgraph_task_arguments.value.append(f"--{argument.option}")
            if argument.value is not None: 
                workgraph_task_arguments.value.append(f"{{{argument.value}}}")

    def _link_output_to_task(self, output: core.UnrolledData):
        workgraph_task = self._aiida_task_nodes[AiidaWorkGraph.get_aiida_label_from_unrolled_task(output.unrolled_task)]
        output_label = AiidaWorkGraph.get_aiida_label_from_unrolled_data(output)
        output_socket = workgraph_task.outputs.new("General", output.src)
        self._aiida_socket_nodes[output_label] = output_socket

    def run(self):
        self._workgraph.run()
        