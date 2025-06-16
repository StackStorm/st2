__defaults__(
    all=dict(
        resolve="pylint",
    )
)

python_sources()

python_tests(
    name="tests",
    tags=["unit"],
    dependencies=[
        "./fixtures",
        "!//conftest.py:test_utils",
    ],
)

python_requirement(
    name="pylint",
    requirements=[
        "pylint~=3.1.0",
        "setuptools",  # includes pkg_resources
    ],
)

python_requirement(
    name="astroid",
    # The version of astroid is constrained by the pylint version above
    requirements=["astroid"],
)
