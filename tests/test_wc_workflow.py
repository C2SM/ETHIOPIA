from pathlib import Path

import pytest

from sirocco.core import Workflow
from sirocco.pretty_print import PrettyPrinter
from sirocco.vizgraph import VizGraph
from sirocco.workgraph import AiidaWorkGraph


@pytest.mark.parametrize("config_path", [
    "tests/files/configs/test_config_small.yml",
    "tests/files/configs/test_config_parameters.yml",
])
def test_run_workgraph(config_path):
    core_workflow = Workflow.from_yaml(config_path)
    aiida_workflow = AiidaWorkGraph(core_workflow)
    out = aiida_workflow.run()
    assert out.get('execution_count', None).value == 0 # TODO should be 1 but we need to update workgraph for this

# configs that are tested only tested parsing
config_test_files = [
    "tests/files/configs/test_config_small.yml",
    "tests/files/configs/test_config_large.yml",
    "tests/files/configs/test_config_parameters.yml",
]

@pytest.fixture(params=config_test_files)
def config_case(request):
    config_path = Path(request.param)
    return (
        config_path,
        (config_path.parent.parent / "data" / config_path.name).with_suffix(".txt"),
    )

@pytest.fixture
def pprinter():
    return PrettyPrinter()

def test_parse_config_file(config_case, pprinter):
    config_path, reference_path = config_case
    reference_str = reference_path.read_text()
    test_str = pprinter.format(Workflow.from_yaml(config_path))
    if test_str != reference_str:
        new_path = Path(reference_path).with_suffix(".new.txt")
        new_path.write_text(test_str)
        assert reference_str == test_str, f"Workflow graph doesn't match serialized data. New graph string dumped to {new_path}."


@pytest.mark.skip(reason="don't run it each time, uncomment to regenerate serilaized data")
def test_serialize_workflow(config_case, pprinter):
    config_path, reference_path = config_case
    reference_path.write_text(pprinter.format(Workflow.from_yaml(config_path)))


def test_vizgraph(config_case):
    config_path, _ = config_case
    VizGraph.from_yaml(config_path).draw()
