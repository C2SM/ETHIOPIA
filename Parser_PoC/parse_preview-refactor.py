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
                                    wg_input_nodes[key] = task_inputs[value].filename
                                elif isinstance(task_inputs[value], FolderData):
                                    wg_input_nodes[key] = "./" # TODO this is is hack, I don't know how to get the path that was inserted
                                elif isinstance(task_inputs[value], SocketGeneral): # COMMENT: NodeSocket might make more sense
                                    wg_input_nodes[key] = task_inputs[value]
                                else:
                                    raise ValueError(f"Got object of type {type(task_inputs[value])} that neither supports `filename` nor `name`.")
                        else:
                            raise NotImplemented("We do not support other options than data yaml keys as argument for the moment.")

                    # TODO: handle case when arguments are not given

                    #   ["g": "/path/to/grid/file.nc@<TIMESTAMP>", "--parse", "output@<TIMESTAMP>"]

                    wg_task_node = self.wg.nodes.new(
                        "ShellJob",
                        name=task_key + f"@{current_date}".replace(' ', '_'),
                        command=self.tasks[task_key]['command'],
                        #e.g. arguments=["--ERA5", "{ERA5}", "--extpar-file", "{extpar_file}", "--grid-file", "{grid_file}"],
                        arguments=arguments,
                        nodes=wg_input_nodes,
                        outputs=task_value["output"],
                        #outputs=map(lambda x : x + f"@{current_date}", task_value["output"]) # does not work
                    )
                    # COMMENT: here might be the problem that outputs are overwritten, since we cannot really add the time stmp to the output
                    #          as the output name is determined by the command
                    self.task_node_output_sockets.update({(key, current_date): wg_task_node.outputs[key] for key in task_value["output"]})

                current_date = current_date + cycle_period

    @classmethod
    def from_yaml(cls, config):
        config_path = Path(config)
        config = yaml.safe_load(config_path.read_text())

        return cls(name=config_path.stem, **config)


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

def main():

    # Parse user input
    # ================
    parser = argparse.ArgumentParser(
        description='draw the graph specified in a weather and climate yaml format')

    parser.add_argument('config', help="path to yaml configuration file")
    args = parser.parse_args()

    # Build and draw graph
    # ====================
    scheduler = Scheduler.from_yaml(args.config)
    #scheduler.submit(wait=True, timeout=300)


if __name__ == '__main__':
    main()
