python_tests(
    skip_pylint=True,
    overrides={
        "test_action_download.py": {
            "dependencies": [
                # imports tests.fixtures which is ambiguous. Tell pants which one to use.
                "./fixtures",
            ],
        }
    },
)
