python_sources(
    dependencies=[
        ":openapi_spec",
    ]
)

# These may be loaded with st2common.util.spec_loader
resources(
    name="openapi_spec",
    sources=["openapi.yaml", "openapi.yaml.j2"],
)
