st2_component_python_distribution(
    component_name="st2client",
    entry_points={
        "console_scripts": {
            "st2": "st2client.shell:main",
        },
    },
    dependencies=[
        # required for SOCKS proxy support (HTTP_PROXY, HTTPS_PROXY, NO_PROXY)
        ":pysocks",
    ],
)

python_requirement(
    name="pysocks",
    requirements=["pysocks"],
)
