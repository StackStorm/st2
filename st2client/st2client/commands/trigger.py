from st2client.models import Trigger
from st2client.commands import resource


class TriggerBranch(resource.ResourceBranch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(TriggerBranch, self).__init__(
            Trigger, description, app, subparsers,
            parent_parser=parent_parser,
            commands={
                'list': TriggerListCommand,
                'get': TriggerGetCommand,
                'update': TriggerUpdateCommand,
                'delete': TriggerDeleteCommand
            })


class TriggerListCommand(resource.ContentPackResourceListCommand):
    display_attributes = ['ref', 'pack', 'name', 'description']


class TriggerGetCommand(resource.ContentPackResourceGetCommand):
    display_attributes = ['all']
    attribute_display_order = ['id', 'ref', 'pack', 'name', 'description',
                               'parameters_schema', 'payload_schema']


class TriggerUpdateCommand(resource.ContentPackResourceUpdateCommand):
    pass


class TriggerDeleteCommand(resource.ContentPackResourceDeleteCommand):
    pass
