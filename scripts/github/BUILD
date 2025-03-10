files(
    name="assets",
    sources=[
        "*.txt",
        "*.conf",
    ],
)

shell_sources(
    dependencies=[":assets"],
    overrides={
        (
            "install-apt-packages-use-cache.sh",
            "install-mongosh.sh",
            "install-virtualenv.sh",
            "setup-environment.sh",
        ): dict(skip_shfmt=True),
    },
)
