from oslo.config import cfg
from st2common.persistence import Access
from st2common.models.db.action import (runnertype_access, action_access, actionexec_access)
from st2common import transport


class RunnerType(Access):
    impl = runnertype_access

    @classmethod
    def _get_impl(kls):
        return kls.impl


class Action(Access):
    impl = action_access

    @classmethod
    def _get_impl(kls):
        return kls.impl


class ActionExecution(Access):
    impl = actionexec_access
    publisher = None

    @classmethod
    def _get_impl(kls):
        return kls.impl

    @classmethod
    def _get_publisher(kls):
        if not kls.publisher:
            kls.publisher = transport.actionexecution.ActionExecutionPublisher(
                cfg.CONF.messaging.url)
        return kls.publisher
