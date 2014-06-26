import os, time, json
import boto.ec2
from st2reactor.container.containerservice import ContainerService

import logging

interval = 20

class EC2InstanceStatusSensor(object):
    __container_service = None
    __log = None
    ec2 = None

    def __init__(self, container_service):
        self.__container_service = container_service
        self.__log = self.__container_service.get_logger(self.__class__.__name__)
        self.ec2 = EC2Sensor('config.json')

    def setup(self):
        self.ec2.connect('us-west-2')
        pass

    def start(self):
        while True:
          triggers = []
          data = self.ec2.getInstanceDetails()
          for i in data:
            trigger = {}
            trigger['name'] = 'st2.ec2.instance_status'
            trigger['event_id'] = time.time()
            trigger['payload'] = data[i]
            trigger['payload']['instance_id'] = i
            triggers.append(trigger)
          try:
            self.__container_service.dispatch(triggers)
          except Exception, e:
            self.__log.error('Exception %s handling st2.ec2.instance_status', e)
          time.sleep(interval)

    def stop(self):
        pass

    def get_trigger_types(self):
        return [
            {'name': 'st2.ec2.instance_status', 'description': 'EC2 Instance Status Sensor', 'payload_info': ['instance_id', 'instance_type', 'launch_time', 'tags', 'image_id', 'ip_address', 'state', 'state_code']}
        ]

class EC2VolumeStatusSensor(object):
    __container_service = None
    __log = None
    ec2 = None

    def __init__(self, container_service):
        self.__container_service = container_service
        self.__log = self.__container_service.get_logger(self.__class__.__name__)
        self.ec2 = EC2Sensor('config.json')

    def setup(self):
        self.ec2.connect('us-west-2')
        pass

    def start(self):
        while True:
          triggers = []
          data = self.ec2.getVolumeDetails()
          for i in data:
            trigger = {}
            trigger['name'] = 'st2.ec2.volume_status'
            trigger['event_id'] = time.time()
            trigger['payload'] = data[i]
            trigger['payload']['volume_id'] = i
            triggers.append(trigger)
          try:
            self.__container_service.dispatch(triggers)
          except Exception, e:
            self.__log.error('Exception %s handling st2.ec2.instance_status', e)

          time.sleep(interval)

    def stop(self):
        pass

    def get_trigger_types(self):
        return [
            {'name': 'st2.ec2.volume_status', 'description': 'EC2 Volume Status Sensor', 'payload_info': ['volume_id', 'create_time', 'region', 'size', 'status', 'tags', 'type', 'attach_time', 'device_map', 'instance_id']}
        ]


class EC2Sensor(object):

    __access_key_id = None
    __secret_Access_key = None
    __conn = None

    def __init__(self,config):
        try:
          config_json=open(config)
          config=json.load(config_json)
          config_json.close() 

          self.__access_key_id=config['aws']['access_key_id']
          self.__secret_access_key=config['aws']['secret_access_key']
        except Exception, e:
          print "Config error with %s: %s" % (config, e)

    def connect(self,region):
        try:
          self.__conn = boto.ec2.connect_to_region(region,
           aws_access_key_id=self.__access_key_id,
           aws_secret_access_key=self.__secret_access_key)
        except Exception, e:
          print "Error connecting to EC2 region: %s" % region

    def getInstanceDetails(self):
        payload = {}
        try:
          instances = self.__conn.get_only_instances()
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
        except Exception, e:
           print "Exception %s" % e
        return payload

    def getVolumeDetails(self):
        payload = {}
        try:
          volumes = self.__conn.get_all_volumes()
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
        except Exception, e:
          print "Exception %s" %e
        return payload

if __name__ == '__main__':
  cs = ContainerService()
  sensor = EC2InstanceStatusSensor(cs)
  sensor.setup()
  sensor.start()
