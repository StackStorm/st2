from __future__ import absolute_import
import os
import sys

from st2common import log as logging
from st2common.service_setup import setup as common_setup
from st2common.service_setup import teardown as common_teardown
from st2common.util.monkey_patch import monkey_patch
from st2actions.resultstracker import config
from st2actions.resultstracker import resultstracker

__all__ = [
    'main'
]


monkey_patch()

LOG = logging.getLogger(__name__)


def _setup():
    common_setup(service='resultstracker', config=config, setup_db=True,
                 register_mq_exchanges=True, register_signal_handlers=True)


def _run_worker():
    LOG.info('(PID=%s) Results tracker started.', os.getpid())
    tracker = resultstracker.get_tracker()
    try:
        tracker.start(wait=True)
    except (KeyboardInterrupt, SystemExit):
        LOG.info('(PID=%s) Results tracker stopped.', os.getpid())
        tracker.shutdown()
    except:
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
        LOG.exception('(PID=%s) Results tracker quit due to exception.', os.getpid())
        return 1
    finally:
        _teardown()
