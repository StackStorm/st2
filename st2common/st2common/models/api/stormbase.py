from wsme import types as wstypes

from mirantis.resource import Resource


class BaseAPI(Resource):
    # TODO: Does URI need a custom type?
    uri = wstypes.text
    name = wstypes.text
    description = wstypes.text
    id = wstypes.text

    @staticmethod
    def from_model(kls, model):
        api_instance = kls()
        api_instance.uri = model.uri
        api_instance.name = model.name
        api_instance.description = model.description
        api_instance.id = str(model.id)
        return api_instance

    @staticmethod
    def to_model(kls, api_instance):
        model = kls()
        model.name = api_instance.name
        model.description = api_instance.description
        return model
