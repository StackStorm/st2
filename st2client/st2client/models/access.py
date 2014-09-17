import logging

from st2client.models import core


LOG = logging.getLogger(__name__)


class Token(core.Resource):
    _display_name = 'Access Token'
    _plural = 'Tokens'
    _plural_display_name = 'Access Tokens'
