import pytest

from sirocco.parsing import load_workflow_config


@pytest.fixture
def config_file_small():
    return "files/configs/"


@pytest.mark.parametrize(
    "config_file", ["tests/files/configs/test_config_small.yml", "tests/files/configs/test_config_large.yml"]
)
def test_parse_config_file(config_file):
    config_workflow = load_workflow_config(config_file)
    config_workflow.to_core_workflow()
