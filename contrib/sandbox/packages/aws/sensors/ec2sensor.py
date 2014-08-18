import time

import boto.ec2

from st2reactor.container.containerservice import ContainerService
from st2client.client import Client

interval = 20

st2_endpoints = {
    'action': 'http://localhost:9101',
    'reactor': 'http://localhost:9102',
    'datastore': 'http://localhost:9103'
}


class EC2InstanceStatusSensor(object):
    def __init__(self, container_service):
        self._container_service = container_service
        self._log = self._container_service.get_logger(self.__class__.__name__)
        self.ec2 = EC2Client()

    def setup(self):
        self.ec2.connect('us-west-2')
        pass

    def start(self):
        while True:
            data = self.ec2.get_instance_details()
            for i in data:
                trigger = {}
                trigger['name'] = 'st2.ec2.instance_status'

                payload = data[i]
                payload['event_id'] = 'ec2-instance-check-' + str(int(time.time()))
                payload['instance_id'] = i
                try:
                    self._container_service.dispatch(trigger, payload)
                except Exception as e:
                    self._log.exception('Exception %s handling st2.ec2.instance_status', e)
            time.sleep(interval)

    def stop(self):
        pass

    def get_trigger_types(self):
        return [
            {
                'name': 'st2.ec2.instance_status',
                'description': 'EC2 Instance Status Sensor',
                'payload_info': [
                    'instance_id', 'instance_type', 'launch_time', 'tags', 'image_id',
                    'ip_address', 'state', 'state_code'
                ]
            }
        ]

    def add_trigger(self, trigger):
        pass

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        pass


class EC2VolumeStatusSensor(object):
    def __init__(self, container_service):
        self._container_service = container_service
        self._log = self._container_service.get_logger(self.__class__.__name__)
        self.ec2 = EC2Client()

    def setup(self):
        self.ec2.connect('us-west-2')

    def start(self):
        while True:
            data = self.ec2.get_volume_details()
            for i in data:
                trigger = {}
                trigger['name'] = 'st2.ec2.volume_status'

                payload = data[i]
                payload['event_id'] = 'ec2-volume-status-check-' + str(int(time.time()))
                payload['volume_id'] = i
                try:
                    self._container_service.dispatch(trigger, payload)
                except Exception as e:
                    self._log.exception('Exception %s handling st2.ec2.instance_status', e)

            time.sleep(interval)

    def stop(self):
        pass

    def get_trigger_types(self):
        return [
            {
                'name': 'st2.ec2.volume_status',
                'description': 'EC2 Volume Status Sensor',
                'payload_info': [
                    'volume_id', 'create_time', 'region', 'size', 'status', 'tags',
                    'type', 'attach_time', 'device_map', 'instance_id'
                ]
            }
        ]

    def add_trigger(self, trigger):
        pass

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        pass


class EC2Client(object):
    def __init__(self):
        try:
            client = Client(st2_endpoints)
            aws_key_id = client.keys.get_by_name('aws_access_key_id')
            if not aws_key_id:
                raise Exception('Key error with aws_access_key_id.')
            aws_secret_key = client.keys.get_by_name('aws_secret_access_key')
            if not aws_secret_key:
                raise Exception('Key error with aws_secret_access_key.')
            self._access_key_id = aws_key_id.value
            self._secret_access_key = aws_secret_key.value
            self._conn = None
        except Exception as e:
            print(e)

    def connect(self, region):
        try:
            self._conn = boto.ec2.connect_to_region(region,
                                                    aws_access_key_id=self._access_key_id,
                                                    aws_secret_access_key=self._secret_access_key)
        except Exception as e:
            print("Exception connecting to EC2 region: %s: %s" % (region, e))

    def get_instance_details(self):
        payload = {}
        try:
            instances = self._conn.get_only_instances()
            for i in instances:
                instance_payload = {}
                instance_payload['instance_type'] = i.instance_type
                instance_payload['launch_time'] = i.launch_time
                instance_payload['tags'] = i.tags
                instance_payload['image_id'] = i.image_id
                instance_payload['ip_address'] = i.ip_address
                instance_payload['state'] = i.state
                instance_payload['state_code'] = i.state_code
                payload[i.id] = instance_payload
        except Exception as e:
            print("Exception %s" % e)
        return payload

    def get_volume_details(self):
        payload = {}
        try:
            volumes = self._conn.get_all_volumes()
            for v in volumes:
                v_payload = {}
                v_payload['create_time'] = v.create_time
                v_payload['region'] = v.region.name
                v_payload['size'] = v.size
                v_payload['status'] = v.status
                v_payload['tags'] = v.tags
                v_payload['type'] = v.type
                v_payload['attach_time'] = v.attach_data.attach_time
                v_payload['device_map'] = v.attach_data.device
                v_payload['instance_id'] = v.attach_data.instance_id
                payload[v.id] = v_payload
        except Exception as e:
            print("Exception %s" % e)
        return payload

if __name__ == '__main__':
    cs = ContainerService()
    sensor = EC2InstanceStatusSensor(cs)
    sensor.setup()
    sensor.start()
