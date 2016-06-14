# Monkey patching should be done as early as possible.
# See http://eventlet.net/doc/patching.html#monkeypatching-the-standard-library
from st2common.util.monkey_patch import monkey_patch
monkey_patch()

import os
import signal
import sys

from st2actions import config
from st2actions import scheduler, worker
from st2common import log as logging
from st2common.service_setup import setup as common_setup
from st2common.service_setup import teardown as common_teardown

__all__ = [
    'main'
]

LOG = logging.getLogger(__name__)


def _setup_sigterm_handler():

        def sigterm_handler(signum=None, frame=None):
            # This will cause SystemExit to be throw and allow for component cleanup.
            sys.exit(0)

        # Register a SIGTERM signal handler which calls sys.exit which causes SystemExit to
        # be thrown. We catch SystemExit and handle cleanup there.
        signal.signal(signal.SIGTERM, sigterm_handler)


def _setup():
    common_setup(service='actionrunner', config=config, setup_db=True, register_mq_exchanges=True,
                 register_signal_handlers=True)
    _setup_sigterm_handler()


def _run_worker():
    LOG.info('(PID=%s) Worker started.', os.getpid())

    components = [
        scheduler.get_scheduler(),
        worker.get_worker()
    ]

    try:
        for component in components:
            component.start()

        for component in components:
            component.wait()
    except (KeyboardInterrupt, SystemExit):
        LOG.info('(PID=%s) Worker stopped.', os.getpid())

        errors = False

        for component in components:
            try:
                component.shutdown()
            except:
                LOG.exception('Unable to shutdown %s.', component.__class__.__name__)
                errors = True

        if errors:
            return 1
    except:
        LOG.exception('(PID=%s) Worker unexpectedly stopped.', os.getpid())
        return 1

    return 0


def _teardown():
    common_teardown()


def main():
    try:
        _setup()
        return _run_worker()
    except SystemExit as exit_code:
        sys.exit(exit_code)
    except:
        LOG.exception('(PID=%s) Worker quit due to exception.', os.getpid())
        return 1
    finally:
        _teardown()
