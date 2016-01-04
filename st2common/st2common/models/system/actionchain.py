# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import six
import string

from st2common.util import schema as util_schema
from st2common.models.api.notification import NotificationSubSchemaAPI


class Node(object):

    schema = {
        "title": "Node",
        "description": "Node of an ActionChain.",
        "type": "object",
        "properties": {
            "name": {
                "description": "The name of this node.",
                "type": "string",
                "required": True
            },
            "ref": {
                "type": "string",
                "description": "Ref of the action to be executed.",
                "required": True
            },
            "params": {
                "type": "object",
                "description": ("Parameter for the execution (old name, here for backward "
                                "compatibility reasons)."),
                "default": {}
            },
            "parameters": {
                "type": "object",
                "description": "Parameter for the execution.",
                "default": {}
            },
            "on-success": {
                "type": "string",
                "description": "Name of the node to invoke on successful completion of action"
                               " executed for this node.",
                "default": ""
            },
            "on-failure": {
                "type": "string",
                "description": "Name of the node to invoke on failure of action executed for this"
                               " node.",
                "default": ""
            },
            "publish": {
                "description": "The variables to publish from the result. Should be of the form"
                               " name.foo. o1: {{node_name.foo}} will result in creation of a"
                               " variable o1 which is now available for reference through"
                               " remainder of the chain as a global variable.",
                "type": "object",
                "patternProperties": {
                    "^\w+$": {}
                }
            },
            "notify": {
                "description": "Notification settings for action.",
                "type": "object",
                "properties": {
                    "on-complete": NotificationSubSchemaAPI,
                    "on-failure": NotificationSubSchemaAPI,
                    "on-success": NotificationSubSchemaAPI
                },
                "additionalProperties": False
            }
        },
        "additionalProperties": False
    }

    def __init__(self, **kw):
        for prop in six.iterkeys(self.schema.get('properties', [])):
            value = kw.get(prop, None)
            # having '-' in the property name lead to challenges in referencing the property.
            # At hindsight the schema property should've been on_success rather than on-success.
            prop = string.replace(prop, '-', '_')
            setattr(self, prop, value)

    def validate(self):
        params = getattr(self, 'params', {})
        parameters = getattr(self, 'parameters', {})

        if params and parameters:
            msg = ('Either "params" or "parameters" attribute needs to be provided, but not '
                   'both')
            raise ValueError(msg)

        return self

    def get_parameters(self):
        # Note: "params" is old deprecated attribute which will be removed in a future release
        params = getattr(self, 'params', {})
        parameters = getattr(self, 'parameters', params)

        return parameters

    def __repr__(self):
        return ('<Node name=%s, ref=%s, on-success=%s, on-failure=%s>' %
                (self.name, self.ref, self.on_success, self.on_failure))


class ActionChain(object):

    schema = {
        "title": "ActionChain",
        "description": "A chain of sequentially executed actions.",
        "type": "object",
        "properties": {
            "chain": {
                "description": "The chain.",
                "type": "array",
                "items": [Node.schema],
                "required": True
            },
            "default": {
                "type": "string",
                "description": "name of the action to be executed."
            },
            "vars": {
                "description": "",
                "type": "object",
                "patternProperties": {
                    "^\w+$": {}
                }
            }
        },
        "additionalProperties": False
    }

    def __init__(self, **kw):
        util_schema.validate(instance=kw, schema=self.schema, cls=util_schema.CustomValidator,
                             use_default=False, allow_default_none=True)

        for prop in six.iterkeys(self.schema.get('properties', [])):
            value = kw.get(prop, None)
            # special handling for chain property to create the Node object
            if prop == 'chain':
                nodes = []
                for node in value:
                    ac_node = Node(**node)
                    ac_node.validate()
                    nodes.append(ac_node)
                value = nodes
            setattr(self, prop, value)
