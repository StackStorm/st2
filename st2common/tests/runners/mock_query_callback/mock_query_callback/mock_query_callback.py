from __future__ import absolute_import

from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.runners.base import ActionRunner
from st2common.runners.base import get_metadata as get_runner_metadata


__all__ = [
    'MockQueryCallbackRunner',

    'get_runner',
    'get_metadata'
]

class MockQueryCallbackRunner(ActionRunner):
    """
    Runner which does absolutely nothing. No-op action.
    """

    def __init__(self, runner_id):
        super(MockQueryCallbackRunner, self).__init__(runner_id=runner_id)

    def pre_run(self):
        super(MockQueryCallbackRunner, self).pre_run()

    def run(self, action_parameters):
        result = {
            'failed': False,
            'succeeded': True,
            'return_code': 0,
        }

        status = LIVEACTION_STATUS_SUCCEEDED
        return (status, result, None)


def get_runner():
    return MockQueryCallbackRunner(str(uuid.uuid4()))


def get_metadata():
    return get_runner_metadata('noop_runner')[0]


