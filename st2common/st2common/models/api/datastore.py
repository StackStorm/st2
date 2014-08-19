from wsme import types as wstypes

from st2common.models.api.stormbase import StormBaseAPI
from st2common.models.db.datastore import KeyValuePairDB


class KeyValuePairAPI(StormBaseAPI):

    value = wstypes.text

    @classmethod
    def from_model(cls, model):
        kvp = StormBaseAPI.from_model(cls, model)
        kvp.value = model.value
        return kvp

    @classmethod
    def to_model(cls, kvp):
        model = StormBaseAPI.to_model(KeyValuePairDB, kvp)
        model.value = kvp.value
        return model
