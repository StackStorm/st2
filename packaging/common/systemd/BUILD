_generators = (
    "st2api-generator",
    "st2auth-generator",
    "st2stream-generator",
)

python_sources(
    name="generator_files",
    sources=_generators,
)

nfpm_content_files(
    name="generators",
    description="systemd service generator files for nfpm packages",
    dependencies=[":generator_files"],
    files=[(gen, f"/usr/lib/systemd/system-generators/{gen}") for gen in _generators],
    file_owner="root",
    file_group="root",
    file_mode="rwxr-xr-x",
)
