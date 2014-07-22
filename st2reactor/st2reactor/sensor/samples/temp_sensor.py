from pecan.rest import RestController
import wsmeext.pecan as wsme_pecan
from wsme import types as wstypes

from st2reactor.sensor.base import Sensor


'''
Dectorators for request validations.
'''


class SensorHook(RestController):
    name = 'temp'

    @wsme_pecan.wsexpose(str, wstypes.text)
    def get_one(self, arg):
        return str(self.container_service)


class St2WebhookSensor(Sensor):
    '''
    A webhook sensor using a micro-framework Flask.
    '''

    webhook = SensorHook

    def setup(self):
        print('setup')

    def start(self):
        print('start')

    def stop(self):
        print('stop')

    def get_trigger_types(self):
        return []
