from wsme import types as wstypes

from mirantis.resource import Resource


def get_id(identifiable):
    if identifiable is None:
        return ''
    return str(identifiable.id)


def get_ref(identifiable):
    if identifiable is None:
        return {}
    return {'id': str(identifiable.id), 'name': identifiable.name}


def get_model_from_ref(db_api, ref):
    if ref is None:
        return None
    model_id = ref['id'] if 'id' in ref else None
    if model_id is not None:
        return db_api.get_by_id(model_id)
    model_name = ref['name'] if 'name' in ref else None
    for model in db_api.query(name=model_name):
        return model
    return None


class StormFoundationAPI(Resource):
    # TODO: Does URI need a custom type?
    uri = wstypes.text
    id = wstypes.text

    @staticmethod
    def from_model(kls, model):
        api_instance = kls()
        api_instance.id = str(model.id)
        api_instance.uri = model.uri
        return api_instance

    @staticmethod
    def to_model(kls, api_instance):
        model = kls()
        return model


class StormBaseAPI(StormFoundationAPI):
    name = wstypes.text
    description = wstypes.wsattr(wstypes.text, default='')

    @staticmethod
    def from_model(kls, model):
        api_instance = StormFoundationAPI.from_model(kls, model)
        api_instance.name = model.name
        api_instance.description = model.description
        return api_instance

    @staticmethod
    def to_model(kls, api_instance):
        model = StormFoundationAPI.to_model(kls, api_instance)
        model.name = api_instance.name
        model.description = api_instance.description
        return model
