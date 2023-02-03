pack_metadata(
    name="metadata",
)

python_requirements(
    name="reqs",
    source="requirements-tests.txt",
    # module_mapping can be removed once pants is released with
    # https://github.com/pantsbuild/pants/pull/17390
    module_mapping={"mail-parser": ["mailparser"]},
)

python_sources(
    dependencies=[":metadata"],
)
