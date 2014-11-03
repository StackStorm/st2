from st2client.models import Sensor
from st2client.commands import resource


class SensorBranch(resource.ResourceBranch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(SensorBranch, self).__init__(
            Sensor, description, app, subparsers,
            parent_parser=parent_parser,
            read_only=True,
            commands={
                'list': SensorListCommand,
                'get': SensorGetCommand
            })


class SensorListCommand(resource.ContentPackResourceListCommand):
    display_attributes = ['ref', 'pack', 'name', 'trigger_types']


class SensorGetCommand(resource.ContentPackResourceGetCommand):
    display_attributes = ['all']
    attribute_display_order = ['id', 'ref', 'pack', 'name', 'entry_point',
                               'artifact_uri', 'trigger_types']
