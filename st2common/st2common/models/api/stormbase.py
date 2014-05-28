from wsme import types as wstypes

from mirantis.resource import Resource


class BaseAPI(Resource):
    # TODO: Does URI need a custom type?
    uri = wstypes.text
    name = wstypes.text
    description = wstypes.text
    id = wstypes.text

    @staticmethod
    def from_model(cls, model):
        instance = cls()
        instance.uri = model.uri
        instance.name = model.name
        instance.description = model.description
        instance.id = str(model.id)
        return instance

