import logging

from st2client.models import core


LOG = logging.getLogger(__name__)


class Sensor(core.Resource):
    _plural = 'Sensortypes'


class Trigger(core.Resource):
    _plural = 'Triggertypes'


class Rule(core.Resource):
    _plural = 'Rules'
