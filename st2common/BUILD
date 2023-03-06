st2_component_python_distribution(
    component_name="st2common",
    scripts=[
        # some scripts in bin are only for development and should not be included.
        "bin/st2-bootstrap-rmq",
        "bin/st2-cleanup-db",
        "bin/st2-register-content",
        "bin/st2-purge-executions",
        "bin/st2-purge-workflows",
        "bin/st2-purge-task-executions",
        "bin/st2-purge-tokens",
        "bin/st2-purge-trigger-instances",
        "bin/st2-purge-traces",
        "bin/st2-purge-rule-enforcements",
        "bin/st2-generate-symmetric-crypto-key",
        "bin/st2-track-result",
        "bin/st2-validate-pack",
        "bin/st2-validate-pack-config",
        "bin/st2-pack-install",
        "bin/st2-pack-download",
        "bin/st2-pack-setup-virtualenv",
        "bin/migrations/v3.5/st2-migrate-db-dict-field-values",
        "bin/migrations/v3.8/st2-drop-st2exporter-marker-collections",
        "bin/st2-run-pack-tests:shell",
        "bin/st2ctl:shell",
        "bin/st2-self-check:shell",
        # dev scripts we might want to include
        # "bin/st2-generate-schemas",
    ],
    entry_points={
        stevedore_namespace("st2common.metrics.driver"): {
            "statsd": "st2common.metrics.drivers.statsd_driver:StatsdDriver",
            "noop": "st2common.metrics.drivers.noop_driver:NoopDriver",
            "echo": "st2common.metrics.drivers.echo_driver:EchoDriver",
        },
        stevedore_namespace("st2common.rbac.backend"): {
            "noop": "st2common.rbac.backends.noop:NoOpRBACBackend",
        },
    },
)
