try:
    import simplejson as json
except:
    import json

from st2actions.runners import ActionRunner


def get_runner():
    return TestRunner()


class TestRunner(ActionRunner):
    def __init__(self):
        self.pre_run_called = False
        self.run_called = False
        self.post_run_called = False

    def pre_run(self):
        self.pre_run_called = True

    def run(self, action_params):
        self.run_called = True
        result = {
            'ran': True,
            'action_params': action_params
        }
        self.container_service.report_result(json.dumps(result))
        self.container_service.report_status(0)

    def post_run(self):
        self.post_run_called = True
