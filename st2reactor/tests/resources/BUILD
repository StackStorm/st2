python_sources(
    name="fixture_sensors",
    # Override the default sources to include test_sensor*.py
    # which are fixtures, not actual test files.
    sources=["test_sensor*.py"],
)

python_sources(
    dependencies=[":fixture_sensors"],
)
