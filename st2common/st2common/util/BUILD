python_sources(
    overrides={
        "virtualenvs.py": dict(
            dependencies=[
                # make sure virtualenvs.py always has functioning virtualenv+pip
                "//:reqs#virtualenv",
                "//:reqs#pip",
                "//:reqs#setuptools",
                "//:reqs#wheel",
            ],
        ),
    },
)

# st2common.utils.concurrency allows using gevent instead of eventlet.
# This gevent support is WIP.
# python_requirement(
#    name="gevent",
#    requirements=["gevent"],
# )
