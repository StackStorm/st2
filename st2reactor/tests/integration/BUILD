__defaults__(
    {(python_test, python_tests): dict(tags=["integration"])},
    extend=True,
)

python_tests(
    name="tests",
    dependencies=[
        "conf/st2.tests.conf:st2_tests_conf",
        "conf/st2.tests2.conf:st2_tests_conf",
    ],
)
