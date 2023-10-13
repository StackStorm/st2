__defaults__(
    all=dict(
        resolve="pylint",
    )
)

python_sources()

python_tests(
    name="tests",
    dependencies=[
        "./fixtures",
        "!//conftest.py:test_utils",
    ],
)

python_requirement(
    name="pylint",
    requirements=[
        "pylint~=2.8.2",
        "setuptools",  # includes pkg_resources
    ],
)

python_requirement(
    name="astroid",
    # The version of astroid is constrained by the pylint version above
    requirements=["astroid"],
)
