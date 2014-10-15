from lib.actions import BaseAction

__all__ = [
    'ImportPublicSSHKeyAction'
]


class ImportPublicSSHKeyAction(BaseAction):
    description = 'Import public SSH key'

    def run(self, credentials, name, key_material):
        driver = self._get_driver_for_credentials(credentials=credentials)
        return driver.import_key_pair_from_string(name=name,
                                                  key_material=key_material)
