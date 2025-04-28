file(
    name="st2client_sample_config",
    source="st2rc.sample.ini",
)

sample_conf(  # defined in pants-plugins/sample_conf
    name="st2.conf.sample",
    source="st2.conf.sample",
    dependencies=[
        "tools/config_gen.py",
    ],
)

file(
    name="logrotate",
    source="logrotate.conf",
)

file(
    name="nginx_sample_config",
    source="nginx/st2.conf",
)

file(
    name="st2_kvstore_demo_crypto_key",
    source="st2_kvstore_demo.crypto.key.json",
)

files(
    name="st2_tests_conf",
    sources=[
        "st2.tests*.conf",
    ],
    dependencies=[
        "st2auth/conf:htpasswd",
        "st2actions/conf:logging",
        "st2reactor/conf:logging",
        "st2tests/conf:other_logging_conf",
    ],
)

file(
    name="st2_dev_conf",
    source="st2.dev.conf",
    dependencies=[
        ":st2_kvstore_demo_crypto_key",
        "st2auth/conf:htpasswd",
        "st2actions/conf:logging",
        "st2api/conf:logging",
        "st2auth/conf:logging",
        "st2reactor/conf:logging",
        "st2stream/conf:logging",
    ],
)

file(
    name="st2_package_conf",
    source="st2.package.conf",
)

shell_command(
    name="htpasswd",
    description="An empty htpasswd file for st2-auth-backend-flat-file",
    command="touch htpasswd",
    tools=["touch"],
    output_files=["htpasswd"],
)

shell_command(
    name="packaged_st2_conf",
    execution_dependencies=[":st2_package_conf"],
    # virtualenv_opts is no longer needed for most OSes. We used to do this only for EL 8.
    command="""crudini --verbose --set st2.package.conf actionrunner virtualenv_opts ''""",
    runnable_dependencies=["//:crudini"],
    output_files=["st2.package.conf"],
)

nfpm_content_files(
    name="packaged_conf_files",
    dependencies=[
        ":packaged_st2_conf",
        ":logrotate",
        ":nginx_sample_config",
        ":htpasswd",
    ],
    files=[
        ("st2.package.conf", "/etc/st2/st2.conf"),
        ("logrotate.conf", "/etc/logrotate.d/st2"),
        ("nginx/st2.conf", "/usr/share/doc/st2/conf/nginx/st2.conf"),
        ("htpasswd", "/etc/st2/htpasswd"),
    ],
    content_type="config|noreplace",
    file_owner="root",
    file_group="root",
    file_mode="rw-r--r--",
    overrides={
        "/etc/st2/st2.conf": dict(
            # st2.conf typically contains secrets, so it is not world readable.
            file_mode="rw-r-----",  # NOTE: Packaging used to install this world readable.
            # TODO: Maybe set file_group=ST2_SVC_USER if a non-root process needs access.
        ),
        "/etc/st2/htpasswd": dict(
            file_owner=ST2_SVC_USER,
            file_group=ST2_SVC_USER,
            file_mode="rw-------",
        ),
        "/usr/share/doc/st2/conf/nginx/st2.conf": dict(
            content_type="",
        ),
    },
)
