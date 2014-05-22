from wsme import types as wtypes

from mirantas.resource import Resource

class BaseAPI(Resource):
    # TODO: Does URI need a custom type?
    uri = wtypes.text
    name = wtypes.text
    description = wtypes.text
    id = wtypes.text

