__defaults__(
    {(python_test, python_tests): dict(tags=["integration"])},
    extend=True,
)

python_tests(
    name="tests",
    dependencies=[
        # used by test_register_content_script
        "conf/st2.tests.conf:st2_tests_conf",
        "conf/st2.tests1.conf:st2_tests_conf",
    ],
)

python_test_utils(
    sources=["*.py", "!test_*.py"],
)
