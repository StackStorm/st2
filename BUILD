python_requirements(
    name="reqs",
    source="requirements-pants.txt",
    # module_mapping can be removed once pants is released with
    # https://github.com/pantsbuild/pants/pull/17390
    module_mapping={
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
        # make sure anything that uses st2-auth-ldap gets the st2auth constant
        "st2-auth-ldap": {
            "dependencies": [
                "st2auth/st2auth/backends/constants.py",
            ]
        },
    },
)

target(
    name="auth_backends",
    dependencies=[
        "//:reqs#st2-auth-backend-flat-file",
        "//:reqs#st2-auth-ldap",
    ],
)

python_test_utils(
    name="test_utils",
    skip_pylint=True,
)
