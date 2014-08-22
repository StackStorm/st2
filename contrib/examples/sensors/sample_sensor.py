class SimpleSensor(object):
    def __init__(self, container_service):
        self._container_service = container_service
        # container_service provides utilities like
        # get_logger() for writing to logs.
        # dispatch() for dispatching triggers into the system.

    def setup(self):
        # Setup stuff goes here. For example, you might establish connections
        # to external system once and reuse it. This is called only once by the system.
        pass

    def start(self):
        # This is where the crux of the sensor work goes.
        # This is called once by the system. If you want to sleep for regular intervals and keep
        # interacting with your external system, you'd do so here explicitly.
        # For example,
        # while True:
        #   time.sleep(30)
        #   some_data = aws_client.get('')
        #   triggers = self._to_triggers(some_data)
        #   # _to_triggers is something you'd write to convert the data format you have
        #   # into something stanley would understand.
        #   self._container_service.dispatch(triggers)
        pass

    def stop(self):
        # This is called when the stanley system goes down. You can perform cleanup operations like
        # closing the connections to external system here.
        pass

    def get_trigger_types(self):
        # You'd define the name of the trigger to use and the payload schema that your triggers
        # would resemble in this section. Trigger name is how rules would be selected to be applied.
        # Payload fields are the ones on which you'd write criteria on.
        # Note you can register multiple trigger types.
        return [{
            'name': 'st2.foo.sensor',
            'payload_schema': {
                'type': 'object',
                'properties': {
                    'k1': {
                        'type': 'string'
                    },
                    'k2': {
                        'enum': ['foo', 'bar', 'baz']
                    }
                },
                'required': ['k1', 'k2'],
                'additionalProperties': False
            }
        }]

    # Methods required for programmable sensors.
    def add_trigger(self, trigger):
        pass

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        pass
