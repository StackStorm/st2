# The files in test_content_version* targets are in ./test_content_version
# which is a git submodule. pack_metadata_in_git_submodule will error with
# instructions on how to checkout the submodules if they are not checked out.
# The test_content_version* targets are dependencies of ./test_content_version_fixture

# pack_metadata_in_git_submodule(
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
    ],
    sources=[
        "test_content_version/**/*.py",
    ],
)

target(
    name="packs_metadata",
    dependencies=[
        # sadly dependencies can't use globs. We must list every subdirectory.
        "./action_chain_tests:metadata",
        "./dummy_pack_1:metadata",
        "./dummy_pack_2:metadata",
        "./dummy_pack_3:metadata",
        "./dummy_pack_4:metadata",
        "./dummy_pack_5:metadata",
        "./dummy_pack_6:metadata",
        "./dummy_pack_7:metadata",
        "./dummy_pack_8:metadata",
        "./dummy_pack_9:metadata",
        "./dummy_pack_10:metadata",
        "./dummy_pack_11:metadata",
        "./dummy_pack_12:metadata",
        "./dummy_pack_13:metadata",
        "./dummy_pack_14:metadata",
        "./dummy_pack_15:metadata",
        "./dummy_pack_16:metadata",
        "./dummy_pack_17:metadata",
        "./dummy_pack_18:metadata",
        "./dummy_pack_19:metadata",
        "./dummy_pack_20:metadata",
        "./dummy_pack_21:metadata",
        "./dummy_pack_22:metadata",
        "./dummy_pack_schema_with_additional_properties_1:metadata",
        "./dummy_pack_schema_with_nested_object_1:metadata",
        "./dummy_pack_schema_with_nested_object_2:metadata",
        "./dummy_pack_schema_with_nested_object_3:metadata",
        "./dummy_pack_schema_with_nested_object_4:metadata",
        "./dummy_pack_schema_with_nested_object_5:metadata",
        "./orquesta_tests:metadata",
        "./pack_dir_name_doesnt_match_ref:metadata",
        "./pack_invalid_requirements:metadata",
        "./test_library_dependencies:metadata",
        "./test_content_version:metadata",  # submodule
        # "./core:metadata",  # todo: how to deal with a symlink like this? relocated_files?
    ],
)
