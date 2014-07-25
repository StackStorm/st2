import logging

from st2client.models import core


LOG = logging.getLogger(__name__)


class KeyValuePair(core.Resource):
    _alias = 'Key'
    _display_name = 'Key Value Pair'
    _plural = 'Keys'
    _plural_display_name = 'Key Value Pairs'
