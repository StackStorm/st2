import uuid
import datetime

import pecan
from pecan import rest
from oslo.config import cfg
from six.moves import http_client

from st2common.models.base import jsexpose
from st2common.models.api.access import TokenAPI, UserAPI
from st2common.persistence.access import Token, User
from st2common import log as logging


LOG = logging.getLogger(__name__)


class TokenController(rest.RestController):

    @jsexpose(body=TokenAPI, status_code=http_client.CREATED)
    def post(self, request=None):

        if not pecan.request.remote_user:
            LOG.audit('Access denied to anonymous user.')
            pecan.abort(http_client.UNAUTHORIZED)

        username = pecan.request.remote_user
        if username:
            try:
                User.get_by_name(username)
            except:
                user = UserAPI(name=username)
                User.add_or_update(UserAPI.to_model(user))
                LOG.audit('Registered new user "%s".' % username)
            LOG.audit('Access granted to user "%s".' % username)

        token = uuid.uuid4().hex
        ttl = (request.ttl
               if request and hasattr(request, 'ttl') and request.ttl < cfg.CONF.auth.token_ttl
               else cfg.CONF.auth.token_ttl)
        expiry = datetime.datetime.now() + datetime.timedelta(seconds=ttl)
        token = TokenAPI(user=username, token=token, expiry=expiry)
        Token.add_or_update(TokenAPI.to_model(token))
        LOG.audit('Access granted to %s with the token set to expire at "%s".' %
                  ('user "%s"' % username if username else "an anonymous user", str(expiry)))

        return token
