import pytest

from sirocco.parsing import load_workflow_config
from sirocco.core import Workflow

@pytest.fixture
def config_file_small():
    return "files/configs/"


@pytest.mark.parametrize(
    "config_file", ["tests/files/configs/test_config_small.yml", "tests/files/configs/test_config_large.yml"]
)
def test_parse_config_file(config_file):
    config_workflow = load_workflow_config(config_file)
    core_workflow = Workflow(config_workflow)
    # TODO add test to compare str(core_workflow) against "tests/files/configs/test_config_xxx.txt"
