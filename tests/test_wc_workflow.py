from wcflow.wc import WcWorkflow
from wcflow import core
from wcflow.workgraph import AiidaWorkGraph 
from pathlib import Path
import pytest

@pytest.fixture
def config_path_str():
    return "tests/files/configs/test_config.yaml"

def test_wc_workflow_init(config_path_str):
    wc_workflow = WcWorkflow.from_yaml(config_path_str)
    core_workflow: core.Workflow = wc_workflow.to_core_workflow()

    from aiida import load_profile
    load_profile()
    aiida_workgraph = AiidaWorkGraph(core_workflow)
    aiida_workgraph.run()