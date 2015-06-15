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

import copy

import six

from st2common.constants.secrets import MASKED_ATTRIBUTE_VALUE


def get_secret_parameters(parameters):
    """
    Filter the provided parameters dict and return a list of parameter names which are marked as
    secret.

    :param parameters: Dictionary with runner or action parameters schema specification.
    :type parameters: ``dict``

    :rtype ``list``
    """
    secret_parameters = [parameter for parameter, options in
                         six.iteritems(parameters) if options.get('secret', False)]

    return secret_parameters


def mask_secret_parameters(parameters, secret_parameters):
    """
    Introspect the parameters dict and return a new dict with masked secret
    parameters.

    :param parameters: Parameters to process.
    :type parameters: ``dict``

    :param secret_parameters: List of parameter names which are secret.
    :type secret_parameters: ``list``
    """
    result = copy.deepcopy(parameters)

    for parameter in secret_parameters:
        if parameter in result:
            result[parameter] = MASKED_ATTRIBUTE_VALUE

    return result
