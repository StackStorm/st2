import mongoengine as me
from st2common.models.db import MongoDBAccess
from st2common.models.db import stormbase


class KeyValuePairDB(stormbase.StormBaseDB):
    """
    Attribute:
        name: Name of the key.
        value: Arbitrary value to be stored.
    """
    value = me.StringField()


# specialized access objects
keyvaluepair_access = MongoDBAccess(KeyValuePairDB)
