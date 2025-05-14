_services = (
    "st2actionrunner.service",
    "st2actionrunner@.service",
    "st2api.service",
    "st2auth.service",
    "st2garbagecollector.service",
    "st2notifier.service",
    "st2rulesengine.service",
    "st2scheduler.service",
    "st2sensorcontainer.service",
    "st2stream.service",
    "st2timersengine.service",
    "st2workflowengine.service",
)

files(
    name="service_files",
    sources=_services,
)

nfpm_content_files(
    name="services",
    description="systemd service files for nfpm rpm packages",
    dependencies=[":service_files"],
    files=[(svc, f"/usr/lib/systemd/system/{svc}") for svc in _services],
    file_owner="root",
    file_group="root",
    file_mode="rw-r--r--",
)
