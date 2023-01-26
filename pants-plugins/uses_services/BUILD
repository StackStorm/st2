python_sources(
    sources=["*.py", "!*_test.py", "!data_fixtures.py"],
)

python_test_utils(
    name="test_utils",
    sources=["data_fixtures.py"],
)

python_tests(
    name="tests",
    overrides={
        # We use this plugin to validate we can run the tests for it.
        "mongo_rules_test.py": {"uses": ["mongo"]},
    },
)
