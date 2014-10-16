import re
import json
import copy
import jinja2

from st2common.models.api.reactor import RuleAPI
from st2common.persistence.datastore import KeyValuePair
import six


PAYLOAD_PREFIX = 'trigger'
RULE_PREFIX = 'rule'
SYSTEM_PREFIX = 'system'


class Jinja2BasedTransformer(object):
    def __init__(self, payload, rule=None):
        context = {}
        if rule:
            context['rule'] = vars(RuleAPI.from_model(rule))
        self._payload_context = self._construct_context(PAYLOAD_PREFIX, payload, context)

    def __call__(self, mapping):
        context = copy.copy(self._payload_context)
        context = self._construct_system_context(mapping, context)
        resolved_mapping = {}
        for mapping_k, mapping_v in six.iteritems(mapping):
            template = jinja2.Template(mapping_v)
            resolved_mapping[mapping_k] = template.render(context)
        return resolved_mapping

    def _construct_context(self, prefix, data, context):
        if data is None:
            return context
        context = self._construct_system_context(data, context)
        template = jinja2.Template(json.dumps(data))
        resolved_data = json.loads(template.render(context))
        if resolved_data:
            if prefix not in context:
                context[prefix] = {}
            context[prefix].update(resolved_data)
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
        if kvps:
            if SYSTEM_PREFIX not in context:
                context[SYSTEM_PREFIX] = {}
            context[SYSTEM_PREFIX].update(kvps)
        return context


def get_transformer(payload, rule=None):
    return Jinja2BasedTransformer(payload, rule)
