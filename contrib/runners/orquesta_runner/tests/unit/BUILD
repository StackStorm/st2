__defaults__(
    {python_test: dict(tags=["unit"])},
    extend=True,
)

python_tests(
    name="tests",
    overrides={
        (
            "test_basic.py",
            "test_cancel.py",
            "test_context.py",
            "test_error_handling.py",
            "test_pause_and_resume.py",
            "test_with_items.py",
        ): dict(
            uses=["system_user"],
        ),
    },
)

python_test_utils(
    sources=["*.py", "!test_*.py"],
)
