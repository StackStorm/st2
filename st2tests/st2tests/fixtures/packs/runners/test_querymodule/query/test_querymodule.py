from st2common.query.base import Querier
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED


class TestQuerier(Querier):
    def __init__(self, *args, **kwargs):
        super(TestQuerier, self).__init__(*args, **kwargs)

    def query(self, execution_id, query_context, last_query_time=None):
        return (LIVEACTION_STATUS_SUCCEEDED, {'called_with': {execution_id: query_context}})


def get_instance():
    return TestQuerier(empty_q_sleep_time=0.2,
                       no_workers_sleep_time=0.1)
