from libcloud.dns.base import Record

from lib.actions import BaseAction

__all__ = [
    'DeleteDNSRecordAction'
]


class DeleteDNSRecordAction(BaseAction):
    description = 'Delete an existing DNS record'

    def run(self, credentials, record_id):
        driver = self._get_driver_for_credentials(credentials=credentials)
        record = Record(id=record_id, name=None, type=None, data=None,
                        zone=None, driver=driver)

        status = driver.delete_record(record=record)

        if status:
            self.logger.info('Successfully deleted record')
        else:
            self.logger.error('Failed to delete a record')

        return status
