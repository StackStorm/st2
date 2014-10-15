from lib.actions import SingleVMAction

__all__ = [
    'StartVMAction'
]


class StartVMAction(SingleVMAction):
    description = 'Start a VM'

    def run(self, credentials, vm_id):
        driver = self._get_driver_for_credentials(credentials=credentials)
        node = self._get_node_for_id(node_id=vm_id, driver=driver)

        self.logger.info('Starting node: %s' % (node))
        status = driver.ex_stop_node(node=node)

        if status is True:
            self.logger.info('Successfully started node "%s"' % (node))
        else:
            self.logger.rror('Failed to start node "%s"' % (node))

        return status
