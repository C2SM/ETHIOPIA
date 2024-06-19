from wcflow.parse_to_workgraph import WcWorkflow
import pytest

@pytest.fixture
def config_file():
    return "src/wcflow/prototype_config.yaml"

def test_wc_workflow_init(config_file):
    WcWorkflow.from_yaml(config_file)

