import logging

from st2client.models import core


LOG = logging.getLogger(__name__)


class Sensor(core.Resource):
    _plural = 'Sensortypes'
    _repr_attributes = ['name', 'pack']


class Trigger(core.Resource):
    _plural = 'Triggertypes'
    _repr_attributes = ['name', 'pack']


class Rule(core.Resource):
    _plural = 'Rules'
