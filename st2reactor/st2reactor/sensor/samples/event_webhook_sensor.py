from st2reactor.sensor.samples.st2_webhook_sensor import St2WebhookSensor

class EventWebhookSensor(St2WebhookSensor):

    def __init__(self, container_service):
        super(EventWebhookSensor, self).__init__(container_service)
        self._port = 6886

    def get_trigger_types(self):
        return [{'name': 'st2.event',
                 'description': 'Sample Event Sensor',
                 'payload_info': [
                    'host',
                    'event_id',
                    'timestamp']
                }]

    def _setup_flask_app(self):
        self._app.add_url_rule('/webhooks/events',
                               'event_webhooks',
                               self._handle_webhook,
                               methods=['POST'])
