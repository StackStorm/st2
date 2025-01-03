nfpm_content_dirs(
    name="root_dirs",
    dirs=[
        "/etc/st2",
        "/opt/stackstorm",
        "/opt/stackstorm/st2",
        "/usr/share/doc/st2",
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
    file_group=ST2_PACKS_GROUP,
    file_mode="rwxrwxr-x",
)

nfpm_content_dirs(
    name="st2_user_dirs",
    dirs=[
        "/opt/stackstorm/configs",
        "/opt/stackstorm/exports",
        "/opt/stackstorm/overrides",
        "/var/log/st2",
        "/var/run/st2",
    ],
    file_owner=ST2_SVC_USER,
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

target(
    name="conf_files",
    dependencies=[
        "//conf:packaged_conf_files",
        "//st2actions/conf:packaged_conf_files",
        "//st2api/conf:packaged_conf_files",
        "//st2auth/conf:packaged_conf_files",
        "//st2client/conf:packaged_bash_completion",
        "//st2reactor/conf:packaged_conf_files",
        "//st2stream/conf:packaged_conf_files",
    ],
)
