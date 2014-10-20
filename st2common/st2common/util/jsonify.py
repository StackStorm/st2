try:
    import simplejson as json
except ImportError:
    import json


from pecan.jsonify import GenericJSON


__all__ = [
    'json_encode',
]


def json_encode(obj, indent=4):
    return json.dumps(obj, cls=GenericJSON, indent=indent)
