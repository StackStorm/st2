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
        "bin/st2-run-pack-tests:shell",
        "bin/st2ctl:shell",
        "bin/st2-self-check:shell",
        # dev scripts we might want to include
        # "bin/st2-generate-schemas",
    ],
)
