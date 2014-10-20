from st2client.models import Trigger
from st2client.commands import resource


class TriggerBranch(resource.ResourceBranch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(TriggerBranch, self).__init__(
            Trigger, description, app, subparsers,
            parent_parser=parent_parser,
            commands={
                'list': TriggerListCommand
            })


class TriggerListCommand(resource.ResourceListCommand):
    display_attributes = ['id', 'content_pack', 'name', 'description']
