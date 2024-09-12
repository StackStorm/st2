# The files in test_content_version* targets are in ./test_content_version
# which is a git submodule. pack_metadata_in_git_submodule will error with
# instructions on how to checkout the submodules if they are not checked out.
# The test_content_version* targets are dependencies of ./test_content_version_fixture

pack_metadata_in_git_submodule(
    name="test_content_version_metadata",
    sources=[
        "test_content_version/pack.yaml",
        "test_content_version/**/*.yaml",
        "test_content_version/icon.png",
        "test_content_version/requirements.txt",
    ],
    # NOTE: If you need the git metadata, make sure to depend on //:capture_git_modules
)

st2_shell_sources_and_resources(
    name="test_content_version_shell",
    # do not check across git submodule boundary
    skip_shellcheck=True,
    sources=[
        "test_content_version/**/*.sh",
    ],
)

python_sources(
    name="test_content_version",
    # do not fmt across git submodule boundary
    skip_black=True,
    dependencies=[
        ":test_content_version_metadata",
        ":test_content_version_shell",
        ":test_content_version_shell_resources",
    ],
    sources=[
        "test_content_version/**/*.py",
    ],
)

packs_glob(
    name="all_packs",
    dependencies=[
        # core is a symlink instead of a dir
        "./core",
        # use :test_content_version instead because of the git submodule
        ":test_content_version",
        "!./test_content_version_fixture",
        # these are not packs
        "!./configs",
        "!./executions",
        "!./runners",
        "!./all_packs_glob",  # the fixture that pulls in this target
    ],
)
