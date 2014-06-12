import copy
import jinja2

PAYLOAD_PREFIX = 'trigger'
RULE_DATA_PREFIX = 'rule'


class Jinja2BasedTransformer(object):
    def __init__(self, payload):
        self._payload_context = Jinja2BasedTransformer._construct_payload_context(payload)

    def __call__(self, mapping, rule_data):
        context = self._construct_context(rule_data)
        resolved_mapping = {}
        for mapping_k, mapping_v in mapping.iteritems():
            template = jinja2.Template(mapping_v)
            resolved_mapping[mapping_k] = template.render(context)
        return resolved_mapping

    def _construct_context(self, rule_data):
        context = copy.copy(self._payload_context)
        if rule_data is None:
            return context
        context[RULE_DATA_PREFIX] = rule_data
        return context

    @staticmethod
    def _construct_payload_context(payload):
        if payload is None:
            return {}
        return {PAYLOAD_PREFIX: payload}


def get_transformer(payload):
    return Jinja2BasedTransformer(payload)
