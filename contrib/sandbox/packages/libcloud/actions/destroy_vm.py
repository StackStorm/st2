from lib.actions import SingleVMAction

__all__ = [
    'DestroyVMAction'
]


class DestroyVMAction(SingleVMAction):
    description = 'Destroy a VM'

    def run(self, credentials, vm_id):
        driver = self._get_driver_for_credentials(credentials=credentials)
        node = self._get_node_for_id(node_id=vm_id, driver=driver)

        self.logger('Destroying node: %s...' % (node))
        status = driver.destroy_node(node=node)

        if status is True:
            self.logger.info('Successfully destroyed node "%s"' % (node))
        else:
            self.logger.error('Failed to destroy node "%s"' % (node))

        return status
