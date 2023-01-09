python_sources()

python_tests(
    name="tests",
    overrides={
        # We use this plugin to validate we can run the tests for it.
        "mongo_rules_test.py": {"uses": ["mongo"]},
    }
)
