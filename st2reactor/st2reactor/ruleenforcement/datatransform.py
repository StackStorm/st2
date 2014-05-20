class Jinja2BasedTransformer(object):
    def __init__(self, payload):
        self.__payload = payload

    def __call__(self, transformation):
        return transformation


def get_transformer(payload):
    return Jinja2BasedTransformer(payload)