shell_sources()

nfpm_content_file(
    name="packaged_bash_completion",
    dependencies=["./st2.complete.sh"],
    src="st2.complete.sh",
    dst="/etc/bash_completion.d/st2",
    content_type="config",
    file_owner="root",
    file_group="root",
    file_mode="rwxr-xr-x",
)
