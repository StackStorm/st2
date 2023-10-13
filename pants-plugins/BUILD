__defaults__(
    all=dict(
        resolve="pants-plugins",
        skip_pylint=True,
        interpreter_constraints=["CPython>=3.7,<3.10"],
    )
)

# this adds a dependency on the pants libs using the version specified in pants.toml
pants_requirements(
    name="pants",
    testutil=True,
)

python_sources()
