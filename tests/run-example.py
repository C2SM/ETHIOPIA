#%%
from pathlib import Path

from sirocco.parsing import load_workflow_config
from sirocco.core import Workflow
from sirocco.pretty_print import PrettyPrinter
from sirocco.vizgraph import VizGraph
from rich.pretty import pprint


config_test_files = [
    "tests/files/configs/test_config_small.yml",
    "tests/files/configs/test_config_large.yml",
    "tests/files/configs/test_config_parameters.yml",
]
config_path = Path(config_test_files[0])

loaded_workflow_config = load_workflow_config(workflow_config=config_path)
pprint(type(loaded_workflow_config))

wf_from_yaml = Workflow.from_yaml(config_path)
pprint(wf_from_yaml)

# test_str = PrettyPrinter.format(wf_from_yaml)
# pprint(test_str)