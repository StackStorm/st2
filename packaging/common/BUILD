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

nfpm_content_symlinks(
    name="symlinks",
    symlinks=[
        # the symlink src will be made available during post-install script
        (f"/opt/stackstorm/st2/bin/{cmd}", f"/usr/bin/{cmd}")
        for cmd in (
            "st2",
            "st2-trigger-refire",
            "st2-rule-tester",
            "st2-run-pack-tests",
            "st2-register-content",
            "st2-apply-rbac-definitions",
            "st2-bootstrap-rmq",
            "st2-generate-symmetric-crypto-key",
            "st2-self-check",
            "st2-track-result",
            "st2-validate-pack-config",
            "st2ctl",
        )
    ],
    file_owner="root",
    file_group="root",
)
