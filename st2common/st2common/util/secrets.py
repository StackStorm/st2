# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
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

import six

from st2common.util.deep_copy import fast_deepcopy_dict
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

    secret_parameters = {}
    parameters_type = parameters.get("type")
    # If the parameter itself is secret, then skip all processing below it
    # and return the type of this parameter.
    #
    # **This causes the _full_ object / array tree to be secret (no children will be shown).**
    #
    # **Important** that we do this check first, so in case this parameter
    # is an `object` or `array`, and the user wants the full thing
    # to be secret, that it is marked as secret.
    if parameters.get("secret", False):
        return parameters_type

    iterator = None
    if parameters_type == "object":
        # if this is an object, then iterate over the properties within
        # the object
        # result = dict
        iterator = six.iteritems(parameters.get("properties", {}))
    elif parameters_type == "array":
        # if this is an array, then iterate over the items definition as a single
        # property
        # result = list
        iterator = enumerate([parameters.get("items", {})])
        secret_parameters = []
    elif parameters_type in ["integer", "number", "boolean", "null", "string"]:
        # if this a "plain old datatype", then iterate over the properties set
        # of the data type
        # result = string (property type)
        iterator = enumerate([parameters])
    else:
        # otherwise, assume we're in an object's properties definition
        # this is the default case for the "root" level for schema specs.
        # result = dict
        iterator = six.iteritems(parameters)

    # iterate over all of the parameters recursively
    for parameter, options in iterator:
        if not isinstance(options, dict):
            continue

        parameter_type = options.get("type")
        if options.get("secret", False):
            # If this parameter is secret, then add it our secret parameters
            #
            # **This causes the _full_ object / array tree to be secret
            #   (no children will be shown)**
            #
            # **Important** that we do this check first, so in case this parameter
            # is an `object` or `array`, and the user wants the full thing
            # to be secret, that it is marked as secret.
            if isinstance(secret_parameters, list):
                secret_parameters.append(parameter_type)
            elif isinstance(secret_parameters, dict):
                secret_parameters[parameter] = parameter_type
            else:
                return parameter_type
        elif parameter_type in ["object", "array"]:
            # otherwise recursively dive into the `object`/`array` and
            # find individual parameters marked as secret
            sub_params = get_secret_parameters(options)
            if sub_params:
                if isinstance(secret_parameters, list):
                    secret_parameters.append(sub_params)
                elif isinstance(secret_parameters, dict):
                    secret_parameters[parameter] = sub_params
                else:
                    return sub_params

    return secret_parameters


def mask_secret_parameters(parameters, secret_parameters, result=None):
    """
    Introspect the parameters dict and return a new dict with masked secret
    parameters.
    :param parameters: Parameters to process.
    :type parameters: ``dict`` or ``list`` or ``string``

    :param secret_parameters: Dict of parameter names which are secret.
                              The type must be the same type as ``parameters``
                              (or at least behave in the same way),
                              so that they can be traversed in the same way as
                              recurse down into the structure.
    :type secret_parameters: ``dict``

    :param result: Deep copy of parameters so that parameters is not modified
                   in place. Default = None, meaning this function will make a
                   deep copy before starting.
    :type result: ``dict`` or ``list`` or ``string``
    """
    # how we iterate depends on what data type was passed in
    iterator = None
    is_dict = isinstance(secret_parameters, dict)
    is_list = isinstance(secret_parameters, list)
    if is_dict:
        iterator = six.iteritems(secret_parameters)
    elif is_list:
        iterator = enumerate(secret_parameters)
    else:
        return MASKED_ATTRIBUTE_VALUE

    # only create a deep copy of parameters on the first call
    # all other recursive calls pass back referneces to this result object
    # so we can reuse it, saving memory and CPU cycles
    if result is None:
        result = fast_deepcopy_dict(parameters)

    # iterate over the secret parameters
    for secret_param, secret_sub_params in iterator:
        if is_dict:
            if secret_param in result:
                result[secret_param] = mask_secret_parameters(
                    parameters[secret_param],
                    secret_sub_params,
                    result=result[secret_param],
                )
        elif is_list:
            # we're assuming lists contain the same data type for every element
            for idx, value in enumerate(result):
                result[idx] = mask_secret_parameters(
                    parameters[idx], secret_sub_params, result=result[idx]
                )
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
    result = fast_deepcopy_dict(response)

    for prop_name, prop_attrs in schema["properties"].items():
        if prop_attrs.get("secret") is True:
            if prop_name in response:
                result[prop_name] = MASKED_ATTRIBUTE_VALUE

    return result
