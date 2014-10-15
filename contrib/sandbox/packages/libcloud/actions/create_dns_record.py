from lib.actions import BaseAction

__all__ = [
    'CreateDNSRecordAction'
]


class CreateDNSRecordAction(BaseAction):
    description = 'Create new DNS record'

    def run(self, credentials, domain, name, type, data, ttl=500):
        driver = self._get_driver_for_credentials(credentials=credentials)
        zones = driver.list_zones()

        try:
            zone = [z for z in zones if z.domain == domain][0]
        except IndexError:
            raise ValueError('Zone with domain "%s" doesn\'t exist' % (domain))

        extra = {'ttl': int(ttl)}
        record = driver.create_record(name=name, zone=zone,
                                      type=type,
                                      data=data, extra=extra)

        self.logger.info('Successfully created record "%s"' % (record.name))
        return record
