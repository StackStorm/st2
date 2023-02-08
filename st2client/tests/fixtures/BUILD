resources(
    name="execution_fixtures",
    sources=["execution*.json", "execution*.txt"],
)

resources(
    name="st2client_ini",
    sources=["*.ini"],
)

python_sources(
    dependencies=[":execution_fixtures"],
)
