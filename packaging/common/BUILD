_packs_group = "st2packs"
_st2_user = "st2"

nfpm_content_dirs(
    name="root_dirs",
    dirs=[
        # "/etc/bash_completion.d",
        # "/etc/logrotate.d",
        "/etc/st2",
        "/opt/stackstorm",
        "/opt/stackstorm/st2",
        "/usr/share/doc/st2",
        "/var/log/st2",
        "/var/run/st2",
    ],
    file_owner="root",
    file_group="root",
    file_mode="rwxr-xr-x",
)

nfpm_content_dirs(
    name="packs_group_dirs",
    dirs=[
        "/opt/stackstorm/packs",
        "/opt/stackstorm/virtualenvs",
        "/usr/share/doc/st2/examples",
    ],
    file_owner="root",
    file_group=_packs_group,
    file_mode="rwxrwxr-x",
)

nfpm_content_dirs(
    name="st2_user_dirs",
    dirs=[
        "/opt/stackstorm/configs",
        "/opt/stackstorm/exports",
        "/opt/stackstorm/overrides",
    ],
    file_owner=_st2_user,
    file_group="root",
    file_mode="rwxr-xr-x",
)

target(
    name="dirs",
    dependencies=[
        ":root_dirs",
        ":packs_group_dirs",
        ":st2_user_dirs",
    ],
)
