# The files in test_content_version* targets are in ./test_content_version
# which is a git submodule.
# The test_content_version* targets are dependencies of ./test_content_version_fixture

GIT_SUBMODULES_INSTRUCTIONS = """
You need git submodules! Please init ... instructions
"""

pack_metadata_no_unmatched_globs(
    name="test_content_version_metadata",
    sources=[
        "test_content_version/pack.yaml",
        "test_content_version/**/*.yaml",
        "test_content_version/icon.png",
        "test_content_version/requirements.txt",
    ],
    message_on_unmatched_globs=GIT_SUBMODULES_INSTRUCTIONS,
)

shell_sources(
    name="test_content_version_shell",
    # do not check across git submodule boundary
    skip_shellcheck=True,
    sources=[
        "test_content_version/**/*.sh",
    ],
)

python_sources_no_unmatched_globs(
    name="test_content_version",
    # do not fmt across git submodule boundary
    skip_black=True,
    dependencies=[
        ":test_content_version_metadata",
        ":test_content_version_shell",
    ],
    sources=[
        "test_content_version/**/*.py",
    ],
    message_on_unmatched_globs=GIT_SUBMODULES_INSTRUCTIONS,
)
