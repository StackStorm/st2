import logging

from st2client import models


LOG = logging.getLogger(__name__)


class Trigger(models.Resource):
    _plural = 'Triggers'


class Rule(models.Resource):
    _plural = 'Rules'
