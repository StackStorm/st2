python_sources(
    sources=["*.py", "!*_test.py", "!data_fixtures.py"],
)

python_test_utils(
    name="test_utils",
    sources=["data_fixtures.py"],
)

python_tests(
    name="tests",
    # Do not enable `uses` for these tests.
    # These tests still need the running services, but if the plugin
    # is somehow broken, then any failures would prevent these tests
    # from running to tell us what is wrong.
    # overrides={
    #    "mongo_rules_test.py": dict(uses=["mongo"]),
    #    "rabbitmq_rules_test.py": dict(uses=["rabbitmq"]),
    #    "redis_rules_test.py": dict(uses=["redis"]),
    #    "system_user_test.py": dict(uses=["system_user"]),
    # },
)
