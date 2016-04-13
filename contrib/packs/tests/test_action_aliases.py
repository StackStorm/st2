from st2tests.base import BaseActionAliasTestCase


class DeployActionAliasTestCase(BaseActionAliasTestCase):
    action_alias_name = 'pack_deploy'

    def test_pack_deploy_alias(self):
        # Includes packs
        format_string = self.action_alias_db.formats[0]['representation'][0]

        # Command with branch
        command = 'pack deploy StackStorm/st2contrib packs libcloud,aws branch master'
        expected_parameters = {
            'repo_name': 'StackStorm/st2contrib',
            'packs': 'libcloud,aws',
            'branch': 'master'
        }
        self.assertExtractedParametersMatch(format_string=format_string,
                                            command=command,
                                            parameters=expected_parameters)

        command = 'pack deploy StackStorm/st2contrib packs libcloud branch ma_branch'
        expected_parameters = {
            'repo_name': 'StackStorm/st2contrib',
            'packs': 'libcloud',
            'branch': 'ma_branch'
        }
        self.assertExtractedParametersMatch(format_string=format_string,
                                            command=command,
                                            parameters=expected_parameters)

        # Command without branch
        format_string = self.action_alias_db.formats[0]['representation'][1]
        command = 'pack deploy StackStorm/st2contrib packs libcloud,aws'
        expected_parameters = {
            'repo_name': 'StackStorm/st2contrib',
            'packs': 'libcloud,aws'
        }
        self.assertExtractedParametersMatch(format_string=format_string,
                                            command=command,
                                            parameters=expected_parameters)

        command = 'pack deploy StackStorm/st2contrib packs libcloud'
        expected_parameters = {
            'repo_name': 'StackStorm/st2contrib',
            'packs': 'libcloud'
        }
        self.assertExtractedParametersMatch(format_string=format_string,
                                            command=command,
                                            parameters=expected_parameters)

        # Doesnt include packs
        format_string = self.action_alias_db.formats[1]['representation'][0]
        command = 'pack deploy StackStorm/st2contrib branch trunk'
        expected_parameters = {
            'repo_name': 'StackStorm/st2contrib',
            'branch': 'trunk'
        }
        self.assertExtractedParametersMatch(format_string=format_string,
                                            command=command,
                                            parameters=expected_parameters)

        format_string = self.action_alias_db.formats[1]['representation'][1]
        command = 'pack deploy StackStorm/st2contrib'
        expected_parameters = {
            'repo_name': 'StackStorm/st2contrib'
        }
        self.assertExtractedParametersMatch(format_string=format_string,
                                            command=command,
                                            parameters=expected_parameters)


class PackInfoActionAliasTestCase(BaseActionAliasTestCase):
    action_alias_name = 'pack_info'

    def test_pack_info_alias(self):
        format_string = self.action_alias_db.formats[0]
        command = 'pack info libcloud'
        expected_parameters = {
            'pack': 'libcloud'
        }
        self.assertExtractedParametersMatch(format_string=format_string,
                                            command=command,
                                            parameters=expected_parameters)

        command = 'pack info aws'
        expected_parameters = {
            'pack': 'aws'
        }
        self.assertExtractedParametersMatch(format_string=format_string,
                                            command=command,
                                            parameters=expected_parameters)


class ShowGitCloneActionAliasTestCase(BaseActionAliasTestCase):
    action_alias_name = 'show_git_clone'

    def test_show_git_cline(self):
        format_string = self.action_alias_db.formats[0]
        command = 'show git clone StackStorm/st2contrib'
        expected_parameters = {
            'repo_name': 'StackStorm/st2contrib'
        }
        self.assertExtractedParametersMatch(format_string=format_string,
                                            command=command,
                                            parameters=expected_parameters)
