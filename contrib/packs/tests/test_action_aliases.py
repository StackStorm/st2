from st2tests.base import BaseActionAliasTestCase


class DeployActionAliasTestCase(BaseActionAliasTestCase):
    alias_name = 'deploy_pack'

    def test_deploy_alias(self):
        # Includes packs
        format_string_1 = self.action_alias_db.formats[0]['representation'][0]

        # String with branch
        command = 'pack deploy StackStorm/st2contrib branch master'
        command = 'pack deploy StackStorm/st2contrib branch ma_branch'

        format_string_2 = self.action_alias_db.formats[0]['representation'][1]

        # Doesnt include packs
        format_string_1 = self.action_alias_db.formats[1]['representation'][0]
        format_string_2 = self.action_alias_db.formats[1]['representation'][1]
        print format_string_1
        pass
