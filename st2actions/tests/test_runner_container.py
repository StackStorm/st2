from st2common.models.db.action import RunnerTypeDB
from st2tests.base import DbTestCase
import tests.config as tests_config
tests_config.parse_args()

# XXX: There is dependency on config being setup before importing
# RunnerContainer. Do not move this until you fix config
# dependencies.
from st2actions.container.base import RunnerContainer


class RunnerContainerTest(DbTestCase):

    def test_get_runner_module(self):
        runner_type_db = RunnerTypeDB()
        runner_type_db.name = 'run-local'
        runner_type_db.runner_module = 'st2actions.runners.fabricrunner'
        runner_container = RunnerContainer()
        runner = runner_container._get_runner(runner_type_db)
        self.assertTrue(runner is not None, 'Runner must be valid.')
