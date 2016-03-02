import eventlet
import os
import sys

from oslo_config import cfg

from st2common import log as logging
from st2common.constants.scheduler import SCHEDULER_ENABLED_LOG_LINE, SCHEDULER_DISABLED_LOG_LINE
from st2common.service_setup import setup as common_setup
from st2common.service_setup import teardown as common_teardown
from st2common.util.monkey_patch import monkey_patch
from st2actions.notifier import config
from st2actions.notifier import notifier
from st2actions.notifier import scheduler

__all__ = [
    'main'
]

monkey_patch()

LOG = logging.getLogger(__name__)


def _setup():
    common_setup(service='notifier', config=config, setup_db=True, register_mq_exchanges=True,
                 register_signal_handlers=True)


def _run_worker():
    LOG.info('(PID=%s) Actions notifier started.', os.getpid())
    actions_notifier = notifier.get_notifier()
    actions_rescheduler = None
    try:
        if cfg.CONF.scheduler.enable:
            actions_rescheduler = scheduler.get_rescheduler()
            eventlet.spawn(actions_rescheduler.start)
            LOG.info(SCHEDULER_ENABLED_LOG_LINE)
        else:
            LOG.info(SCHEDULER_DISABLED_LOG_LINE)
        actions_notifier.start(wait=True)
    except (KeyboardInterrupt, SystemExit):
        LOG.info('(PID=%s) Actions notifier stopped.', os.getpid())
        if actions_rescheduler:
            actions_rescheduler.shutdown()
        actions_notifier.shutdown()
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
