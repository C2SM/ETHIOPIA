from __future__ import annotations

from pathlib import Path

import strictyaml  # type: ignore[import-untyped]
from strictyaml import Datetime, Map, MapPattern, Optional, Seq, Str, UniqueSeq  # type: ignore[import-untyped]

# Define the schema

CYCLES_TASK_INPUT_SCHEMA = Str() | MapPattern(
    Str(),
    Map(
        {
            Optional("lag"): UniqueSeq(Str()) | Str(),
            Optional("date"): UniqueSeq(Datetime()) | Datetime(),
            Optional("arg_option"): Str(),
        }
    ),
)
CYCLES_TASK_DEPEND_SCHEMA = Str() | MapPattern(
    Str(),
    Map(
        {
            Optional("lag"): UniqueSeq(Str()) | Str(),
            Optional("date"): UniqueSeq(Str()) | Str(),
        }
    ),
)
CYCLES_SCHEMA = Map(
    {
        Optional("period"): Datetime(),
        Optional("period"): Str(),
        "tasks": MapPattern(
            Str(),
            Map(
                {
                    Optional("inputs"): Seq(CYCLES_TASK_INPUT_SCHEMA),
                    Optional("outputs"): UniqueSeq(Str()),
                    Optional("depends"): Seq(CYCLES_TASK_DEPEND_SCHEMA),
                }
            ),
        ),
    }
)
WORKFLOW_SCHEMA = Map(
    {
        "start_date": Str(),
        "end_date": Str(),
        "cycles": MapPattern(Str(), CYCLES_SCHEMA),
        "tasks": MapPattern(Str(), MapPattern(Str(), Str() | MapPattern(Str(), Str()))),
        "data": MapPattern(Str(), Map({"type": Str(), "src": Str(), Optional("format"): Str()})),
    }
)


def load_yaml(path: Path | str) -> dict:
    """
    Load and validates a yaml file representing a WC workflow.
    """
    if isinstance(path, str):
        path = Path(path)
    return strictyaml.load(path.read_text(), WORKFLOW_SCHEMA, label=path.absolute().__str__()).data
