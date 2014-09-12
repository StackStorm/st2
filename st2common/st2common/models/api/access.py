import datetime

from st2common.models.base import BaseAPI
from st2common.models.db.access import UserDB, TokenDB
from st2common import log as logging


LOG = logging.getLogger(__name__)


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
                "pattern": "^\d{4}-\d{2}-\d{2}[ ]\d{2}:\d{2}:\d{2}.\d{6}$"
            }
        },
        "additionalProperties": False
    }

    def __init__(self, **kw):
        expiry = kw.pop('expiry') if 'expiry' in kw else None
        super(TokenAPI, self).__init__(**kw)
        self.expiry = (datetime.datetime.strptime(expiry, '%Y-%m-%d %H:%M:%S.%f')
                       if expiry and not isinstance(expiry, datetime.datetime) else expiry)

    @classmethod
    def to_model(cls, token):
        model = super(cls, cls).to_model(token)
        model.user = str(token.user) if token.user else None
        model.token = str(token.token) if token.token else None
        model.ttl = getattr(token, 'ttl', None)
        model.expiry = token.expiry
        return model
