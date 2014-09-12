import mongoengine as me
from st2common.models.db import stormbase


class UserDB(stormbase.StormFoundationDB):
    name = me.StringField(required=True, unique=True)
    active = me.BooleanField(required=True, default=True)


class TokenDB(stormbase.StormFoundationDB):
    user = me.StringField(required=True)
    token = me.StringField(required=True, unique=True)
    expiry = me.DateTimeField()
    active = me.BooleanField(required=True, default=True)
