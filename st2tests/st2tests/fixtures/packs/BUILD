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

# Please make sure to register all of the packs in this dir.
# For each pack, depend on the python_sources target (which depends on pack_metadata).
target(
    name="all_packs",
    dependencies=[
        "./action_chain_tests",
        "./core",
        "./dummy_pack_1",
        "./dummy_pack_2",
        "./dummy_pack_3",
        "./dummy_pack_4",
        "./dummy_pack_5",
        "./dummy_pack_6",
        "./dummy_pack_7",
        "./dummy_pack_8",
        "./dummy_pack_9",
        "./dummy_pack_10",
        "./dummy_pack_11",
        "./dummy_pack_12",
        "./dummy_pack_13",
        "./dummy_pack_14",
        "./dummy_pack_15",
        "./dummy_pack_16",
        "./dummy_pack_17",
        "./dummy_pack_18",
        "./dummy_pack_19",
        "./dummy_pack_20",
        "./dummy_pack_21",
        "./dummy_pack_22",
        "./dummy_pack_23",
        "./dummy_pack_schema_with_additional_items_1",
        "./dummy_pack_schema_with_additional_properties_1",
        "./dummy_pack_schema_with_nested_object_1",
        "./dummy_pack_schema_with_nested_object_2",
        "./dummy_pack_schema_with_nested_object_3",
        "./dummy_pack_schema_with_nested_object_4",
        "./dummy_pack_schema_with_nested_object_5",
        "./dummy_pack_schema_with_pattern_and_additional_properties_1",
        "./dummy_pack_schema_with_pattern_properties_1",
        "./orquesta_tests",
        "./pack_dir_name_doesnt_match_ref",
        "./pack_invalid_requirements",
        ":test_content_version",
        "./test_library_dependencies",
    ],
)
