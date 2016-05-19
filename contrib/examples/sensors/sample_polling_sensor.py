from st2reactor.sensor.base import PollingSensor


class SamplePollingSensor(PollingSensor):
    """
    * self.sensor_service
        - provides utilities like
            get_logger() for writing to logs.
            dispatch() for dispatching triggers into the system.
    * self._config
        - contains configuration that was specified as
          config.yaml in the pack.
    * self._poll_interval
        - indicates the interval between two successive poll() calls.
    """

    def setup(self):
        # Setup stuff goes here. For example, you might establish connections
        # to external system once and reuse it. This is called only once by the system.
        pass

    def poll(self):
        # This is where the crux of the sensor work goes.
        # This is called every self._poll_interval.
        # For example, let's assume you want to query ec2 and get
        # health information about your instances:
        #   some_data = aws_client.get('')
        #   payload = self._to_payload(some_data)
        #   # _to_triggers is something you'd write to convert the data format you have
        #   # into a standard python dictionary. This should follow the payload schema
        #   # registered for the trigger.
        #   self.sensor_service.dispatch(trigger, payload)
        #   # You can refer to the trigger as dict
        #   # { "name": ${trigger_name}, "pack": ${trigger_pack} }
        #   # or just simply by reference as string.
        #   # i.e. dispatch(${trigger_pack}.${trigger_name}, payload)
        #   # E.g.: dispatch('examples.foo_sensor', {'k1': 'stuff', 'k2': 'foo'})
        #   # trace_tag is a tag you would like to associate with the dispacthed TriggerInstance
        #   # Typically the trace_tag is unique and a reference to an external event.
        pass

    def cleanup(self):
        # This is called when the st2 system goes down. You can perform cleanup operations like
        # closing the connections to external system here.
        pass

    def add_trigger(self, trigger):
        # This method is called when trigger is created
        pass

    def update_trigger(self, trigger):
        # This method is called when trigger is updated
        pass

    def remove_trigger(self, trigger):
        # This method is called when trigger is deleted
        pass
