import argparse

from aiida.manage.configuration import load_profile

from wcflow import core, wc, workgraph

load_profile()


def main():
    parser = argparse.ArgumentParser(description="Runs a WC workfow from yaml file.")
    parser.add_argument("wc_yaml", type=str, help="The yaml file describing a wc workflow.")
    args = parser.parse_args()

    wc_workflow = wc.Workflow.from_yaml(args.wc_yaml)
    core_workflow: core.Workflow = wc_workflow.to_core_workflow()

    aiida_workgraph = workgraph.AiidaWorkGraph(core_workflow)
    print("Starting workflow please run `workgraph web start` in another terminal to start a GUI as webservice.")  # noqa: T201
    result = aiida_workgraph.run()
    print("Result:", result)  # noqa: T201
