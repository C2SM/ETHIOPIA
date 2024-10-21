# ETHIOPIA

ETHIOPIA (wEaTHer and clImate wOrkflow graPhs for aiIdA)
is a library for creating weather and climate workflows from a yaml
format inspired by [cylc](https://cylc.github.io/) using
[AiiDA](https://www.aiida.net/) as workflow engine.

## Install

To install it please use

``` bash
pip install -e .
```

## Developer tools

To manage the repo we use [hatch]{.title-ref} please install it

``` bash
pip install hatch
hatch shell # activate shell as dev environment 
hatch test # run tests
hatch fmt # run formatting
hatch run docs:build # build docs
hatch run docs:serve # live preview of doc for development
```

### Tests
``` bash
pip install hatch
verdi devel launch-add # creates required codes
verdi presto
hatch test
```

## Resources

-   <https://aiida-workgraph.readthedocs.io/en/latest/>
-   <https://github.com/aiidateam/aiida-workgraph>
