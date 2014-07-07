import re
import json
import copy
import jinja2

from st2common.persistence.datastore import KeyValuePair
from st2common.models.db.datastore import KeyValuePairDB


PAYLOAD_PREFIX = 'trigger'
RULE_DATA_PREFIX = 'rule'
SYSTEM_PREFIX = 'system'


class Jinja2BasedTransformer(object):
    def __init__(self, payload):
        self._payload_context = Jinja2BasedTransformer._construct_payload_context(payload)

    def __call__(self, mapping, rule_data):
        context = self._construct_context(rule_data)
        context = self._construct_system_context(mapping, context)
        context = self._construct_system_context(context, context)
        context = self._render_context(context)
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

    def _construct_system_context(self, data, context):
        """Identify the system context in the data."""
        # The following regex will look for all occurrences of "{{system.*}}",
        # "{{ system.* }}", "{{ system.*}}", and "{{system.* }}" in the data.
        regex = '{{\s*' + SYSTEM_PREFIX + '.(.*?)\s*}}'
        keys = re.findall(regex, json.dumps(data))
        if not keys:
            return context
        kvps = {}
        for key in keys:
            kvp = KeyValuePair.get_by_name(key)
            kvps[key] = kvp.value
        if kvps and SYSTEM_PREFIX not in context:
            context[SYSTEM_PREFIX] = {}
        context[SYSTEM_PREFIX].update(kvps)
        return context

    def _render_context(self, context):
        """Self-render the context."""
        template = jinja2.Template(json.dumps(context))
        resolved_context = json.loads(template.render(context))
        return resolved_context

    @staticmethod
    def _construct_payload_context(payload):
        if payload is None:
            return {}
        return {PAYLOAD_PREFIX: payload}


def get_transformer(payload):
    return Jinja2BasedTransformer(payload)
