from st2client.models import Trigger
from st2client.commands import resource


class TriggerBranch(resource.ResourceBranch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(TriggerBranch, self).__init__(
            Trigger, description, app, subparsers,
            parent_parser=parent_parser,
            commands={
                'list': TriggerListCommand,
                'get': TriggerGetCommand
            })


class TriggerListCommand(resource.ContentPackResourceListCommand):
    display_attributes = ['ref', 'pack', 'name', 'description']


class TriggerGetCommand(resource.ContentPackResourceGetCommand):
    display_attributes = ['all']
