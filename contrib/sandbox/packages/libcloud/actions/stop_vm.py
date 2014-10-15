from lib.actions import SingleVMAction

__all__ = [
    'StopVMAction'
]


class StopVMAction(SingleVMAction):
    description = 'Stop a VM'

    def run(self, credentials, vm_id):
        driver = self._get_driver_for_credentials(credentials=credentials)
        node = self._get_node_for_id(node_id=vm_id, driver=driver)

        self.logger.info('Stopping node: %s' % (node))
        status = driver.ex_stop_node(node=node)

        if status is True:
            self.logger.info('Successfully stopped node "%s"' % (node))
        else:
            self.logger.error('Failed to stop node "%s"' % (node))

        return status
