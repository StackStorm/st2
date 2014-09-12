import mongoengine as me
from st2common.models.db import stormbase


class UserDB(stormbase.StormFoundationDB):
    name = me.StringField(required=True, unique=True)


class TokenDB(stormbase.StormFoundationDB):
    user = me.StringField(required=True)
    token = me.StringField(required=True, unique=True)
    expiry = me.DateTimeField()
