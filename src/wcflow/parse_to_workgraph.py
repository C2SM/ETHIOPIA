#!/usr/bin/env python3

from datetime import datetime
from isoduration import parse_duration
import yaml
from lxml import etree
import webbrowser
from pathlib import Path
import argparse
from copy import deepcopy
from pprint import pprint

from aiida_workgraph import node, WorkGraph, build_node
from aiida_shell import ShellJob
from aiida.orm import SinglefileData, RemoteData, FolderData
from aiida import load_profile
from aiida_shell import launch_shell_job
from aiida.orm import load_code

load_profile()


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


class WcTask:
    def __init__(self, name, run_spec):
        self.name = name
        self.run_spec = run_spec
        self.input = []
        self.output = []
        self.depends = []


class WcData:
    def __init__(self, name, run_spec):
        self.name = name
        rel_path = run_spec.get("rel_path")
        abs_path = run_spec.get("abs_path")
        if rel_path is None and abs_path is None:
            raise ValueError(
                f"Error wheen trying to define data node {name}. "
                f"Either rel_path or abs_path must be specified"
            )
        if rel_path and abs_path:
            raise ValueError(
                f"Error wheen trying to define data node {name}. "
                f"Only one of rel_path or abs_path must be specified"
            )
        self.abs_path = abs_path
        self.rel_apth = rel_path
        self.run_spec = run_spec

    def is_concrete(self):
        return self.abs_path is not None


class WcCycle:
    def __init__(self, name, spec, graph):
        self.name = name
        self.graph = graph
        self.parse_spec(spec)

    def parse_spec(self, spec):
        if (d := spec.get("start_date")) is None:
            self.start_date = self.graph.start_date
        else:
            self.start_date = datetime.fromisoformat(d)

        if (d := spec.get("end_date")) is None:
            self.end_date = self.graph.end_date
        else:
            self.end_date = datetime.fromisoformat(d)

        if (p := spec.get("period")) is None:
            self.period = None
        else:
            self.period = parse_duration(p)

        self.tasks = spec.get("tasks", [])
        self.data = spec.get("data", [])


