from oslo.config import cfg
from st2common.util import isotime
from st2common.models.base import BaseAPI
from st2common.models.db.access import UserDB, TokenDB
from st2common import log as logging


LOG = logging.getLogger(__name__)


def get_system_username():
    return cfg.CONF.system_user.user


class UserAPI(BaseAPI):
    model = UserDB
    schema = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "title": "User",
        "type": "object",
        "properties": {
            "name": {
                "type": "string"
            }
        },
        "required": ["name"],
        "additionalProperties": False
    }


class TokenAPI(BaseAPI):
    model = TokenDB
    schema = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "title": "Token",
        "type": "object",
        "properties": {
            "id": {
                "type": "string"
            },
            "user": {
                "type": ["string", "null"]
            },
            "token": {
                "type": ["string", "null"]
            },
            "ttl": {
                "type": "integer",
                "minimum": 1
            },
            "expiry": {
                "type": ["string", "null"],
                "pattern": isotime.ISO8601_UTC_REGEX
            }
        },
        "additionalProperties": False
    }

    @classmethod
    def from_model(cls, model):
        doc = super(cls, cls)._from_model(model)
        doc['expiry'] = isotime.format(model.expiry, offset=False) if model.expiry else None
        return cls(**doc)

    @classmethod
    def to_model(cls, token):
        model = super(cls, cls).to_model(token)
        model.user = str(token.user) if token.user else None
        model.token = str(token.token) if token.token else None
        model.ttl = getattr(token, 'ttl', None)
        model.expiry = isotime.parse(token.expiry) if token.expiry else None
        return model
