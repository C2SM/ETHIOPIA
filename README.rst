.. marker-intro

Weather and Climate Workflow Tool based on AiiDA
================================================

WcFlow a library for creating weather and climate workflows from a yaml format inspired by `cylc <https://cylc.github.io/>`_ using `AiiDA <https://www.aiida.net/>`_ as workflow engine.

.. marker-installation

Install
-------

To install it please use

.. code-block:: bash

    pip install -e .

.. marker-developer-tools

Developer tools
---------------

To manage the repo we use `hatch` please install it

.. code-block:: bash

    pip install hatch
    hatch test # run tests
    hatch fmt # run formatting
    hatch run docs:build # build docs

Resources
---------
- https://aiida-workgraph.readthedocs.io/en/latest/
- https://github.com/superstar54/aiida-workgraph
