python_tests(
    skip_pylint=True,
    overrides={
        "test_action_sendmail.py": dict(
            dependencies=[
                # contrib/core is symlinked to st2tests/st2tests/fixtures/packs/core
                # so pants thinks "mail-parser" is defined twice, making it ambiguous.
                # Use contrib/core as the canonical copy.
                "contrib/core:reqs#mail-parser",
            ],
        ),
    },
)
