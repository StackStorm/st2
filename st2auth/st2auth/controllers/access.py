import pecan

from pecan import rest
from six.moves import http_client

from st2common.models.base import jsexpose
from st2common.models.api.access import TokenAPI
from st2common.services.access import create_token
from st2common import log as logging


LOG = logging.getLogger(__name__)


class TokenController(rest.RestController):

    @jsexpose(body=TokenAPI, status_code=http_client.CREATED)
    def post(self, request, **kwargs):
        if not pecan.request.remote_user:
            LOG.audit('Access denied to anonymous user.')
            pecan.abort(http_client.UNAUTHORIZED)

        ttl = getattr(request, 'ttl', None)
        tokendb = create_token(pecan.request.remote_user, ttl)

        return TokenAPI.from_model(tokendb)
