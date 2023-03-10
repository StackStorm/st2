resource(
    name="openapi_specs",
    source="openapi.yaml.j2",
)

# This is for an empty __init__.py file.
# Tests will import __package__ from it to tell dep inference it is needed.
python_sources(
    dependencies=[":openapi_specs"],
)
