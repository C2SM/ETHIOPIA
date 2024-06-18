self_graph_dict = {
    "Extpar@2025-01-01-00-00": {
        "inputs": {"obs_data": "obs_data@2025-01-01-00-00"},
        "outputs": {"extpar_file": "extpar_file@2025-01-01-00-00"},
    },
    "preproc@2025-01-01-00-00": {
        "inputs": {
            "grid_file": "grid_file@2025-01-01-00-00",
            "extpar_file": "extpar_file@2025-01-01-00-00",
            "ERA5": "ERA5@2025-01-01-00-00",
        },
        "outputs": {"icon_input": "icon_input@2025-01-01-00-00"},
    },
    "preproc@2025-03-01-00-00": {
        "inputs": {
            "grid_file": "grid_file@2025-01-01-00-00",
            "extpar_file": "extpar_file@2025-01-01-00-00",
            "ERA5": "ERA5@2025-01-01-00-00",
        },
        "outputs": {"icon_input": "icon_input@2025-03-01-00-00"},
    },
    "preproc@2025-05-01-00-00": {
        "inputs": {
            "grid_file": "grid_file@2025-01-01-00-00",
            "extpar_file": "extpar_file@2025-01-01-00-00",
            "ERA5": "ERA5@2025-01-01-00-00",
        },
        "outputs": {"icon_input": "icon_input@2025-05-01-00-00"},
    },
    "preproc@2025-07-01-00-00": {
        "inputs": {
            "grid_file": "grid_file@2025-01-01-00-00",
            "extpar_file": "extpar_file@2025-01-01-00-00",
            "ERA5": "ERA5@2025-01-01-00-00",
        },
        "outputs": {"icon_input": "icon_input@2025-07-01-00-00"},
    },
    "ICON@2025-01-01-00-00": {
        "inputs": {
            "grid_file": "grid_file@2025-01-01-00-00",
            "icon_input": "icon_input@2025-01-01-00-00",
        },
        "outputs": {
            "stream_1": "stream_1@2025-01-01-00-00",
            "stream_2": "stream_2@2025-01-01-00-00",
            "restart": "restart@2025-01-01-00-00",
        },
    },
    "ICON@2025-03-01-00-00": {
        "inputs": {
            "grid_file": "grid_file@2025-01-01-00-00",
            "icon_input": "icon_input@2025-03-01-00-00",
            "restart": "restart@2025-01-01-00-00",
        },
        "outputs": {
            "stream_1": "stream_1@2025-03-01-00-00",
            "stream_2": "stream_2@2025-03-01-00-00",
            "restart": "restart@2025-03-01-00-00",
        },
    },
    "ICON@2025-05-01-00-00": {
        "inputs": {
            "grid_file": "grid_file@2025-01-01-00-00",
            "icon_input": "icon_input@2025-05-01-00-00",
            "restart": "restart@2025-03-01-00-00",
        },
        "outputs": {
            "stream_1": "stream_1@2025-05-01-00-00",
            "stream_2": "stream_2@2025-05-01-00-00",
            "restart": "restart@2025-05-01-00-00",
        },
    },
    "ICON@2025-07-01-00-00": {
        "inputs": {
            "grid_file": "grid_file@2025-01-01-00-00",
            "icon_input": "icon_input@2025-07-01-00-00",
            "restart": "restart@2025-05-01-00-00",
        },
        "outputs": {
            "stream_1": "stream_1@2025-07-01-00-00",
            "stream_2": "stream_2@2025-07-01-00-00",
            "restart": "restart@2025-07-01-00-00",
        },
    },
    "postproc 1@2025-01-01-00-00": {
        "inputs": {"stream_1": "stream_1@2025-01-01-00-00"},
        "outputs": {"postout_1": "postout_1@2025-01-01-00-00"},
    },
    "postproc 1@2025-03-01-00-00": {
        "inputs": {"stream_1": "stream_1@2025-03-01-00-00"},
        "outputs": {"postout_1": "postout_1@2025-03-01-00-00"},
    },
    "postproc 1@2025-05-01-00-00": {
        "inputs": {"stream_1": "stream_1@2025-05-01-00-00"},
        "outputs": {"postout_1": "postout_1@2025-05-01-00-00"},
    },
    "postproc 1@2025-07-01-00-00": {
        "inputs": {"stream_1": "stream_1@2025-07-01-00-00"},
        "outputs": {"postout_1": "postout_1@2025-07-01-00-00"},
    },
    "postproc 2@2025-01-01-00-00": {
        "inputs": {"stream_2": "stream_2@2025-07-01-00-00"},
        "outputs": {"postout_2": "postout_2@2025-01-01-00-00"},
    },
    "store & clean 1@2025-01-01-00-00": {
        "inputs": {
            "postout_1": "postout_1@2025-01-01-00-00",
            "stream_1": "stream_1@2025-01-01-00-00",
            "icon_input": "icon_input@2025-01-01-00-00",
        },
        "outputs": {"stored_data_1": "stored_data_1@2025-01-01-00-00"},
    },
    "store & clean 1@2025-03-01-00-00": {
        "inputs": {
            "postout_1": "postout_1@2025-03-01-00-00",
            "stream_1": "stream_1@2025-03-01-00-00",
            "icon_input": "icon_input@2025-03-01-00-00",
        },
        "outputs": {"stored_data_1": "stored_data_1@2025-01-01-00-00"},
    },
    "store & clean 1@2025-05-01-00-00": {
        "inputs": {
            "postout_1": "postout_1@2025-05-01-00-00",
            "stream_1": "stream_1@2025-05-01-00-00",
            "icon_input": "icon_input@2025-05-01-00-00",
        },
        "outputs": {"stored_data_1": "stored_data_1@2025-01-01-00-00"},
    },
    "store & clean 1@2025-07-01-00-00": {
        "inputs": {
            "postout_1": "postout_1@2025-07-01-00-00",
            "stream_1": "stream_1@2025-07-01-00-00",
            "icon_input": "icon_input@2025-07-01-00-00",
        },
        "outputs": {"stored_data_1": "stored_data_1@2025-01-01-00-00"},
    },
    "store & clean 2@2025-01-01-00-00": {
        "inputs": {
            "postout_2": "postout_2@2025-01-01-00-00",
            "stream_2": "stream_2@2025-07-01-00-00",
        },
        "outputs": {"stored_data_2": "stored_data_2@2025-01-01-00-00"},
    },
}
