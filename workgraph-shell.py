#%%

from sirocco.core import Workflow
from sirocco.parsing import load_workflow_config
from sirocco.pretty_print import PrettyPrinter
from sirocco.vizgraph import VizGraph
from sirocco.workgraph import AiidaWorkGraph

from aiida import orm, load_profile

load_profile()

config_test_files = [
    "/home/geiger_j/aiida_projects/aiida-icon-clm/git-repos/WCFlow/tests/files/configs/test_config_small.yml",
    "/home/geiger_j/aiida_projects/aiida-icon-clm/git-repos/WCFlow/tests/files/configs/test_config_large.yml",
    "/home/geiger_j/aiida_projects/aiida-icon-clm/git-repos/WCFlow/tests/files/configs/test_config_parameters.yml",
]
# config_path = Path(config_test_files[0])

for config_path in config_test_files:
    loaded_workflow_config = load_workflow_config(workflow_config=config_path)
    # pprint(type(loaded_workflow_config))

    core_workflow = Workflow.from_yaml(config_path)
    # pprint(wf_from_yaml)

    test_str = PrettyPrinter().format(core_workflow)
    # print(test_str)

    vizgraph = VizGraph.from_yaml(config_path)
    # print(vizgraph)
    # vizgraph.draw()

    aiida_wg = AiidaWorkGraph(core_workflow=core_workflow)

    break
