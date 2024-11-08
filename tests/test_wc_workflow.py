import pytest

from sirocco.core import Workflow
from sirocco.parsing import load_workflow_config
from pathlib import Path

@pytest.fixture
def config_file_small():
    return "files/configs/"


@pytest.mark.parametrize(
    "config_file", ["tests/files/configs/test_config_small.yml", "tests/files/configs/test_config_large.yml"]
)
def test_parse_config_file(config_file):
    workflow = Workflow.from_yaml(config_file)
    assert str(workflow) == Path(config_file).with_suffix('.txt').read_text()
