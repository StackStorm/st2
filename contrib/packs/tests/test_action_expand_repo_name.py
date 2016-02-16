import yaml

from st2tests.base import BaseActionTestCase

from expand_repo_name import ExpandRepoName

__all__ = [
    'ExpandRepoNameTestCase'
]

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

class ExpandRepoNameTestCase(BaseActionTestCase):
    def test_run_config_blank(self):
        config = yaml.safe_load(MOCK_CONFIG_BLANK)
        action = ExpandRepoName(config)

        self.assertRaises(Exception, action.run,
                          repo_name="st2contrib")

    def test_run_repositories_blank(self):
        config = yaml.safe_load(MOCK_CONFIG_BLANK_REPOSITORIES)
        action = ExpandRepoName(config)

        self.assertRaises(Exception, action.run,
                          repo_name="st2contrib")

    def test_run_st2contrib_expands(self):
        config = yaml.safe_load(MOCK_CONFIG_FULL)
        action = ExpandRepoName(config)

        expected = {'repo_url': 'https://github.com/StackStorm/st2contrib.git', 'subtree': True}

        result = action.run(repo_name="st2contrib")
        self.assertEqual(result, expected)

    def test_run_st2incubator_expands(self):
        config = yaml.safe_load(MOCK_CONFIG_FULL)
        action = ExpandRepoName(config)

        expected = {'repo_url': 'https://github.com/StackStorm/st2incubator.git', 'subtree': True}

        result = action.run(repo_name="st2incubator")
        self.assertEqual(result, expected)
