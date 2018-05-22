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

"""
Utility functions related to masking secrets in the logs.
"""

from __future__ import absolute_import
import copy

import six

from st2common.constants.secrets import MASKED_ATTRIBUTE_VALUE


def get_secret_parameters(parameters):
    """
    Filter the provided parameters dict and return a dict of parameters which are marked as
    secret. Every key in the dict is the parameter name and values are the parameter type:

    >>> d = get_secret_parameters(params)
    >>> d
    {
        "param_a": "string",
        "param_b": "boolean",
        "param_c": "integer"
    }

    If a paramter is a dictionary or a list, then the value will be a nested dictionary
    containing information about that sub-object:

    >>> d = get_secret_parameters(params)
    >>> d
    {
        "param_dict": {
            "nested_a": "boolean",
            "nested_b": "string",
        },
        "param_list": {
            "nested_dict: {
              "param_c": "integer"
            }
        }
    }

    Note: in JSON Schema, we're assuming lists contain the same data type for every element


    :param parameters: Dictionary with runner or action parameters schema specification.
    :type parameters: ``dict``

    :rtype ``list``
    """

    # determine if this parameters set is an object definition
    # if it is, then drill in and grab the properties from the object itself
    parameters_type = parameters.get('type')
    if parameters_type == 'object':
        parameters = parameters.get('properties', {})
    elif parameters_type == 'array':
        parameters = parameters.get('items', {})

    # iterate over all of the parameters recursively
    secret_parameters = {}
    for parameter, options in six.iteritems(parameters):
        # if parameter is a dict or a list, then we need to recurse into them
        parameter_type = options.get('type')
        if parameter_type == 'object':
            sub_params = get_secret_parameters(options.get('properties', {}))
            secret_parameters[parameter] = sub_params
        elif parameter_type == 'array':
            sub_params = get_secret_parameters(options.get('items', {}))
            secret_parameters[parameter] = sub_params
        elif options.get('secret', False):
            # if this parameter is secret, then add it our secret parameters
            secret_parameters[parameter] = parameter_type

    return secret_parameters


def mask_secret_parameters(parameters, secret_parameters):
    """
    Introspect the parameters dict and return a new dict with masked secret
    parameters.

    :param parameters: Parameters to process.
    :type parameters: ``dict``

    :param secret_parameters: Dict of parameter names which are secret.
    :type secret_parameters: ``dict``
    """
    result = copy.deepcopy(parameters)
    for secret_param, secret_sub_params in six.iteritems(secret_parameters):
        if secret_param in result:
            if isinstance(result[secret_param], dict):
                result[secret_param] = mask_secret_parameters(parameters[secret_param],
                                                              secret_sub_params)
            elif isinstance(result[secret_param], list):
                # we're assuming lists contain the same data type for every element
                for idx, value in enumerate(result[secret_param]):
                    result[secret_param][idx] = mask_secret_parameters(parameters[secret_param][idx],
                                                                       secret_sub_params)
            else:
                result[secret_param] = MASKED_ATTRIBUTE_VALUE
    return result


def mask_inquiry_response(response, schema):
    """
    Introspect an Inquiry's response dict and return a new dict with masked secret
    values.

    :param response: Inquiry response to process.
    :type response: ``dict``

    :param schema: Inquiry response schema
    :type schema: ``dict``
    """
    result = copy.deepcopy(response)

    for prop_name, prop_attrs in schema['properties'].items():
        if prop_attrs.get('secret') is True:
            if prop_name in response:
                result[prop_name] = MASKED_ATTRIBUTE_VALUE

    return result
