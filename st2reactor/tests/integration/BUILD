__defaults__(
    {python_test: dict(tags=["integration"])},
    extend=True,
)

_conf_deps = [
    "conf/st2.tests.conf:st2_tests_conf",
    "conf/st2.tests2.conf:st2_tests_conf",
]

python_tests(
    name="tests",
    dependencies=_conf_deps,
    uses=["mongo", "rabbitmq", "redis"],
    overrides={
        "test_garbage_collector.py": dict(
            dependencies=[
                *_conf_deps,
                "st2reactor/bin/st2garbagecollector",
            ],
            stevedore_namespaces=[
                "st2common.metrics.driver",
            ],
            entry_point_dependencies={
                "contrib/runners/inquirer_runner": ["st2common.runners.runner"],
            },
        ),
        "test_rules_engine.py": dict(
            dependencies=[
                *_conf_deps,
                "st2reactor/bin/st2timersengine",
            ],
            stevedore_namespaces=[
                "st2common.metrics.driver",
            ],
        ),
        "test_sensor_container.py": dict(
            dependencies=[
                *_conf_deps,
                "st2reactor/bin/st2sensorcontainer",
                "contrib/examples/sensors",
                "contrib/examples:metadata",
            ],
            stevedore_namespaces=[
                "st2common.metrics.driver",
            ],
        ),
        "test_sensor_watcher.py": dict(
            uses=["rabbitmq"],
        ),
    },
)
