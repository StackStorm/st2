import yaml

from st2tests.base import BaseActionTestCase

from check_auto_deploy_repo import CheckAutoDeployRepo

__all__ = [
    'CheckAutoDeployRepoActionTestCase'
]

MOCK_DATA_1 = { "deployment_branch": "master", "notify_channel": "community" }

MOCK_CONFIG_BLANK = ""

MOCK_CONFIG_BLANK_REPOSITORIES = "repositories:"

MOCK_CONFIG_FULL= """
repositories:
  st2contrib:
    repo: "https://github.com/StackStorm/st2contrib.git"
    subtree: true
    auto_deployment:
      branch: "master"
      notify_channel: "community"

  st2incubator:
    repo: "https://github.com/StackStorm/st2incubator.git"
    subtree: true
    auto_deployment:
      branch: "master"
      notify_channel: "community"
"""

class CheckAutoDeployRepoActionTestCase(BaseActionTestCase):
    action_cls = CheckAutoDeployRepo

    def test_run_config_blank(self):
        config = yaml.safe_load(MOCK_CONFIG_BLANK)
        action = self.get_action_instance(config=config)

        self.assertRaises(Exception, action.run,
                          branch="refs/heads/master", repo_name="st2contrib")

    def test_run_repositories_blank(self):
        config = yaml.safe_load(MOCK_CONFIG_BLANK_REPOSITORIES)
        action = self.get_action_instance(config=config)

        self.assertRaises(Exception, action.run,
                          branch="refs/heads/master", repo_name="st2contrib")

    def test_run_st2contrib_no_auto_deloy(self):
        config = yaml.safe_load(MOCK_CONFIG_FULL)
        action = self.get_action_instance(config=config)

        self.assertRaises(Exception, action.run,
                          branch="refs/heads/dev", repo_name="st2contrib")

    def test_run_st2contrib_auto_deloy(self):
        config = yaml.safe_load(MOCK_CONFIG_FULL)
        action = self.get_action_instance(config=config)

        expected = {'deployment_branch': 'master', 'notify_channel': 'community'}

        result = action.run(branch="refs/heads/master", repo_name="st2contrib")
        self.assertEqual(result, expected)


    def test_run_st2incubator_no_auto_deloy(self):
        config = yaml.safe_load(MOCK_CONFIG_FULL)
        action = CheckAutoDeployRepo(config)

        self.assertRaises(Exception, action.run,
                          branch="refs/heads/dev", repo_name="st2incubator")

    def test_run_st2incubator_auto_deloy(self):
        config = yaml.safe_load(MOCK_CONFIG_FULL)
        action = self.get_action_instance(config=config)

        expected = {'deployment_branch': 'master', 'notify_channel': 'community'}

        result = action.run(branch="refs/heads/master", repo_name="st2incubator")
        self.assertEqual(result, expected)
