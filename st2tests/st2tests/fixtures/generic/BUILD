pack_metadata(
    name="metadata",
    dependencies=[
        "./actions:shell",
        "./actions:shell_resources",
        # policytypes/fake_policy_type_1.py needs:
        "//st2tests/st2tests/policies/concurrency.py",
        # policytypes/fake_policy_type_2.py needs:
        "//st2tests/st2tests/policies/mock_exception.py",
        # policytypes/fake_policy_type_3.py needs:
        "//st2actions/st2actions/policies/concurrency_by_attr.py",
    ],
)

python_sources(
    dependencies=[":metadata"],
)
