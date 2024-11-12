from pathlib import Path

import pytest

from sirocco.core import Workflow


@pytest.fixture
def config_file_small():
    return "files/configs/"


config_test_files = ["tests/files/configs/test_config_small.yml", "tests/files/configs/test_config_large.yml"]


@pytest.mark.parametrize("config_file", config_test_files)
def test_parse_config_file(config_file):
    config_path = Path(config_file)
    reference_str = (config_path.parent / ".." / "data" / config_path.name).with_suffix(".txt").read_text()
    test_str = str(Workflow.from_yaml(config_file))
    if test_str != reference_str:
        new_path = Path(config_file).with_suffix(".new.txt")
        new_path.write_text(test_str)
        msg = f"Workflow graph doesn't match serialized data. New graph string dumped to {new_path}."
        raise ValueError(msg)


@pytest.mark.skip(reason="don't run it each time, uncomment to regenerate serilaized data")
@pytest.mark.parametrize("config_file", config_test_files)
def test_serialize_workflow(config_file):
    config_path = Path(config_file)
    reference_path = (config_path.parent / ".." / "data" / config_path.name).with_suffix(".txt")
    reference_path.write_text(str(Workflow.from_yaml(config_file)))
