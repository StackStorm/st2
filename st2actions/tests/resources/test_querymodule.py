from st2actions.query.base import Querier


class TestQuerier(Querier):
    def __init__(self, *args, **kwargs):
        super(TestQuerier, self).__init__(*args, **kwargs)

    def query(self, execution_id, query_context):
        return True, {'called_with': {execution_id: query_context}}
