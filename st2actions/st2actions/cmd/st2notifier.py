import eventlet
import os
import sys

from st2common import log as logging
from st2common.service_setup import setup as common_setup
from st2common.service_setup import teardown as common_teardown
from st2actions.notifier import config
from st2actions.notifier import notifier
from st2actions.notifier import scheduler


LOG = logging.getLogger(__name__)


eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if '--use-debugger' in sys.argv else True,
    time=True)


def _setup():
    common_setup(service='notifier', config=config, setup_db=True, register_mq_exchanges=True,
                 register_signal_handlers=True)


def _run_worker():
    LOG.info('(PID=%s) Actions notifier started.', os.getpid())
    actions_notifier = notifier.get_notifier()
    actions_rescheduler = scheduler.get_rescheduler()
    try:
        eventlet.spawn(actions_rescheduler.start)
        actions_notifier.start(wait=True)
    except (KeyboardInterrupt, SystemExit):
        LOG.info('(PID=%s) Actions notifier stopped.', os.getpid())
        actions_rescheduler.shutdown()
        actions_notifier.shutdown()
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
