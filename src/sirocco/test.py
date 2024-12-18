data = {
    'name': 'inputs',
    'identifier': 'node_graph.namespace',
    'link_limit': 1000000.0,
    'links': [],
    'metadata': {},
    'sockets': {
        'metadata': {
            'name': 'metadata',
            'identifier': 'workgraph.namespace',
            'link_limit': 1,
            'links': [],
            'metadata': {
                'arg_type': 'kwargs',
                'required': False,
                'dynamic': False
            },
            'sockets': {
                'store_provenance': {
                    'name': 'store_provenance',
                    'identifier': 'workgraph.bool',
                    'link_limit': 1,
                    'links': [],
                    'metadata': {'arg_type': 'kwargs', 'required': False},
                    'property': {
                        'value': None,
                        'name': 'store_provenance',
                        'identifier': 'workgraph.bool',
                        'default': None,
                        'metadata': {},
                        'list_index': 0,
                        'arg_type': 'kwargs'
                    }
                },
                'description': {
                    'name': 'description',
                    'identifier': 'workgraph.any',
                    'link_limit': 1,
                    'links': [],
                    'metadata': {'arg_type': 'kwargs', 'required': False},
                    'property': {
                        'value': None,
                        'name': 'description',
                        'identifier': 'workgraph.any',
                        'default': None,
                        'metadata': {},
                        'list_index': 0,
                        'arg_type': 'kwargs'
                    }
                },
                'label': {
                    'name': 'label',
                    'identifier': 'workgraph.any',
                    'link_limit': 1,
                    'links': [],
                    'metadata': {'arg_type': 'kwargs', 'required': False},
                    'property': {
                        'value': None,
                        'name': 'label',
                        'identifier': 'workgraph.any',
                        'default': None,
                        'metadata': {},
                        'list_index': 0,
                        'arg_type': 'kwargs'
                    }
                },
                'call_link_label': {
                    'name': 'call_link_label',
                    'identifier': 'workgraph.string',
                    'link_limit': 1,
                    'links': [],
                    'metadata': {'arg_type': 'kwargs', 'required': False},
                    'property': {
                        'value': None,
                        'name': 'call_link_label',
                        'identifier': 'workgraph.string',
                        'default': None,
                        'metadata': {},
                        'list_index': 0,
                        'arg_type': 'kwargs'
                    }
                },
                # ... (continue similar patterns for remaining keys)
            }
        },
        'code': {
            'name': 'code',
            'identifier': 'workgraph.any',
            'link_limit': 1,
            'links': [],
            'metadata': {'arg_type': 'kwargs', 'required': True},
            'property': {
                'value': None,
                'name': 'code',
                'identifier': 'workgraph.any',
                'default': None,
                'metadata': {},
                'list_index': 0,
                'arg_type': 'kwargs'
            }
        },
        'monitors': {
            'name': 'monitors',
            'identifier': 'workgraph.namespace',
            'link_limit': 1,
            'links': [],
            'metadata': {'arg_type': 'kwargs', 'required': False, 'dynamic': True},
            'sockets': {}
        },
        'remote_folder': {
            'name': 'remote_folder',
            'identifier': 'workgraph.any',
            'link_limit': 1,
            'links': [],
            'metadata': {'arg_type': 'kwargs', 'required': False},
            'property': {
                'value': None,
                'name': 'remote_folder',
                'identifier': 'workgraph.any',
                'default': None,
                'metadata': {},
                'list_index': 0,
                'arg_type': 'kwargs'
            }
        },
    }
}
