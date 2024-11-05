from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from lxml import etree
from pygraphviz import AGraph

if TYPE_CHECKING:
    from sirocco.core import Store
from sirocco.core import Workflow


class VizGraph:
    """Class for visualizing a Sirocco workflow"""

    node_base_kw = {'style': 'filled', 'fontname': 'Fira Sans', 'fontsize': 14, 'penwidth': 2}
    edge_base_kw = {'color': '#77767B', 'penwidth': 1.5}
    task_node_kw = node_base_kw | {'shape': 'box', 'fillcolor': '#ffd8dc', 'fontcolor': '#330005', 'color': '#4F161D'}
    data_gen_node_kw = node_base_kw | {'shape': 'ellipse', 'fillcolor': '#d8e9ff', 'fontcolor': '#001633', 'color': '#001633'}
    data_av_node_kw = node_base_kw | {'shape': 'ellipse', 'fillcolor': '#c5e5c3', 'fontcolor': '#001633', 'color': '#2d3d2c'}
    cluster_kw = {'bgcolor': '#F6F5F4', 'color': None, 'fontsize': 16}
    io_edge_kw = edge_base_kw
    wait_on_edge_kw = edge_base_kw | {'style': 'dashed'}

    def __init__(self, name:str, cycles: Store, data: Store) -> None:

        self.name = name
        self.agraph = AGraph(name=name, fontname='Fira Sans', newrank=True)
        for data_node in data.values():
            if data_node.available:
                gv_kw = self.data_av_node_kw
            else:
                gv_kw = self.data_gen_node_kw
            self.agraph.add_node(data_node, label=data_node.name, **gv_kw)

        k = 1
        for cycle in cycles.values():
            # NOTE: For some reason, clusters need to have a unique name that starts with 'cluster'
            #       otherwise they are not taken into account. Hence the k index.
            cluster_nodes = []
            for task_node in cycle.tasks:
                cluster_nodes.append(task_node)
                self.agraph.add_node(task_node, label=task_node.name, **self.task_node_kw)
                for data_node in task_node.inputs:
                    self.agraph.add_edge(data_node, task_node, **self.io_edge_kw)
                for data_node in task_node.outputs:
                    self.agraph.add_edge(task_node, data_node, **self.io_edge_kw)
                    cluster_nodes.append(data_node)
                for wait_task_node in task_node.wait_on:
                    self.agraph.add_edge(wait_task_node, task_node, **self.wait_on_edge_kw)
            cluster_label = cycle.name
            if cycle.date is not None:
                cluster_label += "\n" + cycle.date.isoformat()
            self.agraph.add_subgraph(cluster_nodes,
                                     name=f'cluster_{cycle.name}_{k}',
                                     clusterrank='global',
                                     label=cluster_label,
                                     tooltip=cluster_label,
                                     **self.cluster_kw)
            k += 1

    def draw(self, **kwargs):
        # draw graphviz dot graph to svg file
        self.agraph.layout(prog='dot')
        file_path = Path(f'./{self.name}.svg')
        self.agraph.draw(path=file_path, format='svg', **kwargs)

        # Add interactive capabilities to the svg graph thanks to
        # https://github.com/BartBrood/dynamic-SVG-from-Graphviz

        # Parse svg
        svg = etree.parse(file_path)
        svg_root = svg.getroot()
        # Add 'onload' tag
        svg_root.set('onload', 'addInteractivity(evt)')
        # Add css style for interactivity
        this_dir = Path(__file__).parent
        style_file_path = this_dir / 'svg-interactive-style.css'
        node = etree.Element('style')
        node.text = style_file_path.read_text()
        svg_root.append(node)
        # Add scripts
        js_file_path = this_dir / 'svg-interactive-script.js'
        node = etree.Element('script')
        node.text = etree.CDATA(js_file_path.read_text())
        svg_root.append(node)

        # write svg again
        svg.write(file_path)

    @classmethod
    def from_core_workflow(cls, workflow: Workflow):
        return cls(workflow.name, workflow.cycles, workflow.data)

    @classmethod
    def from_yaml(cls, config_path: str):
        return cls.from_core_workflow(Workflow.from_yaml(config_path))
