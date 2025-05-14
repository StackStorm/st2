resources(
    sources=[
        "*.yaml",
        # pants ignores empty __init__.py files.
        # However, the tests for st2common.util.file_system need it to be present,
        # so we treat it as a resource instead of a python source file.
        "__init__.py",
    ],
)
