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

VALIDATOR = util_schema.get_validator(assign_property_default=False)


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
                "description": "query context to be used by querier.",
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


class ActionChain(object):

    schema = {
        "title": "ActionChain",
        "description": "A chain of sequentially executed actions.",
        "type": "object",
        "properties": {
            "chain": {
                "description": "The chains.",
                "type": "array",
                "items": [Node.schema],
                "required": True
            },
            "default": {
                "type": "string",
                "description": "Ref of the action to be executed."
            }
        },
        "additionalProperties": False
    }

    def __init__(self, **kw):
        VALIDATOR(self.schema).validate(kw)

        for prop in six.iterkeys(self.schema.get('properties', [])):
            value = kw.get(prop, None)
            # special handling for chain property to create the Node object
            if prop == 'chain':
                nodes = []
                for node in value:
                    nodes.append(Node(**node))
                value = nodes
            setattr(self, prop, value)
