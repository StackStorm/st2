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

nfpm_content_files(
    name="packaged_conf_files",
    dependencies=[
        ":st2_package_conf",
        ":logrotate",
    ],
    files=[
        ("st2.package.conf", "/etc/st2/st2.conf"),
        ("logrotate.conf", "/etc/logrotate.d/st2"),
    ],
    file_owner="root",
    file_group="root",
    file_mode="rw-r--r--",
)
