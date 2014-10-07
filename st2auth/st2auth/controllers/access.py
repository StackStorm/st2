import pecan

from oslo.config import cfg
from pecan import rest
from six.moves import http_client

from st2common.models.base import jsexpose
from st2common.models.api.access import TokenAPI
from st2common.services.access import create_token
from st2common import log as logging


LOG = logging.getLogger(__name__)


class TokenController(rest.RestController):

    @jsexpose(body=TokenAPI, status_code=http_client.CREATED)
    def post(self, request=None):

        if not pecan.request.remote_user:
            LOG.audit('Access denied to anonymous user.')
            pecan.abort(http_client.UNAUTHORIZED)

        ttl = (request.ttl if request and hasattr(request, 'ttl') and
               request.ttl < cfg.CONF.auth.token_ttl else cfg.CONF.auth.token_ttl)

        return create_token(pecan.request.remote_user, ttl)
