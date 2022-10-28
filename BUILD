python_requirements(
    name="reqs",
    source="requirements-pants.txt",
    module_mapping={
        "gitpython": ["git"],
        "python-editor": ["editor"],
        "python-json-logger": ["pythonjsonlogger"],
        "python-statsd": ["statsd"],
        "sseclient-py": ["sseclient"],
        "oslo.config": ["oslo_config"],
        "RandomWords": ["random_words"],
    },
    overrides={
        # flex and stevedore uses pkg_resources w/o declaring the dep
        ("flex", "stevedore"): {
            "dependencies": [
                "//:reqs#setuptools",
            ]
        },
        # do not use the prance[flex] extra as that pulls in an old version of flex
        "prance": {
            "dependencies": [
                "//:reqs#flex",
            ]
        },
        # tooz needs one or more backends (tooz is used by the st2 coordination backend)
        "tooz": {
            "dependencies": [
                "//:reqs#redis",
                "//:reqs#zake",
            ]
        },
    },
)

python_test_utils(
    name="test_utils0",
)
