from pathlib import Path

import pytest

from sirocco.core import Workflow
from sirocco.pretty_print import PrettyPrinter
from sirocco.vizgraph import VizGraph


@pytest.fixture
def pprinter():
    return PrettyPrinter()


config_test_files = [
    "tests/files/configs/test_config_small.yml",
    "tests/files/configs/test_config_large.yml",
    "tests/files/configs/test_config_parameters.yml",
]


@pytest.fixture(params=config_test_files)
def config_case(request):
    config_path = Path(request.param)
    return {
        'yml': config_path,
        'txt': (config_path.parent.parent / "data" / config_path.name).with_suffix(".txt"),
        'svg': (config_path.parent.parent / "svgs" / config_path.name).with_suffix(".svg"),
    }


def test_parse_config_file(config_case, pprinter):
    config_path, reference_path = config_case['yml'], config_case['txt']
    reference_str = reference_path.read_text()
    test_str = pprinter.format(Workflow.from_yaml(config_path))
    if test_str != reference_str:
        new_path = Path(reference_path).with_suffix(".new.txt")
        new_path.write_text(test_str)
        msg = f"Workflow graph doesn't match serialized data. New graph string dumped to {new_path}."
        raise ValueError(msg)


@pytest.mark.skip(reason="don't run it each time, uncomment to regenerate serilaized data")
def test_serialize_workflow(config_case, pprinter):
    config_path, reference_path = config_case['yml'], config_case['txt']
    reference_path.write_text(pprinter.format(Workflow.from_yaml(config_path)))


def test_vizgraph(config_case):
    config_path, svg_path =config_case['yml'], config_case['svg']
    VizGraph.from_yaml(config_path).draw(file_path=svg_path)
