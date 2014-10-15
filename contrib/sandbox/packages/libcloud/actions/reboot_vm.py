from lib.actions import SingleVMAction

__all__ = [
    'RebootVMAction'
]


class RebootVMAction(SingleVMAction):
    description = 'Reboot a VM'

    def run(self, credentials, vm_id):
        driver = self._get_driver_for_credentials(credentials=credentials)
        node = self._get_node_for_id(node_id=vm_id, driver=driver)

        self.logger.info('Rebooting node: %s' % (node))
        status = driver.reboot_node(node=node)

        if status is True:
            self.logger.info('Successfully rebooted node "%s"' % (node))
        else:
            self.logger.error('Failed to reboot node "%s"' % (node))

        return status
