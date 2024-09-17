from wcflow import wc
from wcflow import core
from wcflow.workgraph import AiidaWorkGraph
from aiida.manage.configuration import load_profile
import pytest

@pytest.fixture
def small_config_path_str():
    return "tests/files/configs/test_config_small.yaml"

def test_small_wc_workflow(small_config_path_str):
    load_profile()
    wc_workflow = wc.Workflow.from_yaml(small_config_path_str)
    core_workflow: core.Workflow = wc_workflow.to_core_workflow()

    aiida_workgraph = AiidaWorkGraph(core_workflow)
    result = aiida_workgraph.run()
    assert result.get('execution_count') == 0
