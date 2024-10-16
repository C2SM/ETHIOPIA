import pytest

from wcflow.parsing import load_workflow_config


@pytest.fixture
def config_file_small():
    return "files/configs/"


#@pytest.mark.parametrize(
#    "config_file", ["tests/files/configs/test_config_small.yml", "tests/files/configs/test_config_large.yml"]
#)
#def test_convert_config_file(config_file):
#    config_workflow = load_workflow_config(config_file)
#    core_workflow = config_workflow.to_core_workflow()
#    AiidaWorkGraph(core_workflow)


@pytest.mark.parametrize("config_file", ["tests/files/configs/test_config_small.yml"])
def test_run_config_file(config_file):
    config_workflow = load_workflow_config(config_file)
    core_workflow = config_workflow.to_core_workflow()
    aiida_workflow = AiidaWorkGraph(core_workflow)
    aiida_workflow.run()
