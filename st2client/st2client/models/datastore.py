import logging

from st2client import models


LOG = logging.getLogger(__name__)


class KeyValuePair(models.Resource):
    _alias = 'Key'
    _display_name = 'Key Value Pair'
    _plural = 'Keys'
    _plural_display_name = 'Key Value Pairs'
