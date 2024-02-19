resources(
    name="assets",
    sources=[
        "**/*.cer",
        "**/*.cnf",
        "**/*.p12",
        "**/*.pem",
        "ca/index.txt*",
        "ca/serial*",
        "README.md",
    ],
)

python_sources(
    dependencies=[":assets"],
)

shell_sources(
    name="util",
)
