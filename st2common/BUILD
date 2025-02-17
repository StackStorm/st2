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
    dependencies=[
        # no entry-point or script yet
        "./st2common/garbage_collection/inquiries.py",  # missing cmd + ./bin/st2-purge-inquiries
        #
        # Things that need to be included as part of the st2common library's API:
        #
        # ### Public API ###
        #
        "./st2common/logging",  # used by all of our logging conf files
        "./st2common/models/system",  # used by runners
        "./st2common/policies",  # used by policies (see st2actions.policies)
        "./st2common/runners",  # used by runners and python actions
        #
        # ### Mixed Public+Internal API ###
        #
        "./st2common/services",  # used by runners, python actions, st2api, ...
        #
        # ### Internal API ###
        #
        "./st2common/constants/garbage_collection.py",  # used by garbage collector
        "./st2common/constants/policy.py",  # used by st2scheduler (in st2actions)
        "./st2common/constants/timer.py",  # used by st2timersengine (in st2reactor)
        "./st2common/middleware",  # used by st2auth, st2api, st2stream
        "./st2common/models/api",  # used by st2auth, st2api, st2stream
        "./st2common/models/system",  # used by st2auth, st2api, st2stream
        "./st2common/models/db/timer.py",  # used by st2api
        "./st2common/models/db/webhook.py",  # used by st2api
        "./st2common/persistence/execution_queue.py",  # used by st2scheduler (in st2actions)
        "./st2common/stream",  # used by st2stream
        "./st2common/transport/consumers.py",  # used by st2actions- and st2reactor-related services
        "./st2common/util/actionalias_helpstring.py",  # used by st2api
        "./st2common/util/auth.py",  # used by st2api, st2auth
        "./st2common/util/keyvalue.py",  # used by st2api
        "./st2common/util/sandboxing.py",  # used by python runner and sensor container
        "./st2common/util/service.py",  # used by st2scheduler (in st2actions)
        "./st2common/util/wsgi.py",  # used by st2stream
        "./st2common/validators/api/misc.py",  # used by st2api
        #
        # ### Dead Code (?) ###
        #
        # Added gunicorn bug workaround for SyncWorker users in #2571. No known active users. To use:
        #   `gunicorn -k st2common.util.gunicorn_workers.EventletSyncWorker ...`
        # "./st2common/util/gunicorn_workers.py",
        #
        # Known dead code that should be deleted. Do not add these:
        # ./st2common/callback/* (was for the old mistral_v2 runner. see #4038)
        # ./st2common/constants/scheduler.py (unused since #4397)
        # ./st2common/content/validators.py (unused since #939)
        # ./st2common/exceptions/api.py (unused since #1840)
        # ./st2common/exceptions/connection.py (unused since #1794)
        # ./st2common/exceptions/resultstracker.py (unused since #5011)
        # ./st2common/models/api/actionrunner.py (unused since #442)
        # ./st2common/models/db/reactor.py (unused since #5922)
        # ./st2common/persistence/reactor.py (unused since #5922)
        # ./st2common/util/argument_parser.py (never used since added in e9ae7e31e1eb47e49f0fdc414ed6d2b8eccf4748)
        # ./st2common/validators/workflow (unused since #5011)
    ],
    # commands helpful in inspecting the dependencies (the "=(...)" is zsh syntax)
    #   python files under st2common that will not be included in the wheel
    #     comm -13 =(pants dependencies --transitive st2common:st2common | grep -v -e : -e __init__.py | grep st2common/st2common | sort) =(find st2common/st2common -name '*.py' -and -not -name '__init__.py' | sort)
    #
    #   python files required by other wheels that are missing from st2common
    #     comm -13 =(pants dependencies --transitive st2common:st2common | grep st2common/st2common | sort) =(pants list --filter-target-type=python_distribution --filter-address-regex=-st2common:st2common :: | xargs pants dependencies --transitive | grep st2common/st2common | sort)
)
