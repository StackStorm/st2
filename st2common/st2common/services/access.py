import uuid
import datetime

from oslo.config import cfg

from st2common.models.api.access import TokenAPI, UserAPI
from st2common.persistence.access import Token, User
from st2common import log as logging


LOG = logging.getLogger(__name__)


def create_token(username, ttl=None):
    if not ttl or ttl > cfg.CONF.auth.token_ttl:
        ttl = cfg.CONF.auth.token_ttl
    if username:
        try:
            User.get_by_name(username)
        except:
            user = UserAPI(name=username)
            User.add_or_update(UserAPI.to_model(user))
            LOG.audit('Registered new user "%s".' % username)
        LOG.audit('Access granted to user "%s".' % username)

    token = uuid.uuid4().hex
    expiry = datetime.datetime.utcnow() + datetime.timedelta(seconds=ttl)
    token = TokenAPI(user=username, token=token, expiry=expiry)
    Token.add_or_update(TokenAPI.to_model(token))
    LOG.audit('Access granted to %s with the token set to expire at "%s".' %
              ('user "%s"' % username if username else "an anonymous user", str(expiry)))
    return token


def delete_token(token):
    token_db = Token.get(token)
    return Token.delete(token_db)
