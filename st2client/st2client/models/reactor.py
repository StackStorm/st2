import logging

from st2client.models import core


LOG = logging.getLogger(__name__)


class Trigger(core.Resource):
    _plural = 'Triggers'


class Rule(core.Resource):
    _plural = 'Rules'
