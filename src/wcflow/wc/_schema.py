from strictyaml import Datetime, Map, MapPattern, Str, Seq, UniqueSeq, Optional

# Define the schema

CYCLES_TASK_INPUT_SCHEMA = Str() | MapPattern(Str(), Map({
    Optional("lag"): UniqueSeq(Str()) | Str(),
    Optional("date"): UniqueSeq(Datetime()) | Datetime(),
    Optional("argument"): Str(),
}))
CYCLES_TASK_DEPEND_SCHEMA = Str() | MapPattern(Str(), Map({
    Optional("lag"): UniqueSeq(Str()) | Str(),
}))
CYCLES_SCHEMA = Map({
        Optional("period"): Datetime(),
        Optional("period"): Str(),
        "tasks":MapPattern(
                Str(), Map({
                    "inputs": Seq(CYCLES_TASK_INPUT_SCHEMA),
                    "outputs": UniqueSeq(Str()),
                    Optional("arguments"): Seq(MapPattern(Str(), Str())),
                    Optional("depends"): Seq(CYCLES_TASK_DEPEND_SCHEMA),
                }))
        })
WORKFLOW_SCHEMA = Map({
    "start_date": Str(),
    "end_date": Str(),
    "cycles": MapPattern(Str(), CYCLES_SCHEMA),
    "tasks": MapPattern(Str(), MapPattern(Str(), Str() | MapPattern(Str(), Str()))),
    "data": MapPattern(Str(), Map({"type": Str(), "src": Str(), Optional("format"): Str()})),
})
