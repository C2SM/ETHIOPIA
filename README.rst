.. marker-intro

Weather and Climate Workflow Tool based on AiiDA
================================================

WcFlow is a library for creating weather and climate workflows from a yaml format inspired by `cylc <https://cylc.github.io/>`_ using `AiiDA <https://www.aiida.net/>`_ as workflow engine.

.. marker-installation-aiida

Installing AiiDA
----------------

To install AiiDA, it is first recommended to create a virtual environment, e.g. via ``venv`` and activate it:

.. code-block:: bash

    python -m venv ~/.python_venvs/wcflow
    source ~/.python_venvs/wcflow/bin/activate

The ``aiida-core`` package can then be installed with pip:

.. code-block:: bash

    pip install aiida-core

Finally, ``verdi presto`` can be used to quickly set up an AiiDA profile using SQLite via:

.. code-block:: bash

    verdi presto --profile-name wcflow

Further information on the installation can be found in the 
`AiiDA documentation <https://aiida.readthedocs.io/projects/aiida-core/en/latest/installation/index.html>`_,
which covers (among other topics) how to set up RabbitMQ, necessary to run processes in the background in a non-blocking manner, as well as how use a more performant PostgreSQL database.

.. marker-installation

Installing the package for development
--------------------------------------

To install the package please use

.. code-block:: bash

    pip install -e .

This will automatically install the additional, required packages, ``aiida-shell`` and ``aiida-workgraph`` at compatible versions.

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
