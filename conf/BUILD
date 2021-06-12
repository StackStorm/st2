file(
    name="st2client_sample_config",
    source="st2rc.sample.ini",
)

file(
    name="st2.conf.sample",
    source="st2.conf.sample",
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
        "st2tests/conf:other-logging-conf",
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
