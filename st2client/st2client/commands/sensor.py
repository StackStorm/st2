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


class SensorListCommand(resource.ResourceListCommand):
    display_attributes = ['id', 'content_pack', 'name', 'description']


class SensorGetCommand(resource.ContentPackResourceGetCommand):
    display_attributes = ['all']
