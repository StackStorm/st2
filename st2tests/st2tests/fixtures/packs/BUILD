# The files in test_content_version* targets are in ./test_content_version
# which is a git submodule.
# The test_content_version* targets are dependencies of ./test_content_version_fixture

resources(
    name="test_content_version_metadata",
    sources=[
        "test_content_version/pack.yaml",
        "test_content_version/**/*.yaml",
        "test_content_version/icon.png",
        "test_content_version/requirements.txt",
    ],
)

shell_sources(
    name="test_content_version_shell",
    sources=[
        "test_content_version/**/*.sh",
    ],
)

python_sources(
    name="test_content_version",
    dependencies=[
        ":test_content_version_metadata",
        ":test_content_version_shell",
    ],
    sources=[
        "test_content_version/**/*.py",
    ],
)
