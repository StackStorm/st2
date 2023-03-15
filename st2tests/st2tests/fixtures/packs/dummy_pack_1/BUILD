pack_metadata(
    name="metadata",
)

python_sources(
    dependencies=[
        ":metadata",
        "./actions",
        "./sensors",
        "./etc",  # extra binary files for st2api/tests/unit/controllers/v1/test_packs_views.py
        "st2tests/st2tests/fixtures/packs/configs/dummy_pack_1.yaml",
    ],
)
