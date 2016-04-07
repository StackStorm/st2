from st2tests.base import BaseActionAliasTestCase


class DeployActionAliasTestCase(BaseActionAliasTestCase):
    action_alias_name = 'deploy_pack'

    def test_deploy_alias(self):
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
                                            values=expected_parameters)

        command = 'pack deploy StackStorm/st2contrib packs libcloud branch ma_branch'
        expected_parameters = {
            'repo_name': 'StackStorm/st2contrib',
            'packs': 'libcloud',
            'branch': 'ma_branch'
        }
        self.assertExtractedParametersMatch(format_string=format_string,
                                            command=command,
                                            values=expected_parameters)

        # Command without branch
        format_string = self.action_alias_db.formats[0]['representation'][1]
        command = 'pack deploy StackStorm/st2contrib packs libcloud,aws'
        expected_parameters = {
            'repo_name': 'StackStorm/st2contrib',
            'packs': 'libcloud,aws'
        }
        self.assertExtractedParametersMatch(format_string=format_string,
                                            command=command,
                                            values=expected_parameters)

        command = 'pack deploy StackStorm/st2contrib packs libcloud'
        expected_parameters = {
            'repo_name': 'StackStorm/st2contrib',
            'packs': 'libcloud'
        }
        self.assertExtractedParametersMatch(format_string=format_string,
                                            command=command,
                                            values=expected_parameters)

        # Doesnt include packs
        format_string = self.action_alias_db.formats[1]['representation'][0]
        command = 'pack deploy StackStorm/st2contrib branch trunk'
        expected_parameters = {
            'repo_name': 'StackStorm/st2contrib',
            'branch': 'trunk'
        }
        self.assertExtractedParametersMatch(format_string=format_string,
                                            command=command,
                                            values=expected_parameters)

        format_string = self.action_alias_db.formats[1]['representation'][1]
        command = 'pack deploy StackStorm/st2contrib'
        expected_parameters = {
            'repo_name': 'StackStorm/st2contrib'
        }
        self.assertExtractedParametersMatch(format_string=format_string,
                                            command=command,
                                            values=expected_parameters)