class WcWorkflow:
    def __init__(self, start_date, end_date, cycles, tasks, data, *args, **kwargs):
        self.start_date = datetime.fromisoformat(start_date)
        self.end_date = datetime.fromisoformat(end_date)
        self.tasks_specs = tasks
        self.data_specs = data
        self.cycles = cycles

        # Needed for date indexing
        self.data = {k: {} for k in data.keys()}
        self.tasks = {k: {} for k in tasks.keys()}

    @property
    def cycles(self):
        return self._cycles

    @cycles.setter
    def cycles(self, specs):
        self._cycles = []
        for name, spec in specs.items():
            self._cycles.append(WcCycle(name, spec, self))

    def add_task(self, name):
        if name not in self.tasks_specs:
            raise ValueError(f"{name} not declared as task")
        if self.cycling_date not in self.tasks[name]:
            task_node = WcTask(name, self.tasks_specs[name])
            self.tasks[name][self.cycling_date] = task_node
            self.graph.add_node(
                task_node,
                label=name,
                tooltip=yaml.dump(task_node.run_spec),
                **task_node.gv_kw,
            )

    def add_data(self, name):
        if name not in self.data_specs:
            raise ValueError(f"{name} not declared as data")
        data_node = WcData(name, self.data_specs[name])
        if data_node.is_concrete():
            if not self.data[name]:
                self.data[name] = data_node
                self.graph.add_node(
                    data_node,
                    label=name,
                    tooltip=yaml.dump(data_node.run_spec),
                    **data_node.gv_kw,
                )
        elif self.cycling_date not in self.data[name]:
            self.data[name][self.cycling_date] = data_node
            self.graph.add_node(
                data_node,
                label=name,
                tooltip=yaml.dump(data_node.run_spec),
                **data_node.gv_kw,
            )

    def get_task(self, spec):
        if isinstance(spec, dict):
            name, graph_spec = next(iter(spec.items()))
        else:
            name, graph_spec = spec, None
        if graph_spec is None:
            return self.tasks[name][self.cycling_date]
        else:
            date = graph_spec.get("date")
            lag = graph_spec.get("lag")
            if date and lag:
                raise ValueError("graph_spec cannot contain both date and lag")
            if not date and not lag:
                raise ValueError("graph_spec must contain eiher date or lag")
            if date:
                return self.task["name"][date]
            else:
                dates = [*self.tasks[name].keys()]
                if isinstance(lag, list):
                    nodes = []
                    for lg in lag:
                        date = self.cycling_date + parse_duration(lg)
                        if date <= dates[-1] and date >= dates[0]:
                            nodes.append(self.tasks[name][date])
                    return nodes
                else:
                    date = self.cycling_date + parse_duration(lag)
                    if date <= dates[-1] and date >= dates[0]:
                        return self.tasks[name][date]

    def get_data(self, spec):
        if isinstance(spec, dict):
            name, graph_spec = next(iter(spec.items()))
        else:
            name, graph_spec = spec, None
        if "abs_path" in self.data_specs[name]:
            if graph_spec:
                raise ValueError(
                    "graph_spec cannot be provided to access data with abs_path"
                )
            return self.data[name]
        elif graph_spec is None:
            return self.data[name][self.cycling_date]
        else:
            date = graph_spec.get("date")
            lag = graph_spec.get("lag")
            if date and lag:
                raise ValueError("graph_spec cannot contain both date and lag")
            if not date and not lag:
                raise ValueError("graph_spec must contain eiher date or lag")
            if date:
                return self.data[name][datetime.fromisoformat(date)]
            else:
                dates = [*self.data[name].keys()]
                if isinstance(lag, list):
                    nodes = []
                    for lg in lag:
                        date = self.cycling_date + parse_duration(lg)
                        if date <= dates[-1] and date >= dates[0]:
                            nodes.append(self.data[name][date])
                    return nodes
                else:
                    date = self.cycling_date + parse_duration(lag)
                    if date <= dates[-1] and date >= dates[0]:
                        return self.data[name][date]

    def add_edge(self, u, v):
        if isinstance(u, list) and isinstance(v, list):
            raise ValueError("Only origin or target of edge can be a list")
        if isinstance(u, list):
            for node in u:
                self.graph.add_edge(node, v, **self.edge_gv_kw)
        elif isinstance(v, list):
            for node in v:
                self.graph.add_edge(u, node, **self.edge_gv_kw)
        else:
            self.graph.add_edge(u, v, **self.edge_gv_kw)

    def prepare(self):
        # Add concrete data nodes
        for name, spec in self.data_specs.items():
            if "abs_path" in spec:
                self.add_data(name)
        # Define all the other task and data nodes
        for cycle in self.cycles:
            self._add_nodes_from_cycle(cycle)
        # Draw edges between nodes
        for cycle in self.cycles:
            self._add_edges_from_cycle(cycle)

    def _add_nodes_from_cycle(self, cycle):
        self.cycling_date = cycle.start_date
        p = cycle.period
        do_parsing = True
        while do_parsing:
            # Tasks nodes with correponding output but not input
            for name, task_graph_spec in cycle.tasks.items():
                # Task nodes
                # note: input, output and dependencies added at second traversing
                self.add_task(name)
                # output nodes
                for out_name in task_graph_spec.get("output", []):
                    self.add_data(out_name)
            # Continue cycling
            if not p:
                do_parsing = False
            else:
                self.cycling_date += p
                do_parsing = (self.cycling_date + p) <= cycle.end_date

    def _add_edges_from_cycle(self, cycle):
        self.cycling_date = cycle.start_date
        p = cycle.period
        do_parsing = True
        k = 0
        while do_parsing:
            cluster = []
            for name, task_graph_spec in cycle.tasks.items():
                task_node = self.get_task(name)
                cluster.append(task_node)
                # add input nodes
                for in_spec in task_graph_spec.get("input", []):
                    if in_node := self.get_data(in_spec):
                        if isinstance(in_node, list):
                            task_node.input.extend(in_node)
                        else:
                            task_node.input.append(in_node)
                        self.add_edge(in_node, task_node)
                # add output nodes
                for out_spec in task_graph_spec.get("output", []):
                    if out_node := self.get_data(out_spec):
                        task_node.output.append(out_node)
                        self.add_edge(task_node, out_node)
                        if not out_node.is_concrete():
                            cluster.append(out_node)
                # add dependencies
                for dep_spec in task_graph_spec.get("depends", []):
                    if dep_node := self.get_task(dep_spec):
                        if isinstance(dep_node, list):
                            task_node.depends.extend(dep_node)
                        else:
                            task_node.depends.append(dep_node)
                        self.add_edge(dep_node, task_node)
            # Add clsuter
            d1 = self.cycling_date
            dates = d1.isoformat()
            if p:
                d2 = self.cycling_date + p
                dates += f" -- {d2.isoformat()}"
            label = f"{cycle.name}\n{dates}"
            self.graph.add_subgraph(
                cluster,
                name=f"cluster_{cycle.name}_{k}",
                clusterrank="global",
                label=label,
                tooltip=label,
                **self.cluster_kw,
            )
            # Continue cycling
            if not p:
                do_parsing = False
            else:
                self.cycling_date += p
                k += 1
                do_parsing = (self.cycling_date + p) <= cycle.end_date

    def draw(self, **kwargs):
        # draw graphviz dot graph to svg file
        self.graph.layout(prog="dot")
        file_path = Path(f"./{self.graph.name}.svg")
        self.graph.draw(path=file_path, format="svg", **kwargs)

        # Add interactive capabilities to the svg graph thanks to
        # https://github.com/BartBrood/dynamic-SVG-from-Graphviz

        # Parse svg
        svg = etree.parse(file_path)
        svg_root = svg.getroot()
        # Add 'onload' tag
        svg_root.set("onload", "addInteractivity(evt)")
        # Add css style for interactivity
        with open("svg-interactive-style.css") as f:
            node = etree.Element("style")
            node.text = f.read()
            svg_root.append(node)
        # Add scripts
        with open("svg-interactive-script.js") as f:
            node = etree.Element("script")
            node.text = etree.CDATA(f.read())
            svg_root.append(node)
        # write svg again
        svg.write(file_path)
        # open in browser
        webbrowser.open(file_path.resolve().as_uri(), new=1)

    @classmethod
    def from_yaml(cls, config):
        config_path = Path(config)
        config = yaml.safe_load(config_path.read_text())
        return cls(
            *map(config["scheduling"].get, ("start_date", "end_date", "graph")),
            *map(config["runtime"].get, ("tasks", "data")),
            name=config_path.stem,
        )

    # ? JG mod here -> To build WorkGraph from dict
    def resolve_inputs(self, task, task_io_dict):
        # ? This should either resolve to the outputs of a previous node, or, if not, to the absolute inputs
        print("self.build_up_dict")
        pprint(self.build_up_dict, sort_dicts=False)

        # Extpar@2025-01-01-00-00
        # extpar_file@2025-01-01-00-00
        # extpar_file@2025-01-01-00-00

        # print('task_io_dict')
        # pprint(task_io_dict, sort_dicts=False)

        input_node_list = []

        prev_outputs = [
            list(_["outputs"].values())[0] for _ in self.build_up_dict.values()
        ]
        output_nodes = [_["task"] for _ in self.build_up_dict.values()]
        # print('prev_outputs', prev_outputs)
        # print('output_nodes', output_nodes)
        prev_output_node_mapping = dict(zip(prev_outputs, output_nodes))
        # print('prev_output_node_mapping')
        # pprint(prev_output_node_mapping, sort_dicts=False)

        # print('input_dict')
        print("prev_output_node_mapping", prev_output_node_mapping)
        for input_argument, input_instance in task_io_dict["inputs"].items():
            print("input_argument", input_argument)
            print("input_instance", input_instance)
            # ? This works if input of current task is output of previous task
            try:
                input_node_list.append(
                    prev_output_node_mapping[input_instance].outputs[input_argument]
                )
            except KeyError:
                print("input_instance")
                print(input_instance)
                print(self.data)
                # ? Here instead attach global input node. For now, just append as string as a quick hack.
                input_node_list.append(input_instance)
                pass

        print("input_node_list", input_node_list)

        # for prev_task, prev_task_outputs in zip(self.build_up_dict.keys(), :
        #     print(prev_task)
        #     print(prev_task_io_dict)

        # print(task_io_dict['inputs'].keys())
        input_node_mapping_dict = dict(
            zip(task_io_dict["inputs"].keys(), input_node_list)
        )
        print(f"task_name: {task}, input_node_mapping_dict")
        pprint(input_node_mapping_dict, sort_dicts=False)
        return input_node_mapping_dict

    def to_aiida_workgraph(self):
        tmp_dict = deepcopy(self.graph_dict)

        print("self.graph_dict")
        pprint(self.graph_dict, sort_dicts=False)

        for itask, (task, task_io_dict) in enumerate(self.graph_dict.items()):
            print("task", task)
            task_name_sanitized = sanitize_link_label(task)
            task_name_no_datetime = sanitize_link_label(task.split("@")[0].lower())

            task_inputs = self.resolve_inputs(task=task, task_io_dict=task_io_dict)

            wg_node = self.workgraph.nodes.new(
                "ShellJob",
                name=task_name_sanitized,
                command=load_code(task_name_no_datetime),
                arguments=list(task_io_dict["inputs"].keys()),
                # nodes=task_io_dict["inputs"],
                nodes=task_inputs,
                outputs=task_io_dict["outputs"],
            )

            self.build_up_dict[task] = tmp_dict.pop(task)
            self.build_up_dict[task]["task"] = wg_node

            # print("self.tmp_dict")
            # pprint(tmp_dict, sort_dicts=False)
            print("self.build_up_dict")
            pprint(self.build_up_dict, sort_dicts=False)

            # if itask > 2:
            #     raise SystemExit


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
    WCG = WcGraph.from_yaml(args.config)
    WCG.prepare()
    WCG.to_aiida_workgraph()
    # WCG.draw()


if __name__ == "__main__":
    main()
