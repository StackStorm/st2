from wsme import types as wtypes

from mirantas.resource import Resource

class StackStormBase(Resource):
    id = wtypes.text
    name = wtypes.text

