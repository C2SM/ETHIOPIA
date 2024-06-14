from aiida import orm
from datetime import datetime
from isoduration import parse_duration
import yaml
from pathlib import Path
import argparse

from aiida.orm.nodes.data import SinglefileData, FolderData
import aiida.orm
from aiida.manage.configuration import load_profile
from aiida_workgraph import WorkGraph
from aiida_workgraph.sockets.built_in import SocketGeneral

# AiiDA stuff
load_profile()



# TODO write these classes
class Cycle:
    pass
class Task:
    pass
class Data:
    pass

class Scheduler():

    # TODO think about name
    def __init__(self, start_date, end_date, cycles, tasks, data, name=""):
        # zero level yaml nodes 
        self.start_date = datetime.fromisoformat(start_date)
        self.end_date = datetime.fromisoformat(end_date)
        self.tasks = tasks
        self.data = data
        self.cycles = cycles
        # TODO: wrap each task, data, cycle with a custom classes that do basic checkes 

        self.outputs = []
        # checks what data are outputs, so they are not available on initialization
        for cycle in self.cycles.values():
            if "period" in cycle:
                cycle_period = parse_duration(cycle["period"])
            else:
                cycle_period = self.end_date - self.start_date
            # create data nodes for all periods
            current_date = self.start_date
            while current_date < self.end_date:
                for task_key, task_value in cycle['tasks'].items():
                    for task_output_key in task_value["output"]:
                        self.outputs.append(task_output_key)
                current_date = current_date + cycle_period

        self.data_nodes = {}
        self.task_node_output_sockets = {}
        self.wg = WorkGraph(name)
        # unroll periodicity of cycles to create all required data nodes
        for cycle in self.cycles.values():
            if "period" in cycle:
                cycle_period = parse_duration(cycle["period"])
            else:
                cycle_period = self.end_date - self.start_date
            # create data nodes for all periods
            current_date = self.start_date
            while current_date < self.end_date:
                for task_key, task_value in cycle['tasks'].items():
                    self.data_nodes[task_key] = {}
                    self.data_nodes[task_key][current_date] = {}
                    task_inputs = {}
                    for task_input_key in task_value["input"]:
                        if task_input_key not in self.outputs and not isinstance(task_input_key, dict): # TODO and case is a hack that should be removed with proper python objects
                            data_node = Scheduler.create_data_node(task_input_key, self.data[task_input_key], current_date)
                            self.data_nodes[task_key][current_date][task_input_key] = data_node
                            task_inputs[task_input_key] = data_node
                        else:
                            # TODO "date" case is missing
                            # TODO lists of lags are missing
                            if isinstance(task_input_key, dict) and "lag" in next(iter(task_input_key.values())).keys():
                                # COMMENT this is a bit quercky because we can have inputs of form
                                #         {'input': ['grid file', 'icon input', {'restart': {'lag': '-P2M'}}]}}
                                #         should be resolved as soon as we have proper object repr
                                lag = next(iter(task_input_key.values()))["lag"]
                                # only require file if lag creates a valid date
                                if self.start_date <= current_date + parse_duration(lag):
                                    required_date = current_date + parse_duration(lag)
                                    task_input_key_ = next(iter(task_input_key.keys()))
                                    if ((task_input_key_, required_date) not in self.task_node_output_sockets.keys()):
                                        raise ValueError(f"Output {task_input_key_} for date {required_date} was requested as input before it was created by a task.")
                                    task_inputs[task_input_key_] = self.task_node_output_sockets[(task_input_key_, required_date)]
                                continue
                            elif isinstance(task_input_key, dict) and "date" in next(iter(task_input_key.values())).keys():
                                date = next(iter(task_input_key.values()))["date"]
                                required_date = datetime.fromisoformat(date)
                                task_input_key_ = next(iter(task_input_key.keys()))
                                if (task_input_key_, required_date) not in self.task_node_output_sockets.keys():
                                    raise ValueError(f"Output {task_input_key_} for date {required_date} was requested as input before it was created by a task.")
                                task_inputs[task_input_key_] = self.task_node_output_sockets[(task_input_key_, required_date)]
                            else:
                                required_date = current_date
                                if (task_input_key, required_date) not in self.task_node_output_sockets.keys():
                                    raise ValueError(f"Output {task_input_key} for date {required_date} was requested as input before it was created by a task.")
                                task_inputs[task_input_key] = self.task_node_output_sockets[(task_input_key, required_date)]


                    # resolve arguments, e.g.
                    #   arguments:
                    #     - g: grid file
                    #     - parse: extpar file 
                    # and this definition
                    #   grid file: {type: file, abs_path: /path/to/grid/file.nc}
                    #   extpar file: {type: file, rel_path: output}
                    # to 
                    #   ["-g", "{g}", "--parse", "{parse}"]
                    arguments = []
                    wg_input_nodes = {}
                    # COMMENT logic is not robust if we have outputs that are not
                    #         specified by arguments
                    if "argument" not in task_value:
                        raise NotImplemented("Default arguments are not implemented yet.")
                    for key, value in task_value["argument"].items():
                        # resolving short and long options following unix standards
                        if value in self.data.keys():
                            if value in task_inputs.keys():
                                if len(key) == 1:
                                    option = f"-{key}"
                                else:
                                    option = f"--{key}"
                                arguments.append(option)
                                arguments.append("{"+key+"}")

                                # COMMENT: This is to differ inputs that are outputs from tasks and inputs on initialization
                                if isinstance(task_inputs[value], SinglefileData): # from initialization
                                    wg_input_nodes[key] = task_inputs[value]
                                elif isinstance(task_inputs[value], FolderData):
                                     # TODO was buggy, might work now but need try it out, not sure if aiida-shell supports FolderNodes
                                    wg_input_nodes[key] = task_inputs[value]
                                elif isinstance(task_inputs[value], SocketGeneral): # COMMENT: NodeSocket might make more sense
                                    wg_input_nodes[key] = task_inputs[value]
                                else:
                                    raise ValueError(f"Got object of type {type(task_inputs[value])} that neither supports `filename` nor `name`.")
                        else:
                            raise NotImplemented("We do not support other options than data yaml keys as argument for the moment.")

                    # TODO: handle case when arguments are not given

                    # retrieves actual filename for all registered outputs, these are required 
                    task_output_src = [self.data[output_key]['src'] for output_key in task_value["output"]]
                    wg_task_node = self.wg.nodes.new(
                        "ShellJob",
                        name=task_key + f"_{current_date}".replace(' ', '_').replace('-', '_').replace(':', '_'), # TODO make a valid label in a clean way with a regex
                        command=self.tasks[task_key]['command'],
                        # e.g. ["g": "/path/to/grid/file.nc@<TIMESTAMP>", "--parse", "output@<TIMESTAMP>"]
                        arguments=arguments,
                        nodes=wg_input_nodes,
                        outputs=task_output_src,
                        #outputs=map(lambda x : x + f"@{current_date}", task_value["output"]) # does not work
                    )
                    # COMMENT: here might be the problem that outputs are overwritten, since we cannot really add the time stmp to the output
                    #          as the output name is determined by the command

                    # We have to store the output sockets for later tasks that might
                    # take it is input. To access them from the workgraph task we need
                    # the actual output name, but then we need to store it using the
                    # output yaml key to make it accesible by future tasks since
                    # multipe outputs can have the same name
                    self.task_node_output_sockets.update({(output_key, current_date):
                        wg_task_node.outputs[self.data[output_key]['src']] for output_key in task_value["output"]})

                current_date = current_date + cycle_period

    @classmethod
    def from_yaml(cls, config):
        config_path = Path(config)
        config = yaml.safe_load(config_path.read_text())

        return cls(name=config_path.stem, **config)

    @classmethod
    def from_dict(cls, name, **kwargs):
        # COMMENT: this is only temporary constructor, I don't think it will be needed later on
        return cls(name=name, **kwargs)


    @staticmethod
    def create_data_node(key: str, value: dict[str, str], date: datetime) -> aiida.orm.Node:
        # TODO date has become useless after discussion 
        """
        Processes an entry from data section in the yaml file. An entry has the form for example:

        .. yaml::

            my_file: {type: file, src: /scratch/user/project/input.txt}

        where `my_file` is the key and `{type: file, src: /scratch/user/project/input.txt}` the value

        :param key: The yaml key of the mapping.
        :param value: The yaml value of the mapping. An unordered set specifying the data.
                      For now only dict[str, str] are used.
        :param date: The date for this instance of the data node as the same data file can created during multiple points in time by periodic jobs.
        """
        data_type = value['type']
        if data_type == 'file':
            data_node = SinglefileData(file=value['src'], label=key)
        elif data_type == 'dir':
            data_node = FolderData(tree=value['src'], label=key)
        else:
            raise ValueError(f'Data type {data_type!r} not supported. Please use \'file\' or \'dir\'.')
        return data_node

        # COMMENT: I find this a bit dangerous, labels are in principle not unique.
        #          Here it should be unique, because otherwise we cannot map data to tasks unambigously
    def submit(self, **kwargs):
        self.wg.submit(**kwargs)

    def run(self, **kwargs):
        self.wg.run(**kwargs)

def replace_env_variables(data):
    import re
    import os
    # this is a bit hacky but simple and should work
    if isinstance(data, dict):
        return {key: replace_env_variables(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [replace_env_variables(item) for item in data]
    elif isinstance(data, str):
        return re.sub(r'\$([A-Z_]+)', lambda match: os.environ.get(match.group(1), match.group(0)), data)
    else:
        return data

def main():

    # Parse user input
    # ================
    parser = argparse.ArgumentParser(
        description='draw the graph specified in a weather and climate yaml format')

    parser.add_argument('config', help="path to yaml configuration file")
    args = parser.parse_args()

    # to replace environment variables
    config_path = Path(args.config)
    config_yaml = yaml.safe_load(config_path.read_text())
    config_yaml = replace_env_variables(config_yaml)

    # Build and draw graph
    # ====================
    scheduler = Scheduler.from_dict(config_path.stem, **config_yaml)
    scheduler.run()


if __name__ == '__main__':
    main()
