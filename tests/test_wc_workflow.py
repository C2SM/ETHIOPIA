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
def config_paths(request):
    config_path = Path(request.param)
    return {
        "yml": config_path,
        "txt": (config_path.parent.parent / "data" / config_path.name).with_suffix(".txt"),
        "svg": (config_path.parent.parent / "svgs" / config_path.name).with_suffix(".svg"),
    }

@pytest.fixture
def pprinter():
    return PrettyPrinter()

def test_parse_config_file(config_paths, pprinter):
    reference_str = config_paths["txt"].read_text()
    test_str = pprinter.format(Workflow.from_yaml(config_paths["yml"]))
    if test_str != reference_str:
        new_path = Path(config_paths["txt"]).with_suffix(".new.txt")
        new_path.write_text(test_str)
        assert reference_str == test_str, f"Workflow graph doesn't match serialized data. New graph string dumped to {new_path}."


@pytest.mark.skip(reason="don't run it each time, uncomment to regenerate serilaized data")
def test_serialize_workflow(config_paths, pprinter):
    config_paths["txt"].write_text(pprinter.format(Workflow.from_yaml(config_paths["yml"])))


def test_vizgraph(config_paths):
    VizGraph.from_yaml(config_paths["yml"]).draw(file_path=config_paths["svg"])
