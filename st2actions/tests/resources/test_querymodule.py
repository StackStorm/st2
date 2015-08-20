from st2actions.query.base import Querier
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED


class TestQuerier(Querier):
    def __init__(self, *args, **kwargs):
        super(TestQuerier, self).__init__(*args, **kwargs)

    def query(self, execution_id, query_context):
        return (LIVEACTION_STATUS_SUCCEEDED, {'called_with': {execution_id: query_context}})


def get_instance():
    return TestQuerier(query_interval=0.1, empty_q_sleep_time=0.2,
                       no_workers_sleep_time=0.1)
